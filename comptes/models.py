import os
from django.utils.timezone import now
from django.contrib.auth.models import AbstractUser
from django.db import models

def user_photo_upload_to(instance, filename):
    """
    Renomme la photo de l'utilisateur au format :
    user_<id>_<timestamp>.<extension>
    """
    ext = filename.split('.')[-1]
    timestamp = now().strftime("%Y%m%d%H%M%S")
    filename = f"user_{instance.id or 'new'}_{timestamp}.{ext}"
    return os.path.join("users/photos", filename)


class CustomUser(AbstractUser):
    USER_TYPES = (
        ('ADMIN', 'Administrateur'),
        ('client', 'Client'),
        ('vendeur', 'Vendeur'),
        ('coursier', 'Coursier'),
    )
    user_type = models.CharField(max_length=22, choices=USER_TYPES, default="client")
    email = models.EmailField('Adresse email', unique=True,max_length=50)
    telephone = models.CharField(max_length=20, unique=True, blank=True)
    photo = models.ImageField(upload_to=user_photo_upload_to, null=True, blank=True)
    is_premium = models.BooleanField(default=False)
    GENRE = (('masculin', 'Masculin'), ('feminin', 'Féminin'))
    genre = models.CharField(max_length=22, choices=GENRE, null=True, blank=True)
    date_inscription = models.DateField(auto_now_add=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    last_activity = models.DateTimeField(null=True, blank=True, verbose_name="Dernière activité")
    REQUIRED_FIELDS = ['email', 'user_type']

    def save(self, *args, **kwargs):
        if not self.username and self.telephone:
            self.username = self.telephone
        super().save(*args, **kwargs)

    @property
    def display_name(self):
        return f"{self.first_name} {self.last_name}" if self.first_name or self.last_name else self.username
    
    @property
    def is_online(self):
        """Vérifie si l'utilisateur est en ligne (dernière activité < 5 minutes)"""
        if not self.last_activity:
            return False
        from django.utils import timezone
        from datetime import timedelta
        return timezone.now() - self.last_activity < timedelta(minutes=5)
    
    def update_activity(self):
        """Met à jour la dernière activité de l'utilisateur"""
        from django.utils import timezone
        self.last_activity = timezone.now()
        self.save(update_fields=['last_activity'])
