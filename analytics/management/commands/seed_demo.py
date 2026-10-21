"""Fill the database with fictional demo data (safe to publish and screenshot)."""
import random
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from django.utils import timezone

from analytics.services import month_starts
from church_management.roles import STAFF, VIEWER, ensure_roles
from communications.models import Message
from donations.models import Donation
from events.models import Attendance, Event
from members.models import Member

FIRST_NAMES = [
    'Neo', 'Kago', 'Lesedi', 'Thato', 'Boitumelo', 'Tshepo', 'Mpho', 'Kabelo', 'Onalenna', 'Naledi',
    'Tumelo', 'Gorata', 'Refilwe', 'Lorato', 'Keabetswe', 'Masego', 'Omphile', 'Karabo', 'Dineo', 'Tebogo',
    'Atang', 'Goitseone', 'Resego', 'Kopano',
]
LAST_NAMES = [
    'Molefe', 'Seretse', 'Kgosi', 'Modise', 'Mokgosi', 'Dube', 'Phiri', 'Ramotswa', 'Sebego', 'Tau',
    'Moeng', 'Letsholo', 'Mothibi', 'Ntsima', 'Segwai', 'Kebonang',
]
CATEGORY_WEIGHTS = [('Adult', 14), ('Teen', 4), ('Sunday School', 3), ('Visitor', 3)]
AGE_RANGE = {'Adult': (25, 70), 'Teen': (13, 19), 'Sunday School': (5, 12), 'Visitor': (20, 60)}

# One-off events: (name, days from today, hour, location, description)
OTHER_EVENTS = [
    ('Youth Fellowship Night', -14, 18, 'Fellowship Hall', 'Games, worship and a short talk for teens.'),
    ('Community Outreach Day', -6, 8, 'Town Square', 'Food parcels and clothing drive for the neighbourhood.'),
    ("Women's Prayer Breakfast", 6, 7, 'Fellowship Hall', 'Breakfast, prayer and testimonies.'),
    ('Choir Rehearsal', 9, 17, 'Main Sanctuary', 'Rehearsal ahead of the harvest service.'),
    ('Bible Study', 13, 19, 'Room 2', 'Study group working through the book of Acts.'),
    ('Annual Harvest Thanksgiving', 30, 10, 'Main Sanctuary', 'Special thanksgiving service followed by lunch.'),
]
ATTENDANCE_RATE = {'Adult': 0.75, 'Teen': 0.55, 'Sunday School': 0.6, 'Visitor': 0.2}


