"""
Middleware qui met à jour le statut des tickets à chaque requête :
- « termine » si l'heure de fin est dépassée
- « en_cours » si l'heure de début est atteinte

Ainsi le ticket démarre automatiquement à son heure, dès qu'un utilisateur charge une page.
"""
from laverie.models import Reservation


class MiseAJourStatutTicketsMiddleware:
    """Appelle marquer_tickets_termines et marquer_tickets_en_cours à chaque requête."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Ne pas exécuter sur les requêtes statiques / médias pour alléger
        path = request.path
        if not path.startswith(("/static/", "/media/", "/favicon")):
            Reservation.marquer_tickets_termines()
            Reservation.marquer_tickets_en_cours()
        return self.get_response(request)
