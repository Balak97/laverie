from django.contrib import admin
from .models import Machine, FonctionMachine, Reservation, MessageLaverie


@admin.register(MessageLaverie)
class MessageLaverieAdmin(admin.ModelAdmin):
    list_display = ('texte_short', 'ordre', 'active', 'auteur', 'date_creation')
    list_filter = ('active',)

    def texte_short(self, obj):
        return (obj.texte[:60] + '…') if len(obj.texte) > 60 else obj.texte
    texte_short.short_description = 'Message'


@admin.register(Machine)
class MachineAdmin(admin.ModelAdmin):
    list_display = ('nom', 'ordre', 'active', 'date_creation')


@admin.register(FonctionMachine)
class FonctionMachineAdmin(admin.ModelAdmin):
    list_display = ('machine', 'nom', 'duree_minutes', 'ordre', 'active')


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ('utilisateur', 'machine', 'fonction', 'debut', 'fin', 'statut', 'date_creation')
    list_filter = ('statut', 'machine')
