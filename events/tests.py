from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Event


class EventTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        get_user_model().objects.create_user('tester', password='pw-12345-xyz')
        cls.future = Event.objects.create(name='Harvest Service', start_time=timezone.now() + timedelta(days=5))
        cls.past = Event.objects.create(name='Old Picnic', start_time=timezone.now() - timedelta(days=5))

    def setUp(self):
        self.client.login(username='tester', password='pw-12345-xyz')

    def test_is_upcoming(self):
        self.assertTrue(self.future.is_upcoming)
        self.assertFalse(self.past.is_upcoming)

    def test_list_separates_upcoming_and_past(self):
        response = self.client.get(reverse('events:list'))
        self.assertEqual([e.name for e in response.context['upcoming']], ['Harvest Service'])
        self.assertEqual([e.name for e in response.context['past']], ['Old Picnic'])

    def test_create_event(self):
        response = self.client.post(reverse('events:create'), {
            'name': 'Bible Study', 'start_time': '2030-06-01T09:00', 'location': 'Room 2', 'description': '',
        })
        self.assertRedirects(response, reverse('events:list'))
        self.assertTrue(Event.objects.filter(name='Bible Study').exists())

    def test_edit_form_prefills_start_time(self):
        response = self.client.get(reverse('events:update', args=[self.future.pk]))
        self.assertContains(response, 'datetime-local')
        self.assertEqual(response.status_code, 200)

    def test_update_and_delete(self):
        self.client.post(reverse('events:update', args=[self.future.pk]), {
            'name': 'Renamed', 'start_time': '2030-06-01T09:00',
        })
        self.future.refresh_from_db()
        self.assertEqual(self.future.name, 'Renamed')
        self.client.post(reverse('events:delete', args=[self.future.pk]))
        self.assertFalse(Event.objects.filter(pk=self.future.pk).exists())


class AttendanceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        from members.models import Member
        get_user_model().objects.create_user('tester', password='pw-12345-xyz')
        cls.event = Event.objects.create(name='Sunday Service', start_time=timezone.now() - timedelta(days=1))
        cls.neo = Member.objects.create(first_name='Neo', last_name='Molefe')
        cls.kago = Member.objects.create(first_name='Kago', last_name='Seretse')
        cls.url = reverse('events:attendance', args=[cls.event.pk])

    def setUp(self):
        self.client.login(username='tester', password='pw-12345-xyz')

    def test_requires_login(self):
        self.client.logout()
        self.assertEqual(self.client.get(self.url).status_code, 302)

    def test_page_lists_members(self):
        response = self.client.get(self.url)
        self.assertContains(response, 'Neo Molefe')
        self.assertContains(response, 'Kago Seretse')

    def test_saving_records_attendance(self):
        response = self.client.post(self.url, {'members': [self.neo.pk]})
        self.assertRedirects(response, self.event.get_absolute_url())
        self.assertEqual(list(self.event.attendances.values_list('member_id', flat=True)), [self.neo.pk])

    def test_saving_again_updates_the_list(self):
        self.client.post(self.url, {'members': [self.neo.pk]})
        self.client.post(self.url, {'members': [self.kago.pk]})
        self.assertEqual(list(self.event.attendances.values_list('member_id', flat=True)), [self.kago.pk])

    def test_ticked_members_are_prechecked(self):
        self.client.post(self.url, {'members': [self.neo.pk]})
        self.assertIn(self.neo.pk, self.client.get(self.url).context['attended_ids'])

    def test_invalid_ids_are_ignored_and_no_duplicates(self):
        self.client.post(self.url, {'members': [self.neo.pk, self.neo.pk, 'abc', '99999']})
        self.assertEqual(self.event.attendances.count(), 1)

    def test_clearing_everyone_removes_all_attendance(self):
        self.client.post(self.url, {'members': [self.neo.pk, self.kago.pk]})
        self.client.post(self.url, {})
        self.assertEqual(self.event.attendances.count(), 0)

    def test_past_events_list_shows_count(self):
        self.client.post(self.url, {'members': [self.neo.pk, self.kago.pk]})
        past = self.client.get(reverse('events:list')).context['past']
        self.assertEqual(past[0].attendee_count, 2)
