from django.urls import path

from . import exports
from .views import DashboardView, ReportsView

app_name = 'analytics'

urlpatterns = [
    path('', DashboardView.as_view(), name='dashboard'),
    path('reports/', ReportsView.as_view(), name='reports'),
    path('reports/export/members.csv', exports.MembersExport.as_view(), name='export_members'),
    path('reports/export/donations.csv', exports.DonationsExport.as_view(), name='export_donations'),
    path('reports/export/attendance.csv', exports.AttendanceExport.as_view(), name='export_attendance'),
]
