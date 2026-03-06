from django.contrib import admin
from .models import Signalement


@admin.register(Signalement)
class SignalementAdmin(admin.ModelAdmin):
    list_display = ('pk', 'utilisateur', 'statut', 'date_creation')
    list_filter = ('statut',)
