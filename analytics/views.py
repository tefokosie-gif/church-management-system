from datetime import date

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Sum
from django.utils import timezone
from django.views.generic import TemplateView

from donations.models import Donation
from events.models import Event
from members.models import Member

from .services import linear_forecast, month_starts, monthly_totals


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

        context.update(
            member_count=Member.objects.count(),
            this_month=this_month,
            change=change,
            year_total=Donation.objects.filter(date__year=today.year).aggregate(t=Sum('amount'))['t'] or 0,
            forecast=forecast,
            next_month=next_month,
            upcoming_events=Event.objects.filter(start_time__gte=timezone.now())[:4],
            recent_donations=Donation.objects.select_related('member')[:6],
            chart_data={
                'labels': [m.strftime('%b %y') for m in months],
                'monthly': floats,
                'forecast_label': next_month.strftime('%b %y') if forecast else None,
                'forecast': round(forecast['next'], 2) if forecast else None,
                'types': {k: float(v) for k, v in types.items()},
                'categories': {label: categories.get(value, 0) for value, label in Member.Category.choices},
            },
        )
        return context
