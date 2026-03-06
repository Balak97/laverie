from django.utils import timezone
from django.utils.deprecation import MiddlewareMixin


class UpdateLastActivityMiddleware(MiddlewareMixin):
    """Middleware pour mettre à jour la dernière activité de l'utilisateur"""
    
    def process_request(self, request):
        """Met à jour la dernière activité à chaque requête pour les utilisateurs connectés"""
        if request.user.is_authenticated:
            # Mettre à jour seulement si la dernière activité est ancienne de plus de 1 minute
            # pour éviter trop de requêtes à la base de données
            if not request.user.last_activity or (timezone.now() - request.user.last_activity).total_seconds() > 60:
                request.user.last_activity = timezone.now()
                request.user.save(update_fields=['last_activity'])
        return None

