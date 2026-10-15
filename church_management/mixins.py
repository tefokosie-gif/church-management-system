"""Small building blocks shared by the views of every app."""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin


class ListPageMixin(LoginRequiredMixin):
    """Login required + a `querystring` (filters without ?page=) for pagination links."""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        params = self.request.GET.copy()
        params.pop('page', None)
        context['querystring'] = params.urlencode()
        return context


class AppFormMixin(LoginRequiredMixin, SuccessMessageMixin):
    """Login required + shared form template + success flash message."""

    template_name = 'form.html'
    title = ''

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = self.title
        context['cancel_url'] = str(self.success_url)
        return context


class AppDeleteMixin(LoginRequiredMixin, SuccessMessageMixin):
    """Login required + shared confirmation page + success flash message."""

    template_name = 'confirm_delete.html'
    title = ''

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = self.title
        context['cancel_url'] = self.object.get_absolute_url()
        return context
