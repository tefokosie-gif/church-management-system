"""Fill the database with fictional demo data (safe to publish and screenshot)."""
import random
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from analytics.services import month_starts
from communications.models import Message
from donations.models import Donation
from events.models import Event
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

# (name, days from today, hour, location, description)
EVENTS = [
    ('Sunday Service', -21, 9, 'Main Sanctuary', 'Weekly worship service.'),
    ('Youth Fellowship Night', -14, 18, 'Fellowship Hall', 'Games, worship and a short talk for teens.'),
    ('Community Outreach Day', -6, 8, 'Town Square', 'Food parcels and clothing drive for the neighbourhood.'),
    ('Sunday Service', 3, 9, 'Main Sanctuary', 'Weekly worship service.'),
    ("Women's Prayer Breakfast", 6, 7, 'Fellowship Hall', 'Breakfast, prayer and testimonies.'),
    ('Choir Rehearsal', 9, 17, 'Main Sanctuary', 'Rehearsal ahead of the harvest service.'),
    ('Bible Study', 13, 19, 'Room 2', 'Study group working through the book of Acts.'),
    ('Annual Harvest Thanksgiving', 30, 10, 'Main Sanctuary', 'Special thanksgiving service followed by lunch.'),
]


class Command(BaseCommand):
    help = 'Create fictional demo data: members, donations, events, messages and a demo login.'

    def add_arguments(self, parser):
        parser.add_argument('--reset', action='store_true',
                            help='Delete existing members, donations, events and messages first.')

    def handle(self, *args, **options):
        if options['reset']:
            for model in (Message, Donation, Event, Member):
                model.objects.all().delete()
        elif Member.objects.exists():
            self.stdout.write(self.style.WARNING('Data already exists. Use --reset to replace it.'))
            return

        rng = random.Random(42)
        today = timezone.localdate()

        # --- demo login ---
        User = get_user_model()
        if not User.objects.filter(username=settings.DEMO_USERNAME).exists():
            User.objects.create_user(
                settings.DEMO_USERNAME, 'demo@example.com', settings.DEMO_PASSWORD,
                first_name='Demo', last_name='Admin',
            )

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

        # --- events ---
        for name, offset, hour, location, description in EVENTS:
            when = timezone.make_aware(datetime.combine(today + timedelta(days=offset), time(hour, 0)))
            Event.objects.create(name=name, start_time=when, location=location, description=description)

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
            f'{Event.objects.count()} events and {Message.objects.count()} messages.'
        ))
        self.stdout.write(f'Demo login: {settings.DEMO_USERNAME} / {settings.DEMO_PASSWORD}')
