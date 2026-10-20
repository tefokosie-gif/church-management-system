from io import StringIO
from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from donations.models import Donation
from members.models import Member

from .services import linear_forecast, month_starts, monthly_totals


class ServiceTests(TestCase):
    def test_month_starts_spans_year_boundary(self):
        months = month_starts(4, today=date(2026, 2, 15))
        self.assertEqual(months, [date(2025, 11, 1), date(2025, 12, 1), date(2026, 1, 1), date(2026, 2, 1)])

    def test_monthly_totals_fills_gaps_with_zero(self):
        Donation.objects.create(amount=Decimal('100'), date='2026-01-05')
        Donation.objects.create(amount=Decimal('50'), date='2026-01-20')
        Donation.objects.create(amount=Decimal('70'), date='2026-03-02')
        months = [date(2026, 1, 1), date(2026, 2, 1), date(2026, 3, 1)]
        self.assertEqual(monthly_totals(months), [Decimal('150'), Decimal('0'), Decimal('70')])

    def test_linear_forecast_continues_a_straight_line(self):
        result = linear_forecast([10, 20, 30])
        self.assertAlmostEqual(result['next'], 40)
        self.assertAlmostEqual(result['slope'], 10)

    def test_linear_forecast_never_negative_and_needs_two_points(self):
        self.assertEqual(linear_forecast([30, 20, 10])['next'], 0.0)
        self.assertIsNone(linear_forecast([5]))


class DashboardTests(TestCase):
    def setUp(self):
        get_user_model().objects.create_user('tester', password='pw-12345-xyz')

    def test_requires_login(self):
        self.assertEqual(self.client.get(reverse('analytics:dashboard')).status_code, 302)

    def test_dashboard_renders_with_no_data(self):
        self.client.login(username='tester', password='pw-12345-xyz')
        self.assertEqual(self.client.get(reverse('analytics:dashboard')).status_code, 200)

    def test_dashboard_renders_with_seeded_data(self):
        call_command('seed_demo', stdout=StringIO())
        self.client.login(username='tester', password='pw-12345-xyz')
        response = self.client.get(reverse('analytics:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['member_count'], Member.objects.count())
        self.assertIsNotNone(response.context['forecast'])

    def test_seed_is_safe_to_run_twice(self):
        call_command('seed_demo', stdout=StringIO())
        count = Member.objects.count()
        call_command('seed_demo', stdout=StringIO())
        self.assertEqual(Member.objects.count(), count)


class AttendanceAnalyticsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        from datetime import timedelta
        from django.utils import timezone
        from events.models import Attendance, Event

        get_user_model().objects.create_user('tester', password='pw-12345-xyz')
        now = timezone.now()
        cls.members = [Member.objects.create(first_name=n, last_name='Test') for n in ('A', 'B', 'C')]
        cls.old = Event.objects.create(name='Old', start_time=now - timedelta(days=14))
        cls.recent = Event.objects.create(name='Recent', start_time=now - timedelta(days=7))
        cls.empty = Event.objects.create(name='Nobody came', start_time=now - timedelta(days=3))
        cls.future = Event.objects.create(name='Future', start_time=now + timedelta(days=3))
        for member in cls.members[:2]:
            Attendance.objects.create(event=cls.old, member=member)
        Attendance.objects.create(event=cls.recent, member=cls.members[0])

    def test_attendance_by_event_is_oldest_first_and_skips_empty_and_future(self):
        from .services import attendance_by_event
        result = attendance_by_event()
        self.assertEqual([(e.name, e.present) for e in result], [('Old', 2), ('Recent', 1)])

    def test_top_attendees_orders_by_times_attended(self):
        from .services import top_attendees
        result = top_attendees()
        self.assertEqual(result[0], self.members[0])
        self.assertEqual(result[0].times, 2)
        self.assertNotIn(self.members[2], result)

    def test_dashboard_shows_average_attendance(self):
        self.client.login(username='tester', password='pw-12345-xyz')
        response = self.client.get(reverse('analytics:dashboard'))
        self.assertEqual(response.context['avg_attendance'], 2)  # (2 + 1) / 2 rounds to 2
        self.assertEqual(response.context['chart_data']['attendance']['values'], [2, 1])
