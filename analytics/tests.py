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
