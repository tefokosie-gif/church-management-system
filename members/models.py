from datetime import date

from django.db import models
from django.urls import reverse
from django.utils import timezone


class Member(models.Model):
    class Category(models.TextChoices):
        ADULT = 'Adult', 'Adult'
        TEEN = 'Teen', 'Teen'
        SUNDAY_SCHOOL = 'Sunday School', 'Sunday School'
        VISITOR = 'Visitor', 'Visitor'

    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    birth_date = models.DateField(null=True, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.ADULT)
    joined = models.DateField(default=timezone.localdate)

    class Meta:
        ordering = ['last_name', 'first_name']

    def __str__(self):
        return self.full_name

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def age(self):
        if not self.birth_date:
            return None
        today = date.today()
        had_birthday = (today.month, today.day) >= (self.birth_date.month, self.birth_date.day)
        return today.year - self.birth_date.year - (0 if had_birthday else 1)

    def get_absolute_url(self):
        return reverse('members:detail', args=[self.pk])
