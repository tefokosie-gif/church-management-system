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


class Attendance(models.Model):
    """Records that one member attended one event."""

    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='attendances')
    member = models.ForeignKey('members.Member', on_delete=models.CASCADE, related_name='attendances')

    class Meta:
        ordering = ['member__last_name', 'member__first_name']
        constraints = [
            models.UniqueConstraint(fields=['event', 'member'], name='one_attendance_per_member_per_event'),
        ]

    def __str__(self):
        return f"{self.member} at {self.event}"
