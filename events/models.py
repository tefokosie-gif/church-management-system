from django.db import models
from django.urls import reverse
from django.utils import timezone


class Event(models.Model):
    name = models.CharField(max_length=100)
    start_time = models.DateTimeField(default=timezone.now)
    location = models.CharField(max_length=120, blank=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ['start_time']

    def __str__(self):
        return self.name

    @property
    def is_upcoming(self):
        return self.start_time >= timezone.now()

    def get_absolute_url(self):
        return reverse('events:detail', args=[self.pk])
