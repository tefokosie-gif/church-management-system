"""CSV downloads of members, donations and attendance (open them in Excel or load them with pandas)."""
import csv
import re

from django.contrib.auth.mixins import PermissionRequiredMixin
from django.http import HttpResponse
from django.utils import timezone
from django.views import View

from donations.models import Donation
from events.models import Attendance
from members.models import Member

from .services import parse_range

PHONE_NUMBER = re.compile(r'\+[\d\s()-]+')


def safe(value):
    """
    Guard against CSV injection: a cell starting with = + - or @ can run as a formula when opened in
    Excel, so such text gets a leading apostrophe. Normal phone numbers (+267 ...) are left alone.
    """
    text = '' if value is None else str(value)
    if text and text[0] in '=+-@\t\r' and not PHONE_NUMBER.fullmatch(text):
        return "'" + text
    return text


class CsvExportView(PermissionRequiredMixin, View):
    filename = 'export'
    header = []

    def get_rows(self, request):
        raise NotImplementedError

    def get(self, request):
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="{self.filename}-{timezone.localdate()}.csv"'
        response.write('\ufeff')  # a byte-order mark so Excel reads accented characters correctly
        writer = csv.writer(response)
        writer.writerow(self.header)
        for row in self.get_rows(request):
            writer.writerow([safe(value) for value in row])
        return response

    @staticmethod
    def get_range(request):
        """(start, end) if the link carries a date range, otherwise None meaning 'everything'."""
        if 'start' in request.GET or 'end' in request.GET:
            return parse_range(request.GET)
        return None


class MembersExport(CsvExportView):
    permission_required = 'members.view_member'
    filename = 'members'
    header = ['id', 'first_name', 'last_name', 'category', 'birth_date', 'email', 'phone', 'joined']

    def get_rows(self, request):
        for m in Member.objects.all():
            yield [m.pk, m.first_name, m.last_name, m.category, m.birth_date, m.email, m.phone, m.joined]


class DonationsExport(CsvExportView):
    permission_required = 'donations.view_donation'
    filename = 'donations'
    header = ['id', 'date', 'donation_type', 'amount', 'member_id', 'member_name', 'notes']

    def get_rows(self, request):
        donations = Donation.objects.select_related('member').order_by('date', 'id')
        date_range = self.get_range(request)
        if date_range:
            donations = donations.filter(date__gte=date_range[0], date__lte=date_range[1])
        for d in donations:
            yield [d.pk, d.date, d.donation_type, d.amount, d.member_id, d.member.full_name if d.member else '', d.notes]


class AttendanceExport(CsvExportView):
    permission_required = 'events.view_attendance'
    filename = 'attendance'
    header = ['event_id', 'event_name', 'event_date', 'member_id', 'member_name', 'category']

    def get_rows(self, request):
        records = Attendance.objects.select_related('event', 'member').order_by('event__start_time', 'member__last_name')
        date_range = self.get_range(request)
        if date_range:
            records = records.filter(event__start_time__date__gte=date_range[0], event__start_time__date__lte=date_range[1])
        for a in records:
            yield [a.event_id, a.event.name, timezone.localtime(a.event.start_time).date(),
                   a.member_id, a.member.full_name, a.member.category]
