from django import forms

from church_management.forms import StyledModelForm

from .models import Donation


class DonationForm(StyledModelForm):
    class Meta:
        model = Donation
        fields = ['donation_type', 'amount', 'date', 'member', 'notes']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'notes': forms.Textarea(attrs={'rows': 3}),
            'amount': forms.NumberInput(attrs={'step': '0.01', 'min': '0.01'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['member'].empty_label = 'Anonymous'
