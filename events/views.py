from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from church_management.mixins import AppDeleteMixin, AppFormMixin

from .forms import EventForm
from .models import Event


class EventListView(LoginRequiredMixin, ListView):
    model = Event
    template_name = 'events/event_list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        now = timezone.now()
        context['upcoming'] = Event.objects.filter(start_time__gte=now).order_by('start_time')
        context['past'] = Event.objects.filter(start_time__lt=now).order_by('-start_time')[:10]
        return context


class EventDetailView(LoginRequiredMixin, DetailView):
    model = Event
    template_name = 'events/event_detail.html'


class EventCreateView(AppFormMixin, CreateView):
    model = Event
    form_class = EventForm
    title = 'Add an event'
    success_url = reverse_lazy('events:list')
    success_message = '%(name)s was added to the calendar.'


class EventUpdateView(AppFormMixin, UpdateView):
    model = Event
    form_class = EventForm
    title = 'Edit event'
    success_url = reverse_lazy('events:list')
    success_message = '%(name)s was updated.'


class EventDeleteView(AppDeleteMixin, DeleteView):
    model = Event
    title = 'Delete event'
    success_url = reverse_lazy('events:list')
    success_message = 'The event was deleted.'
