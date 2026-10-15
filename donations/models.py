from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils import timezone


class Donation(models.Model):
    class Type(models.TextChoices):
        TITHES = 'Tithes', 'Tithes'
        OTHER = 'Other Givings', 'Other Givings'

    donation_type = models.CharField(max_length=20, choices=Type.choices, default=Type.TITHES)
    amount = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))]
    )
    date = models.DateField(default=timezone.localdate)
    member = models.ForeignKey(
        'members.Member', null=True, blank=True, on_delete=models.SET_NULL,
        related_name='donations', help_text='Leave empty for an anonymous gift.',
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-date', '-id']

    def __str__(self):
        return f"{self.donation_type} - {self.amount}"

    def get_absolute_url(self):
        return reverse('donations:detail', args=[self.pk])
