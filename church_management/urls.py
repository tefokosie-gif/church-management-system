from django.conf import settings
from django.contrib import admin
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import include, path

from .forms import StyledAuthenticationForm

admin.site.site_header = 'Church Manager admin'
admin.site.site_title = 'Church Manager admin'

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/login/', LoginView.as_view(
        template_name='accounts/login.html',
        authentication_form=StyledAuthenticationForm,
        redirect_authenticated_user=True,
        extra_context={
            'demo_mode': settings.DEMO_MODE,
            'demo_username': settings.DEMO_USERNAME,
            'demo_password': settings.DEMO_PASSWORD,
        },
    ), name='login'),
    path('accounts/logout/', LogoutView.as_view(), name='logout'),
    path('', include('analytics.urls')),
    path('members/', include('members.urls')),
    path('donations/', include('donations.urls')),
    path('events/', include('events.urls')),
    path('messages/', include('communications.urls')),
]
