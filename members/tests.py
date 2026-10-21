from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Member


class MemberTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_superuser('tester', password='pw-12345-xyz')
        cls.member = Member.objects.create(first_name='Neo', last_name='Molefe', email='neo@example.com')

    def login(self):
        self.client.login(username='tester', password='pw-12345-xyz')

    def test_pages_require_login(self):
        url = reverse('members:list')
        self.assertRedirects(self.client.get(url), f"{reverse('login')}?next={url}")

    def test_list_shows_members_and_search_filters(self):
        Member.objects.create(first_name='Kago', last_name='Seretse')
        self.login()
        response = self.client.get(reverse('members:list'))
        self.assertContains(response, 'Molefe')
        self.assertContains(response, 'Seretse')
        response = self.client.get(reverse('members:list'), {'q': 'seretse'})
        self.assertContains(response, 'Seretse')
        self.assertNotContains(response, 'Molefe')

    def test_category_filter(self):
        Member.objects.create(first_name='Mpho', last_name='Dube', category='Teen')
        self.login()
        response = self.client.get(reverse('members:list'), {'category': 'Teen'})
        self.assertContains(response, 'Dube')
        self.assertNotContains(response, 'Molefe')

    def test_create_member(self):
        self.login()
        response = self.client.post(reverse('members:create'), {
            'first_name': 'Thato', 'last_name': 'Phiri', 'category': 'Adult',
            'joined': '2025-01-15', 'email': '', 'phone': '', 'birth_date': '',
        })
        self.assertRedirects(response, reverse('members:list'))
        self.assertTrue(Member.objects.filter(last_name='Phiri').exists())

    def test_create_requires_name(self):
        self.login()
        response = self.client.post(reverse('members:create'), {'category': 'Adult', 'joined': '2025-01-15'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Member.objects.count(), 1)

    def test_update_member(self):
        self.login()
        self.client.post(reverse('members:update', args=[self.member.pk]), {
            'first_name': 'Neo', 'last_name': 'Modise', 'category': 'Adult', 'joined': '2025-01-15',
        })
        self.member.refresh_from_db()
        self.assertEqual(self.member.last_name, 'Modise')

    def test_delete_member(self):
        self.login()
        self.client.post(reverse('members:delete', args=[self.member.pk]))
        self.assertFalse(Member.objects.filter(pk=self.member.pk).exists())

    def test_detail_page(self):
        self.login()
        self.assertContains(self.client.get(self.member.get_absolute_url()), 'Neo Molefe')

    def test_age(self):
        today = date.today()
        member = Member(first_name='A', last_name='B', birth_date=today.replace(year=today.year - 30) - timedelta(days=1))
        self.assertEqual(member.age, 30)
        self.assertIsNone(Member(first_name='A', last_name='B').age)


class MemberAttendanceTests(TestCase):
    def test_detail_shows_events_attended(self):
        from django.utils import timezone
        from events.models import Attendance, Event
        get_user_model().objects.create_superuser('tester', password='pw-12345-xyz')
        member = Member.objects.create(first_name='Neo', last_name='Molefe')
        for name in ('One', 'Two'):
            Attendance.objects.create(event=Event.objects.create(name=name, start_time=timezone.now()), member=member)
        self.client.login(username='tester', password='pw-12345-xyz')
        response = self.client.get(member.get_absolute_url())
        self.assertEqual(response.context['attended_count'], 2)
