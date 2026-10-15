from django.contrib import admin

from .models import Message


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('subject', 'recipient', 'sender', 'sent_at')
    search_fields = ('subject', 'content')
