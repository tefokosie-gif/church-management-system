from django import forms

from church_management.forms import StyledModelForm

from .models import Member


class MemberForm(StyledModelForm):
    class Meta:
        model = Member
        fields = ['first_name', 'last_name', 'category', 'birth_date', 'email', 'phone', 'joined']
        widgets = {
            'birth_date': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'joined': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
        }
