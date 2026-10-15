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
