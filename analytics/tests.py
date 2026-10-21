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
        get_user_model().objects.create_superuser('tester', password='pw-12345-xyz')

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

        get_user_model().objects.create_superuser('tester', password='pw-12345-xyz')
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


class ReportTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        import csv  # noqa: F401  (used by helper below)
        get_user_model().objects.create_superuser('tester', password='pw-12345-xyz')
        cls.neo = Member.objects.create(first_name='Neo', last_name='Molefe', phone='+267 71 000 0001')
        cls.kago = Member.objects.create(first_name='Kago', last_name='Seretse')
        for day in ('2026-01-05', '2026-02-05', '2026-03-05'):  # Neo gives in 3 different months
            Donation.objects.create(amount=Decimal('100'), date=day, member=cls.neo)
        Donation.objects.create(amount=Decimal('50'), date='2026-02-10', member=cls.kago, donation_type='Other Givings')
        Donation.objects.create(amount=Decimal('100'), date='2026-03-15')  # anonymous
        Donation.objects.create(amount=Decimal('999'), date='2025-06-01', member=cls.kago)  # outside the range
        cls.start, cls.end = date(2026, 1, 1), date(2026, 3, 31)

    def setUp(self):
        self.client.login(username='tester', password='pw-12345-xyz')

    @staticmethod
    def rows(response):
        import csv
        import io
        return list(csv.reader(io.StringIO(response.content.decode('utf-8-sig'))))

    # --- date range ---
    def test_parse_range_defaults_to_last_12_months(self):
        from .services import parse_range
        self.assertEqual(parse_range({}, today=date(2026, 10, 21)), (date(2025, 11, 1), date(2026, 10, 21)))

    def test_parse_range_ignores_bad_input_and_swaps_reversed_dates(self):
        from .services import parse_range
        self.assertEqual(parse_range({'start': 'nonsense'}, today=date(2026, 10, 21))[0], date(2025, 11, 1))
        self.assertEqual(parse_range({'start': '2026-03-01', 'end': '2026-01-01'}), (date(2026, 1, 1), date(2026, 3, 1)))

    # --- report numbers ---
    def test_giving_report_totals_and_months(self):
        from .services import giving_report
        report = giving_report(self.start, self.end)
        self.assertEqual(report['total'], Decimal('450'))
        self.assertEqual(report['gifts'], 5)
        self.assertEqual([m['month'] for m in report['monthly']], [date(2026, 1, 1), date(2026, 2, 1), date(2026, 3, 1)])
        february = report['monthly'][1]
        self.assertEqual((february['tithes'], february['other'], february['total']), (Decimal('100'), Decimal('50'), Decimal('150')))

    def test_top_givers_and_giver_counts(self):
        from .services import giving_report
        report = giving_report(self.start, self.end)
        self.assertEqual(report['top_givers'][0]['member'], self.neo)
        self.assertEqual(report['top_givers'][0]['share'], 67)  # 300 of 450
        self.assertEqual(report['active_givers'], 2)
        self.assertEqual(report['regular_givers'], 1)  # only Neo gave in 3+ different months
        self.assertEqual(report['anonymous_pct'], 22)  # 100 of 450

    def test_reports_page_respects_the_date_range(self):
        response = self.client.get(reverse('analytics:reports'), {'start': '2025-01-01', 'end': '2025-12-31'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '999.00')
        self.assertNotContains(response, '450.00')

    def test_reports_page_renders_with_defaults(self):
        self.assertEqual(self.client.get(reverse('analytics:reports')).status_code, 200)

    # --- CSV exports ---
    def test_members_export(self):
        response = self.client.get(reverse('analytics:export_members'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('text/csv', response['Content-Type'])
        self.assertIn('attachment', response['Content-Disposition'])
        rows = self.rows(response)
        self.assertEqual(rows[0][:3], ['id', 'first_name', 'last_name'])
        self.assertEqual(len(rows), 3)  # header + 2 members

    def test_donations_export_with_and_without_a_range(self):
        everything = self.rows(self.client.get(reverse('analytics:export_donations')))
        self.assertEqual(len(everything) - 1, 6)
        in_range = self.rows(self.client.get(reverse('analytics:export_donations'), {'start': '2026-01-01', 'end': '2026-03-31'}))
        self.assertEqual(len(in_range) - 1, 5)

    def test_attendance_export(self):
        from datetime import timedelta
        from django.utils import timezone
        from events.models import Attendance, Event
        event = Event.objects.create(name='Sunday Service', start_time=timezone.now() - timedelta(days=2))
        Attendance.objects.create(event=event, member=self.neo)
        rows = self.rows(self.client.get(reverse('analytics:export_attendance')))
        self.assertEqual(rows[1][1], 'Sunday Service')
        self.assertEqual(rows[1][4], 'Neo Molefe')

    def test_csv_injection_is_neutralised_but_phone_numbers_survive(self):
        Member.objects.create(first_name='=HYPERLINK("http://evil")', last_name='X')
        rows = self.rows(self.client.get(reverse('analytics:export_members')))
        first_names = [r[1] for r in rows]
        self.assertIn("'=HYPERLINK(\"http://evil\")", first_names)
        self.assertIn('+267 71 000 0001', [r[6] for r in rows])

    def test_exports_require_login(self):
        self.client.logout()
        self.assertEqual(self.client.get(reverse('analytics:export_members')).status_code, 302)
