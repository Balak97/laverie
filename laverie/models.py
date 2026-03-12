from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.db.models import Max


class MessageLaverie(models.Model):
    """Message publié par un agent, affiché en défilement en haut des machines."""
    texte = models.CharField(max_length=500, help_text="Message affiché aux utilisateurs")
    ordre = models.PositiveSmallIntegerField(default=0, help_text="Ordre d'affichage (plus petit = en premier)")
    active = models.BooleanField(default=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    auteur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='messages_laverie',
    )

    class Meta:
        ordering = ['ordre', '-date_creation']
        verbose_name = 'Message laverie'
        verbose_name_plural = 'Messages laverie'

    def __str__(self):
        return (self.texte[:50] + '…') if len(self.texte) > 50 else self.texte


class Machine(models.Model):
    """Machine à laver dans la salle."""
    nom = models.CharField(max_length=100, help_text="Ex: Machine 1, Lave-linge A")
    ordre = models.PositiveSmallIntegerField(default=0, help_text="Ordre d'affichage")
    active = models.BooleanField(default=True)
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['ordre', 'nom']

    def __str__(self):
        return self.nom


class FonctionMachine(models.Model):
    """Fonction/programme d'une machine (coton, jeans, délicat, etc.) avec durée."""
    machine = models.ForeignKey(Machine, on_delete=models.CASCADE, related_name='fonctions')
    nom = models.CharField(max_length=80, help_text="Ex: Coton, Jeans, Délicat")
    duree_minutes = models.PositiveIntegerField(help_text="Durée du cycle en minutes")
    ordre = models.PositiveSmallIntegerField(default=0)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ['machine', 'ordre', 'nom']
        unique_together = [['machine', 'nom']]

    def __str__(self):
        return f"{self.machine.nom} — {self.nom} ({self.duree_minutes} min)"

    def duree_affichage(self):
        """Durée formatée en heures et minutes (ex: 1 h 30 min, 45 min)."""
        h = self.duree_minutes // 60
        m = self.duree_minutes % 60
        if h and m:
            return f"{h} h {m} min"
        if h:
            return f"{h} h"
        return f"{m} min"


# Limite : même personne, même machine, même jour
MAX_TICKETS_SAME_DAY_SAME_MACHINE = 5


class Reservation(models.Model):
    """Ticket / réservation d'un créneau sur une machine."""
    STATUT_CHOICES = [
        ('reserve', _('Reserved')),
        ('en_cours', _('In progress')),
        ('termine', _('Completed')),
        ('annule', _('Cancelled')),
    ]
    utilisateur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reservations_laverie'
    )
    machine = models.ForeignKey(Machine, on_delete=models.CASCADE, related_name='reservations')
    fonction = models.ForeignKey(
        FonctionMachine,
        on_delete=models.CASCADE,
        related_name='reservations',
        null=True,
        blank=True
    )
    debut = models.DateTimeField()
    fin = models.DateTimeField()
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='reserve')
    date_creation = models.DateTimeField(auto_now_add=True)
    numero = models.PositiveIntegerField(
        unique=True,
        null=True,
        blank=True,
        help_text="Numéro de ticket (séquentiel, affiché à l'utilisateur)",
    )

    class Meta:
        ordering = ['-debut']

    def __str__(self):
        return f"{self.utilisateur} — {self.machine} — {self.debut}"

    def save(self, *args, **kwargs):
        if self.numero is None:
            agg = Reservation.objects.aggregate(Max('numero'))
            next_num = (agg['numero__max'] or 0) + 1
            self.numero = next_num
        super().save(*args, **kwargs)

    @classmethod
    def count_user_same_day_machine(cls, user, machine, day_date):
        """Nombre de réservations (hors annulées) de cet utilisateur sur cette machine pour ce jour."""
        return cls.objects.filter(
            utilisateur=user, machine=machine, debut__date=day_date
        ).exclude(statut='annule').count()

    def duree_minutes(self):
        """Durée réelle du créneau (debut → fin) en minutes. Prend en compte les prolongations/réductions."""
        if self.debut and self.fin:
            delta = self.fin - self.debut
            return int(delta.total_seconds() / 60)
        if self.fonction:
            return self.fonction.duree_minutes
        return 0

    def duree_affichage(self):
        """Durée formatée (ex: 1 h 30 min, 45 min). Utilise la durée réelle du créneau (après modif)."""
        n = self.duree_minutes()
        if n >= 60:
            return f"{n // 60} h {n % 60} min" if n % 60 else f"{n // 60} h"
        return f"{n} min"

    @classmethod
    def marquer_tickets_termines(cls):
        """Passe en 'termine' les réservations dont l'heure de fin est dépassée."""
        from django.utils import timezone
        now = timezone.now()
        return cls.objects.filter(
            statut__in=('reserve', 'en_cours'),
            fin__lt=now,
        ).update(statut='termine')

    @classmethod
    def marquer_tickets_en_cours(cls):
        """Passe en 'en_cours' les réservations dont l'heure de début est atteinte (créneau en cours)."""
        from django.utils import timezone
        now = timezone.now()
        return cls.objects.filter(
            statut='reserve',
            debut__lte=now,
            fin__gte=now,
        ).update(statut='en_cours')


class ChatMachineMessage(models.Model):
    """Message dans le chat d'une machine : échange entre les personnes ayant un ticket sur cette machine."""
    machine = models.ForeignKey(
        Machine,
        on_delete=models.CASCADE,
        related_name='chat_messages',
    )
    auteur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='chat_messages_laverie',
    )
    texte = models.TextField(max_length=1000)
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['date_creation']
        verbose_name = _('Machine chat message')
        verbose_name_plural = _('Machine chat messages')

    def __str__(self):
        return f"{self.auteur} — {self.machine}: {self.texte[:40]}…"
