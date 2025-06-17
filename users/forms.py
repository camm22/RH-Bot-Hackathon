from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import CustomUser

class CustomUserCreationForm(UserCreationForm):
    birth_date = forms.DateField(
        required=False, 
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    sex = forms.ChoiceField(
        choices=CustomUser.SEX_CHOICES, 
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'first_name', 'last_name', 'birth_date', 'sex', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Ajoute 'form-control' aux widgets des autres champs
        for field_name, field in self.fields.items():
            if field.widget.attrs.get('class') is None:
                field.widget.attrs['class'] = 'form-control'

