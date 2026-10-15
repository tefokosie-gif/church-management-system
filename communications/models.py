from django.conf import settings
from django.db import models
from django.urls import reverse


class Message(models.Model):
    """A message sent by a staff user to a church member."""

    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name='sent_messages'
    )
    recipient = models.ForeignKey('members.Member', on_delete=models.CASCADE, related_name='messages')
    subject = models.CharField(max_length=120)
    content = models.TextField()
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-sent_at']

    def __str__(self):
        return f"{self.subject} -> {self.recipient}"

    def get_absolute_url(self):
        return reverse('communications:detail', args=[self.pk])
