"""
Commande à lancer périodiquement (ex. toutes les minutes via cron ou Planificateur de tâches)
pour que les tickets passent automatiquement en « en_cours » à l'heure de début
et en « termine » à l'heure de fin, même si personne ne charge une page.
"""
from django.core.management.base import BaseCommand
from laverie.models import Reservation


class Command(BaseCommand):
    help = "Met à jour le statut des réservations : termine si fin dépassée, en_cours si créneau commencé."

    def handle(self, *args, **options):
        n_termines = Reservation.marquer_tickets_termines()
        n_en_cours = Reservation.marquer_tickets_en_cours()
        if n_termines or n_en_cours:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Terminés: {n_termines}, En cours: {n_en_cours}"
                )
            )
        else:
            self.stdout.write("Aucun statut à mettre à jour.")
