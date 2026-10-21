from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase
from django.urls import reverse

from members.models import Member

from .models import Message


class MessageTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_superuser('tester', password='pw-12345-xyz')
        cls.member = Member.objects.create(first_name='Neo', last_name='Molefe', email='neo@example.com')
        cls.no_email = Member.objects.create(first_name='Kago', last_name='Seretse')

    def setUp(self):
        self.client.login(username='tester', password='pw-12345-xyz')

    def test_send_message_saves_and_emails(self):
        response = self.client.post(reverse('communications:create'), {
            'recipient': self.member.pk, 'subject': 'Hello', 'content': 'See you Sunday.',
        })
        self.assertRedirects(response, reverse('communications:list'))
        message = Message.objects.get()
        self.assertEqual(message.sender, self.user)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['neo@example.com'])

    def test_cannot_message_member_without_email(self):
        response = self.client.post(reverse('communications:create'), {
            'recipient': self.no_email.pk, 'subject': 'Hello', 'content': 'Hi',
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Message.objects.count(), 0)

    def test_list_and_detail(self):
        message = Message.objects.create(sender=self.user, recipient=self.member, subject='Hi there', content='Body text')
        self.assertContains(self.client.get(reverse('communications:list')), 'Hi there')
        self.assertContains(self.client.get(message.get_absolute_url()), 'Body text')

    def test_recipient_prefilled_from_query_string(self):
        response = self.client.get(reverse('communications:create'), {'recipient': self.member.pk})
        self.assertEqual(response.context['form'].initial['recipient'], self.member.pk)
