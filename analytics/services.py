"""Calculations behind the dashboard, kept separate from the view so they are easy to test."""
from datetime import date
from decimal import Decimal

from django.db.models import Avg, Count, Sum
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


# ---------------------------------------------------------------- reports

REGULAR_GIVER_MONTHS = 3  # a "regular giver" gave in at least this many different months


def parse_range(params, today=None):
    """Read ?start= and ?end= (YYYY-MM-DD). Defaults to the last 12 months; swaps them if reversed."""
    today = today or timezone.localdate()

    def parse(value, default):
        try:
            return date.fromisoformat(value)
        except (TypeError, ValueError):
            return default

    start = parse(params.get('start'), month_starts(12, today)[0])
    end = parse(params.get('end'), today)
    return (end, start) if start > end else (start, end)


def months_between(start, end):
    """First day of every month from start's month to end's month."""
    months, current = [], date(start.year, start.month, 1)
    while current <= end:
        months.append(current)
        current = date(current.year + (current.month == 12), current.month % 12 + 1, 1)
    return months


def giving_report(start, end):
    """Giving between two dates: totals, a month-by-month table, top givers and giver counts."""
    donations = Donation.objects.filter(date__gte=start, date__lte=end)
    summary = donations.aggregate(total=Sum('amount'), gifts=Count('id'), average=Avg('amount'))
    total = summary['total'] or Decimal('0')

    # month-by-month table
    rows = (
        donations.annotate(month=TruncMonth('date'))
        .values('month', 'donation_type')
        .annotate(amount=Sum('amount'), gifts=Count('id'))
    )
    by_month = {}
    for row in rows:
        entry = by_month.setdefault(row['month'], {'gifts': 0})
        entry[row['donation_type']] = row['amount']
        entry['gifts'] += row['gifts']
    monthly = []
    for month in months_between(start, end):
        entry = by_month.get(month, {})
        tithes = entry.get(Donation.Type.TITHES, Decimal('0'))
        other = entry.get(Donation.Type.OTHER, Decimal('0'))
        monthly.append({'month': month, 'tithes': tithes, 'other': other,
                        'total': tithes + other, 'gifts': entry.get('gifts', 0)})

    # top givers
    named = donations.filter(member__isnull=False)
    top_rows = list(named.values('member').annotate(amount=Sum('amount'), gifts=Count('id')).order_by('-amount', 'member')[:10])
    members = Member.objects.in_bulk([row['member'] for row in top_rows])
    top_givers = [
        {'member': members[row['member']], 'amount': row['amount'], 'gifts': row['gifts'],
         'share': round(row['amount'] / total * 100) if total else 0}
        for row in top_rows
    ]

    # how many members gave at all, and how many gave in several different months
    months_by_member = {}
    for member_id, day in named.values_list('member_id', 'date'):
        months_by_member.setdefault(member_id, set()).add((day.year, day.month))
    active = len(months_by_member)
    regular = sum(1 for months in months_by_member.values() if len(months) >= REGULAR_GIVER_MONTHS)

    anonymous = donations.filter(member__isnull=True).aggregate(t=Sum('amount'))['t'] or Decimal('0')
    member_count = Member.objects.count()
    return {
        'total': total,
        'gifts': summary['gifts'],
        'average': summary['average'] or 0,
        'monthly': monthly,
        'top_givers': top_givers,
        'active_givers': active,
        'regular_givers': regular,
        'member_count': member_count,
        'active_pct': round(active / member_count * 100) if member_count else 0,
        'anonymous_pct': round(anonymous / total * 100) if total else 0,
    }


def attendance_report(start, end, limit=10):
    """Past events between two dates that have attendance recorded, newest first, with attendance rates."""
    member_count = Member.objects.count()
    events = list(
        Event.objects.filter(start_time__date__gte=start, start_time__date__lte=end, start_time__lt=timezone.now())
        .annotate(present=Count('attendances'))
        .filter(present__gt=0)
        .order_by('-start_time')[:limit]
    )
    for event in events:
        event.rate = round(event.present / member_count * 100) if member_count else 0
    average = round(sum(e.present for e in events) / len(events)) if events else None
    return {'events': events, 'average': average}
