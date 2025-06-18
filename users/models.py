from django.db import models
from django.contrib.auth.models import AbstractUser

class CustomUser(AbstractUser):
    # tes champs existants
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('user', 'User'),
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='user')

    SEX_CHOICES = (
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
    )
    birth_date = models.DateField(null=True, blank=True)
    sex = models.CharField(max_length=6, choices=SEX_CHOICES, null=True, blank=True)
    
    # Nouveaux champs basés sur le CSV
    employee_id = models.CharField(max_length=10, unique=True, null=True, blank=True)
    
    DEPARTMENT_CHOICES = (
        ('IT', 'IT'),
        ('Marketing', 'Marketing'),
        ('Finance', 'Finance'),
        ('RH', 'RH'),
        ('Ventes', 'Ventes'),
        ('Recherche', 'Recherche'),
        ('Direction', 'Direction'),
    )
    departement = models.CharField(max_length=20, choices=DEPARTMENT_CHOICES, null=True, blank=True)
    
    is_manager = models.BooleanField(default=False)
    poste = models.CharField(max_length=100, null=True, blank=True)
    responsable = models.CharField(max_length=10, null=True, blank=True)  # ID du responsable
    date_embauche = models.DateField(null=True, blank=True)
    
    # Congés
    conges_droit_annuel = models.FloatField(default=25.0)
    conges_utilises = models.FloatField(default=0.0)
    conges_planifies = models.FloatField(default=0.0)
    conges_restants = models.FloatField(default=25.0)
    
    # Congés maladie
    conges_maladie_droit = models.FloatField(default=10.0)
    conges_maladie_utilises = models.FloatField(default=0.0)
    conges_maladie_restants = models.FloatField(default=10.0)
    
    # Rémunération
    salaire = models.FloatField(null=True, blank=True)
    eligible_prime = models.BooleanField(default=True)
    date_prochaine_evaluation = models.DateField(null=True, blank=True)
    
    # Avantages
    REGIME_SANTE_CHOICES = (
        ('Standard', 'Standard'),
        ('Premium', 'Premium'),
        ('Exécutif', 'Exécutif'),
    )
    regime_sante = models.CharField(max_length=20, choices=REGIME_SANTE_CHOICES, default='Standard')

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.employee_id or self.username})"

    @property
    def manager_name(self):
        if self.responsable:
            try:
                manager = CustomUser.objects.get(employee_id=self.responsable)
                return f"{manager.first_name} {manager.last_name}"
            except CustomUser.DoesNotExist:
                return "Manager non trouvé"
        return "Aucun"


class Chat(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='chats')
    title = models.CharField(max_length=200, default='New Chat')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.user.username} - {self.title}"

    @property
    def last_message(self):
        last_msg = self.messages.last()
        if last_msg:
            return last_msg.content[:50] + ('...' if len(last_msg.content) > 50 else '')
        return "Start a conversation..."


class Message(models.Model):
    SENDER_CHOICES = (
        ('user', 'User'),
        ('ai', 'AI'),
    )
    
    chat = models.ForeignKey(Chat, on_delete=models.CASCADE, related_name='messages')
    sender = models.CharField(max_length=4, choices=SENDER_CHOICES)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.chat.title} - {self.sender}: {self.content[:30]}..."
