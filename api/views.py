from django.db.models import Count, Sum
from django.utils import timezone
from rest_framework import filters, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from donations.models import Donation
from events.models import Event
from members.models import Member

from .serializers import DonationSerializer, EventSerializer, MemberSerializer


class MemberViewSet(viewsets.ModelViewSet):
    """List, create, view, update and delete members. Supports ?search=, ?category= and ?ordering=."""

    queryset = Member.objects.all()
    serializer_class = MemberSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['first_name', 'last_name', 'email']
    ordering_fields = ['last_name', 'first_name', 'joined']

    def get_queryset(self):
        queryset = super().get_queryset()
        category = self.request.query_params.get('category')
        return queryset.filter(category=category) if category else queryset


class DonationViewSet(viewsets.ModelViewSet):
    """Donations. Supports ?type=, ?member=<id>, ?search= (notes) and ?ordering=date or amount."""

    queryset = Donation.objects.select_related('member')
    serializer_class = DonationSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['notes']
    ordering_fields = ['date', 'amount']

    def get_queryset(self):
        queryset = super().get_queryset()
        params = self.request.query_params
        if params.get('type'):
            queryset = queryset.filter(donation_type=params['type'])
        if params.get('member', '').isdigit():
            queryset = queryset.filter(member_id=params['member'])
        return queryset


class EventViewSet(viewsets.ModelViewSet):
    """Events with attendee counts. Supports ?upcoming=true, ?search= and ?ordering=start_time."""

    queryset = Event.objects.annotate(attendee_count=Count('attendances'))
    serializer_class = EventSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'location']
    ordering_fields = ['start_time', 'name']

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.query_params.get('upcoming', '').lower() == 'true':
            queryset = queryset.filter(start_time__gte=timezone.now())
        return queryset


class SummaryView(APIView):
    """Headline numbers for the dashboard."""

    def get(self, request):
        today = timezone.localdate()

        def total(queryset):
            return float(queryset.aggregate(t=Sum('amount'))['t'] or 0)

        return Response({
            'members': Member.objects.count(),
            'members_by_category': dict(Member.objects.values_list('category').annotate(n=Count('id'))),
            'donations_total': total(Donation.objects.all()),
            'donations_this_month': total(Donation.objects.filter(date__year=today.year, date__month=today.month)),
            'upcoming_events': Event.objects.filter(start_time__gte=timezone.now()).count(),
        })
