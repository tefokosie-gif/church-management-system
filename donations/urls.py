from django.urls import path

from . import views

app_name = 'donations'

urlpatterns = [
    path('', views.DonationListView.as_view(), name='list'),
    path('add/', views.DonationCreateView.as_view(), name='create'),
    path('<int:pk>/', views.DonationDetailView.as_view(), name='detail'),
    path('<int:pk>/edit/', views.DonationUpdateView.as_view(), name='update'),
    path('<int:pk>/delete/', views.DonationDeleteView.as_view(), name='delete'),
]
