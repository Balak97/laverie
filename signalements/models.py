from django.db import models
from django.conf import settings


class Signalement(models.Model):
    """Problème signalé par un utilisateur (étudiant)."""
    STATUT_CHOICES = [
        ('nouveau', 'Nouveau'),
        ('en_cours', 'En cours'),
        ('resolu', 'Résolu'),
    ]
    utilisateur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='signalements',
    )
    description = models.TextField(help_text="Explication du problème")
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='nouveau')
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date_creation']
        verbose_name = 'Signalement'
        verbose_name_plural = 'Signalements'

    def __str__(self):
        return f"Signalement #{self.pk} — {self.utilisateur} — {self.date_creation.date()}"
