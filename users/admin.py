from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Chat, Message

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


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    readonly_fields = ['created_at']


class ChatAdmin(admin.ModelAdmin):
    list_display = ['title', 'user', 'created_at', 'updated_at']
    list_filter = ['created_at', 'updated_at']
    search_fields = ['title', 'user__username']
    inlines = [MessageInline]


class MessageAdmin(admin.ModelAdmin):
    list_display = ['chat', 'sender', 'content_preview', 'created_at']
    list_filter = ['sender', 'created_at']
    search_fields = ['content', 'chat__title']
    
    def content_preview(self, obj):
        return obj.content[:50] + ('...' if len(obj.content) > 50 else '')
    content_preview.short_description = 'Content'


admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(Chat, ChatAdmin)
admin.site.register(Message, MessageAdmin)
