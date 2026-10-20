from django.contrib import admin

from .models import Attendance, Event


class AttendanceInline(admin.TabularInline):
    model = Attendance
    extra = 0
    autocomplete_fields = ['member']


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('name', 'start_time', 'location')
    search_fields = ('name', 'location')
    inlines = [AttendanceInline]
