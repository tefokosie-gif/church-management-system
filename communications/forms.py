from django import forms

from church_management.forms import StyledModelForm
from members.models import Member

from .models import Message


class MessageForm(StyledModelForm):
    class Meta:
        model = Message
        fields = ['recipient', 'subject', 'content']
        widgets = {'content': forms.Textarea(attrs={'rows': 6})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only members with an email address can receive a message.
        self.fields['recipient'].queryset = Member.objects.exclude(email='')
