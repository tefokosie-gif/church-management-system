from django.urls import path

from . import views

app_name = 'communications'

urlpatterns = [
    path('', views.MessageListView.as_view(), name='list'),
    path('new/', views.MessageCreateView.as_view(), name='create'),
    path('<int:pk>/', views.MessageDetailView.as_view(), name='detail'),
]
