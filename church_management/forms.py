from django import forms
from django.contrib.auth.forms import AuthenticationForm


class StyledModelForm(forms.ModelForm):
    """A ModelForm that adds the app's CSS classes to every widget."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                continue
            css = 'input select' if isinstance(widget, forms.Select) else 'input'
            widget.attrs['class'] = f"{widget.attrs.get('class', '')} {css}".strip()


class StyledAuthenticationForm(AuthenticationForm):
    """Login form with the app's styling."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update(
            {'class': 'input', 'placeholder': 'Username', 'autofocus': True}
        )
        self.fields['password'].widget.attrs.update(
            {'class': 'input', 'placeholder': 'Password'}
        )
