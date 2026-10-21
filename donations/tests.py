from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from members.models import Member

from .models import Donation


class DonationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        get_user_model().objects.create_superuser('tester', password='pw-12345-xyz')
        cls.member = Member.objects.create(first_name='Neo', last_name='Molefe')
        Donation.objects.create(donation_type='Tithes', amount=Decimal('500.00'), date='2026-01-10', member=cls.member)
        Donation.objects.create(donation_type='Other Givings', amount=Decimal('100.00'), date='2026-01-11')

    def setUp(self):
        self.client.login(username='tester', password='pw-12345-xyz')

    def test_list_total_and_filter(self):
        response = self.client.get(reverse('donations:list'))
        self.assertContains(response, '600.00')
        response = self.client.get(reverse('donations:list'), {'type': 'Tithes'})
        self.assertContains(response, '500.00')
        self.assertNotContains(response, '600.00')

    def test_create_donation(self):
        response = self.client.post(reverse('donations:create'), {
            'donation_type': 'Tithes', 'amount': '250.00', 'date': '2026-02-01', 'member': self.member.pk, 'notes': '',
        })
        self.assertRedirects(response, reverse('donations:list'))
        self.assertEqual(Donation.objects.count(), 3)

    def test_amount_must_be_positive(self):
        response = self.client.post(reverse('donations:create'), {
            'donation_type': 'Tithes', 'amount': '0', 'date': '2026-02-01',
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Donation.objects.count(), 2)

    def test_deleting_member_keeps_donation(self):
        self.member.delete()
        self.assertEqual(Donation.objects.count(), 2)
        self.assertIsNone(Donation.objects.get(amount=Decimal('500.00')).member)

    def test_delete_donation(self):
        donation = Donation.objects.first()
        self.client.post(reverse('donations:delete', args=[donation.pk]))
        self.assertEqual(Donation.objects.count(), 1)