class Command(BaseCommand):
    help = 'Create fictional demo data: members, donations, events, messages and a demo login.'

    def add_arguments(self, parser):
        parser.add_argument('--reset', action='store_true',
                            help='Delete existing members, donations, events and messages first.')

    def handle(self, *args, **options):
        # --- demo logins: one full-access (Staff), one read-only (Viewer) ---
        ensure_roles()
        User = get_user_model()
        for username, password, last_name, role in (
            (settings.DEMO_USERNAME, settings.DEMO_PASSWORD, 'Admin', STAFF),
            (settings.DEMO_VIEWER_USERNAME, settings.DEMO_VIEWER_PASSWORD, 'Viewer', VIEWER),
        ):
            user, created = User.objects.get_or_create(
                username=username,
                defaults={'first_name': 'Demo', 'last_name': last_name, 'email': f'{username}@example.com'},
            )
            if created:
                user.set_password(password)
                user.save()
            user.groups.set([Group.objects.get(name=role)])

        if options['reset']:
            for model in (Message, Donation, Event, Member):
                model.objects.all().delete()
        elif Member.objects.exists():
            self.stdout.write(self.style.WARNING('Data already exists. Use --reset to replace it.'))
            return

        rng = random.Random(42)
        today = timezone.localdate()

        # --- members ---
        names = [(f, l) for f in FIRST_NAMES for l in LAST_NAMES]
        rng.shuffle(names)
        categories, weights = zip(*CATEGORY_WEIGHTS)
        members = []
        for i, (first, last) in enumerate(names[:24]):
            category = rng.choices(categories, weights)[0]
            low, high = AGE_RANGE[category]
            birth = today - timedelta(days=int(rng.uniform(low, high) * 365.25))
            members.append(Member(
                first_name=first, last_name=last, category=category, birth_date=birth,
                email='' if category == 'Sunday School' else f'{first}.{last}@example.com'.lower(),
                phone=f'+267 71 000 {i:04d}',
                joined=today - timedelta(days=rng.randint(30, 1100)),
            ))
        Member.objects.bulk_create(members)
        members = list(Member.objects.all())
        givers = [m for m in members if m.category in ('Adult', 'Teen')]

        # --- donations: ~12 months of giving with a gentle upward trend ---
        donations = []
        for index, start in enumerate(month_starts(12, today)):
            next_start = date(start.year + (start.month == 12), start.month % 12 + 1, 1)
            end = min(next_start - timedelta(days=1), today)
            growth = 1 + 0.03 * index
            for _ in range(rng.randint(6, 10)):
                is_tithe = rng.random() < 0.7
                base = rng.randrange(200, 1500, 50) if is_tithe else rng.randrange(50, 500, 25)
                donations.append(Donation(
                    donation_type=Donation.Type.TITHES if is_tithe else Donation.Type.OTHER,
                    amount=Decimal(round(base * growth / 5) * 5),
                    date=start + timedelta(days=rng.randint(0, (end - start).days)),
                    member=rng.choice(givers) if rng.random() < 0.75 else None,
                ))
        Donation.objects.bulk_create(donations)

        # --- events: eight past Sunday services, one coming up, plus the one-off events ---
        def at(day, hour):
            return timezone.make_aware(datetime.combine(day, time(hour, 0)))

        last_sunday = today - timedelta(days=((today.weekday() + 1) % 7) or 7)
        next_sunday = today + timedelta(days=(6 - today.weekday()) or 7)
        for weeks_back in range(8):
            Event.objects.create(name='Sunday Service', start_time=at(last_sunday - timedelta(weeks=weeks_back), 9),
                                 location='Main Sanctuary', description='Weekly worship service.')
        Event.objects.create(name='Sunday Service', start_time=at(next_sunday, 9),
                             location='Main Sanctuary', description='Weekly worship service.')
        for name, offset, hour, location, description in OTHER_EVENTS:
            Event.objects.create(name=name, start_time=at(today + timedelta(days=offset), hour),
                                 location=location, description=description)

        # --- attendance for past events (attendance slowly trends upward) ---
        attendances = []
        past_events = Event.objects.filter(start_time__lt=timezone.now()).order_by('start_time')
        for index, event in enumerate(past_events):
            trend = 0.85 + 0.03 * index
            for member in members:
                rate = ATTENDANCE_RATE[member.category] * trend
                if event.name == 'Youth Fellowship Night':
                    rate = 0.9 if member.category == 'Teen' else 0.05
                elif event.name == 'Community Outreach Day':
                    rate *= 0.5
                if rng.random() < min(rate, 0.95):
                    attendances.append(Attendance(event=event, member=member))
        Attendance.objects.bulk_create(attendances)

        # --- messages ---
        sender = User.objects.get(username=settings.DEMO_USERNAME)
        with_email = [m for m in members if m.email]
        samples = [
            ('Welcome to the church family', 'We are so glad you joined us. Let us know if you need anything.'),
            ('Harvest Thanksgiving this month', 'Please join us for the annual Harvest Thanksgiving service and lunch.'),
            ('Thank you for your giving', 'Thank you for your generous support of the church this month.'),
            ('Choir rehearsal reminder', 'Rehearsal is this week. Please arrive ten minutes early.'),
        ]
        for subject, content in samples:
            Message.objects.create(sender=sender, recipient=rng.choice(with_email), subject=subject, content=content)

        self.stdout.write(self.style.SUCCESS(
            f'Created {Member.objects.count()} members, {Donation.objects.count()} donations, '
            f'{Event.objects.count()} events ({Attendance.objects.count()} attendance records) '
            f'and {Message.objects.count()} messages.'
        ))
        self.stdout.write(f'Demo logins: {settings.DEMO_USERNAME} / {settings.DEMO_PASSWORD} (full access), '
                          f'{settings.DEMO_VIEWER_USERNAME} / {settings.DEMO_VIEWER_PASSWORD} (read-only)')
