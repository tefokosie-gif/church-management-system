"""Calculations behind the dashboard, kept separate from the view so they are easy to test."""
from datetime import date
from decimal import Decimal

from django.db.models import Count, Sum
from django.db.models.functions import TruncMonth
from django.utils import timezone

from donations.models import Donation
from events.models import Event
from members.models import Member


def month_starts(n, today=None):
    """First day of each of the last `n` months, oldest first, ending with the current month."""
    today = today or timezone.localdate()
    months = []
    for back in range(n - 1, -1, -1):
        year, month = today.year, today.month - back
        while month <= 0:
            month += 12
            year -= 1
        months.append(date(year, month, 1))
    return months


def monthly_totals(months):
    """Total donated in each of the given months (a list of first-of-month dates)."""
    rows = (
        Donation.objects.filter(date__gte=months[0])
        .annotate(month=TruncMonth('date'))
        .values('month')
        .annotate(total=Sum('amount'))
    )
    by_month = {row['month']: row['total'] for row in rows}
    return [by_month.get(m, Decimal('0')) for m in months]


def linear_forecast(values):
    """
    Fit a straight line (ordinary least squares) through `values` and predict the next point.
    Returns {'next': predicted_value, 'slope': change_per_period}, or None with < 2 points.
    """
    n = len(values)
    if n < 2:
        return None
    mean_x = (n - 1) / 2
    mean_y = sum(values) / n
    sxx = sum((x - mean_x) ** 2 for x in range(n))
    sxy = sum((x - mean_x) * (y - mean_y) for x, y in enumerate(values))
    slope = sxy / sxx
    intercept = mean_y - slope * mean_x
    return {'next': max(0.0, intercept + slope * n), 'slope': slope}


def attendance_by_event(limit=8):
    """Attendance counts for the most recent past events that have attendance recorded, oldest first."""
    events = (
        Event.objects.filter(start_time__lt=timezone.now())
        .annotate(present=Count('attendances'))
        .filter(present__gt=0)
        .order_by('-start_time')[:limit]
    )
    return list(reversed(list(events)))


def top_attendees(limit=5):
    """Members who have attended the most events."""
    return list(
        Member.objects.annotate(times=Count('attendances'))
        .filter(times__gt=0)
        .order_by('-times', 'last_name', 'first_name')[:limit]
    )
