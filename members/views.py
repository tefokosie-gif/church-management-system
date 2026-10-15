from django.db.models import Q, Sum
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin

from church_management.mixins import AppDeleteMixin, AppFormMixin, ListPageMixin

from .forms import MemberForm
from .models import Member


class MemberListView(ListPageMixin, ListView):
    model = Member
    template_name = 'members/member_list.html'
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset()
        self.q = self.request.GET.get('q', '').strip()
        self.category = self.request.GET.get('category', '')
        if self.q:
            queryset = queryset.filter(
                Q(first_name__icontains=self.q)
                | Q(last_name__icontains=self.q)
                | Q(email__icontains=self.q)
            )
        if self.category:
            queryset = queryset.filter(category=self.category)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(q=self.q, category=self.category, categories=Member.Category.choices)
        return context


class MemberDetailView(LoginRequiredMixin, DetailView):
    model = Member
    template_name = 'members/member_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        donations = self.object.donations.all()
        context['recent_donations'] = donations[:5]
        context['total_given'] = donations.aggregate(total=Sum('amount'))['total'] or 0
        return context


class MemberCreateView(AppFormMixin, CreateView):
    model = Member
    form_class = MemberForm
    title = 'Add a member'
    success_url = reverse_lazy('members:list')
    success_message = '%(first_name)s %(last_name)s was added.'


class MemberUpdateView(AppFormMixin, UpdateView):
    model = Member
    form_class = MemberForm
    title = 'Edit member'
    success_url = reverse_lazy('members:list')
    success_message = 'Changes to %(first_name)s %(last_name)s were saved.'


class MemberDeleteView(AppDeleteMixin, DeleteView):
    model = Member
    title = 'Delete member'
    success_url = reverse_lazy('members:list')
    success_message = 'The member was deleted.'
