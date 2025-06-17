from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser

class CustomUserAdmin(UserAdmin):
    model = CustomUser

    # Affiche toutes les infos importantes dans la liste
    list_display = [
        'username', 'email', 'first_name', 'last_name',
        'role', 'birth_date', 'sex',
        'is_active', 'is_staff', 'is_superuser'
    ]

    # Supprime les filtres
    list_filter = []  # ou simplement ne pas le définir du tout

    # Fiche de l'utilisateur : affiche tout
    fieldsets = UserAdmin.fieldsets + (
        ('Informations supplémentaires', {
            'fields': ('role', 'birth_date', 'sex'),
        }),
    )

    # Pour le formulaire d'ajout dans l'admin
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Informations supplémentaires', {
            'fields': ('role', 'birth_date', 'sex'),
        }),
    )

    search_fields = ['username', 'email', 'first_name', 'last_name']
    ordering = ['username']

admin.site.register(CustomUser, CustomUserAdmin)
