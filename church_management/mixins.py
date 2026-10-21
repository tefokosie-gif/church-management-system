"""Small building blocks shared by the views of every app."""
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin

# Each view that uses these sets `permission_required`, e.g. 'members.add_member'.
# Anonymous visitors are sent to the login page; signed-in users without the permission get a 403 page.


class ListPageMixin(PermissionRequiredMixin):
    """Permission check + a `querystring` (filters without ?page=) for pagination links."""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        params = self.request.GET.copy()
        params.pop('page', None)
        context['querystring'] = params.urlencode()
        return context


class AppFormMixin(PermissionRequiredMixin, SuccessMessageMixin):
    """Permission check + shared form template + success flash message."""

    template_name = 'form.html'
    title = ''

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = self.title
        context['cancel_url'] = str(self.success_url)
        return context


class AppDeleteMixin(PermissionRequiredMixin, SuccessMessageMixin):
    """Permission check + shared confirmation page + success flash message."""

    template_name = 'confirm_delete.html'
    title = ''

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = self.title
        context['cancel_url'] = self.object.get_absolute_url()
        return context
