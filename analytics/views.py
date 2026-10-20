from datetime import date

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Sum
from django.utils import timezone
from django.views.generic import TemplateView

from donations.models import Donation
from events.models import Event
from members.models import Member

from .services import attendance_by_event, linear_forecast, month_starts, monthly_totals, top_attendees


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'analytics/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.localdate()

        months = month_starts(12, today)
        series = monthly_totals(months)
        floats = [float(v) for v in series]
        forecast = linear_forecast(floats)

        this_month, last_month = series[-1], series[-2]
        change = None
        if last_month:
            change = round((this_month - last_month) / last_month * 100)

        next_month = date(today.year + (today.month == 12), today.month % 12 + 1, 1)

        categories = dict(Member.objects.values_list('category').annotate(n=Count('id')))
        types = dict(
            Donation.objects.filter(date__gte=months[0])
            .values_list('donation_type').annotate(total=Sum('amount'))
        )

        attended = attendance_by_event()
        attendance_values = [e.present for e in attended]
        member_count = Member.objects.count()
        avg_attendance = round(sum(attendance_values) / len(attendance_values)) if attendance_values else None

        context.update(
            member_count=member_count,
            avg_attendance=avg_attendance,
            attendance_rate=round(avg_attendance / member_count * 100) if avg_attendance and member_count else None,
            top_attendees=top_attendees(),
            this_month=this_month,
            change=change,
            year_total=Donation.objects.filter(date__year=today.year).aggregate(t=Sum('amount'))['t'] or 0,
            forecast=forecast,
            next_month=next_month,
            upcoming_events=Event.objects.filter(start_time__gte=timezone.now())[:4],
            recent_donations=Donation.objects.select_related('member')[:6],
            chart_data={
                'attendance': {
                    'labels': [timezone.localtime(e.start_time).strftime('%d %b') for e in attended],
                    'names': [e.name for e in attended],
                    'values': attendance_values,
                },
                'labels': [m.strftime('%b %y') for m in months],
                'monthly': floats,
                'forecast_label': next_month.strftime('%b %y') if forecast else None,
                'forecast': round(forecast['next'], 2) if forecast else None,
                'types': {k: float(v) for k, v in types.items()},
                'categories': {label: categories.get(value, 0) for value, label in Member.Category.choices},
            },
        )
        return context
