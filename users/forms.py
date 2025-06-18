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
    
    # Nouveaux champs basés sur le CSV
    employee_id = forms.CharField(
        max_length=10,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ID Employé (ex: E001)'})
    )
    
    departement = forms.ChoiceField(
        choices=[('', 'Sélectionnez un département')] + list(CustomUser.DEPARTMENT_CHOICES),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    poste = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Votre poste'})
    )
    
    date_embauche = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    
    salaire = forms.FloatField(
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Salaire annuel'})
    )
    
    regime_sante = forms.ChoiceField(
        choices=CustomUser.REGIME_SANTE_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'first_name', 'last_name', 'birth_date', 'sex', 
                 'employee_id', 'departement', 'poste', 'date_embauche', 'salaire', 
                 'regime_sante', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Ajoute 'form-control' aux widgets des autres champs
        for field_name, field in self.fields.items():
            if field.widget.attrs.get('class') is None:
                field.widget.attrs['class'] = 'form-control'

