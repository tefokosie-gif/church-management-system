from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register('members', views.MemberViewSet, basename='member')
router.register('donations', views.DonationViewSet, basename='donation')
router.register('events', views.EventViewSet, basename='event')

urlpatterns = [
    path('summary/', views.SummaryView.as_view(), name='api-summary'),
    path('', include(router.urls)),
]
