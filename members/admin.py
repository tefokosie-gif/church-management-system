from django.contrib import admin

from .models import Member


@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'category', 'email', 'phone', 'joined')
    list_filter = ('category',)
    search_fields = ('first_name', 'last_name', 'email')
