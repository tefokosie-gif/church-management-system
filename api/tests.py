from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from donations.models import Donation
from events.models import Attendance, Event
from members.models import Member


class ApiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        get_user_model().objects.create_user('tester', password='pw-12345-xyz')
        cls.neo = Member.objects.create(first_name='Neo', last_name='Molefe', email='neo@example.com')
        cls.kago = Member.objects.create(first_name='Kago', last_name='Seretse', category='Teen')
        Donation.objects.create(amount=Decimal('500.00'), date=timezone.localdate(), member=cls.neo)
        Donation.objects.create(donation_type='Other Givings', amount=Decimal('100.00'), date=timezone.localdate())
        cls.event = Event.objects.create(name='Sunday Service', start_time=timezone.now())
        Attendance.objects.create(event=cls.event, member=cls.neo)

    def login(self):
        self.client.login(username='tester', password='pw-12345-xyz')

    def test_api_requires_login(self):
        for url in ('/api/', '/api/members/', '/api/donations/', '/api/events/', '/api/summary/'):
            self.assertEqual(self.client.get(url).status_code, 403, url)

    def test_basic_auth_works_for_scripts(self):
        import base64
        token = base64.b64encode(b'tester:pw-12345-xyz').decode()
        response = self.client.get('/api/members/', HTTP_AUTHORIZATION=f'Basic {token}')
        self.assertEqual(response.status_code, 200)

    def test_member_list_search_and_filter(self):
        self.login()
        data = self.client.get('/api/members/').json()
        self.assertEqual(data['count'], 2)
        self.assertEqual(self.client.get('/api/members/?search=seretse').json()['count'], 1)
        self.assertEqual(self.client.get('/api/members/?category=Teen').json()['results'][0]['first_name'], 'Kago')

    def test_member_crud(self):
        self.login()
        response = self.client.post('/api/members/', {'first_name': 'Thato', 'last_name': 'Phiri', 'category': 'Adult'},
                                    content_type='application/json')
        self.assertEqual(response.status_code, 201)
        pk = response.json()['id']
        self.assertEqual(response.json()['full_name'], 'Thato Phiri')
        response = self.client.patch(f'/api/members/{pk}/', {'phone': '+267 71 000 0001'}, content_type='application/json')
        self.assertEqual(response.json()['phone'], '+267 71 000 0001')
        self.assertEqual(self.client.delete(f'/api/members/{pk}/').status_code, 204)
        self.assertFalse(Member.objects.filter(pk=pk).exists())

    def test_member_validation(self):
        self.login()
        response = self.client.post('/api/members/', {'last_name': 'NoFirstName'}, content_type='application/json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('first_name', response.json())

    def test_donations_filter_and_member_name(self):
        self.login()
        data = self.client.get('/api/donations/').json()
        self.assertEqual(data['count'], 2)
        self.assertEqual(self.client.get('/api/donations/?type=Tithes').json()['count'], 1)
        self.assertEqual(self.client.get(f'/api/donations/?member={self.neo.pk}').json()['results'][0]['member_name'], 'Neo Molefe')

    def test_donation_amount_must_be_positive(self):
        self.login()
        response = self.client.post('/api/donations/', {'donation_type': 'Tithes', 'amount': '0', 'date': '2026-01-01'},
                                    content_type='application/json')
        self.assertEqual(response.status_code, 400)

    def test_events_include_attendee_count_and_upcoming_filter(self):
        self.login()
        Event.objects.create(name='Later', start_time=timezone.now() + timezone.timedelta(days=5))
        results = self.client.get('/api/events/').json()['results']
        self.assertEqual({e['name']: e['attendee_count'] for e in results}, {'Sunday Service': 1, 'Later': 0})
        upcoming = self.client.get('/api/events/?upcoming=true').json()['results']
        self.assertEqual([e['name'] for e in upcoming], ['Later'])

    def test_summary(self):
        self.login()
        data = self.client.get('/api/summary/').json()
        self.assertEqual(data['members'], 2)
        self.assertEqual(data['donations_total'], 600.0)
        self.assertEqual(data['members_by_category'], {'Adult': 1, 'Teen': 1})

    def test_browsable_api_renders_in_a_browser(self):
        self.login()
        response = self.client.get('/api/members/', HTTP_ACCEPT='text/html')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Member List')
