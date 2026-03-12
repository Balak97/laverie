from django.db import models
from django.conf import settings


class Conversation(models.Model):
    participant1 = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='conversations_as_p1'
    )
    participant2 = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='conversations_as_p2'
    )
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date_creation']

   


class Message(models.Model):
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='messages'
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sent_messages'
    )
    contenu = models.TextField(blank=True)
    lu = models.BooleanField(default=False)
    date_envoi = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['date_envoi']

    def __str__(self):
        return ""
