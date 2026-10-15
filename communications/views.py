from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.mail import send_mail
from django.urls import reverse_lazy
from django.views.generic import CreateView, DetailView, ListView

from church_management.mixins import AppFormMixin, ListPageMixin

from .forms import MessageForm
from .models import Message


class MessageListView(ListPageMixin, ListView):
    model = Message
    template_name = 'communications/message_list.html'
    paginate_by = 12

    def get_queryset(self):
        return super().get_queryset().select_related('recipient', 'sender')


class MessageDetailView(LoginRequiredMixin, DetailView):
    model = Message
    template_name = 'communications/message_detail.html'


class MessageCreateView(AppFormMixin, CreateView):
    model = Message
    form_class = MessageForm
    title = 'Send a message'
    success_url = reverse_lazy('communications:list')
    success_message = 'Message sent to %(recipient)s.'

    def get_initial(self):
        initial = super().get_initial()
        recipient_id = self.request.GET.get('recipient', '')
        if recipient_id.isdigit():
            initial['recipient'] = int(recipient_id)
        return initial

    def form_valid(self, form):
        form.instance.sender = self.request.user
        response = super().form_valid(form)
        message = self.object
        send_mail(
            message.subject, message.content, settings.DEFAULT_FROM_EMAIL,
            [message.recipient.email], fail_silently=True,
        )
        return response
