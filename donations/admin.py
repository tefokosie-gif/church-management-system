from django.contrib import admin

from .models import Donation


@admin.register(Donation)
class DonationAdmin(admin.ModelAdmin):
    list_display = ('date', 'donation_type', 'amount', 'member')
    list_filter = ('donation_type', 'date')
    date_hierarchy = 'date'
