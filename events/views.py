from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from church_management.mixins import AppDeleteMixin, AppFormMixin
from members.models import Member

from .forms import EventForm
from .models import Attendance, Event


class EventListView(PermissionRequiredMixin, ListView):
    permission_required = 'events.view_event'
    model = Event
    template_name = 'events/event_list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        now = timezone.now()
        context['upcoming'] = Event.objects.filter(start_time__gte=now).order_by('start_time')
        context['past'] = (
            Event.objects.filter(start_time__lt=now)
            .annotate(attendee_count=Count('attendances'))
            .order_by('-start_time')[:10]
        )
        return context


class EventDetailView(PermissionRequiredMixin, DetailView):
    permission_required = 'events.view_event'
    model = Event
    template_name = 'events/event_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['attendances'] = self.object.attendances.select_related('member')
        return context


class EventAttendanceView(PermissionRequiredMixin, View):
    permission_required = 'events.change_event'
    """A checklist of every member; ticked members are saved as having attended."""

    template_name = 'events/event_attendance.html'

    def get(self, request, pk):
        event = get_object_or_404(Event, pk=pk)
        context = {
            'event': event,
            'members': Member.objects.all(),
            'attended_ids': set(event.attendances.values_list('member_id', flat=True)),
        }
        return render(request, self.template_name, context)

    def post(self, request, pk):
        event = get_object_or_404(Event, pk=pk)
        valid_ids = set(Member.objects.values_list('id', flat=True))
        chosen = {int(i) for i in request.POST.getlist('members') if i.isdigit()} & valid_ids
        current = set(event.attendances.values_list('member_id', flat=True))

        event.attendances.filter(member_id__in=current - chosen).delete()
        Attendance.objects.bulk_create([Attendance(event=event, member_id=i) for i in chosen - current])

        messages.success(request, f'Attendance saved: {len(chosen)} present.')
        return redirect(event)


class EventCreateView(AppFormMixin, CreateView):
    permission_required = 'events.add_event'
    model = Event
    form_class = EventForm
    title = 'Add an event'
    success_url = reverse_lazy('events:list')
    success_message = '%(name)s was added to the calendar.'


class EventUpdateView(AppFormMixin, UpdateView):
    permission_required = 'events.change_event'
    model = Event
    form_class = EventForm
    title = 'Edit event'
    success_url = reverse_lazy('events:list')
    success_message = '%(name)s was updated.'


class EventDeleteView(AppDeleteMixin, DeleteView):
    permission_required = 'events.delete_event'
    model = Event
    title = 'Delete event'
    success_url = reverse_lazy('events:list')
    success_message = 'The event was deleted.'
