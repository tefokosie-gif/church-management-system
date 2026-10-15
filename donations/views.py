from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from church_management.mixins import AppDeleteMixin, AppFormMixin, ListPageMixin

from .forms import DonationForm
from .models import Donation


class DonationListView(ListPageMixin, ListView):
    model = Donation
    template_name = 'donations/donation_list.html'
    paginate_by = 12

    def get_queryset(self):
        queryset = super().get_queryset().select_related('member')
        self.dtype = self.request.GET.get('type', '')
        if self.dtype:
            queryset = queryset.filter(donation_type=self.dtype)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        total = self.get_queryset().aggregate(total=Sum('amount'))['total'] or 0
        context.update(dtype=self.dtype, types=Donation.Type.choices, total=total)
        return context


class DonationDetailView(LoginRequiredMixin, DetailView):
    model = Donation
    template_name = 'donations/donation_detail.html'


class DonationCreateView(AppFormMixin, CreateView):
    model = Donation
    form_class = DonationForm
    title = 'Record a donation'
    success_url = reverse_lazy('donations:list')
    success_message = 'Donation recorded.'


class DonationUpdateView(AppFormMixin, UpdateView):
    model = Donation
    form_class = DonationForm
    title = 'Edit donation'
    success_url = reverse_lazy('donations:list')
    success_message = 'Donation updated.'


class DonationDeleteView(AppDeleteMixin, DeleteView):
    model = Donation
    title = 'Delete donation'
    success_url = reverse_lazy('donations:list')
    success_message = 'The donation was deleted.'
