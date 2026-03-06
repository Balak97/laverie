# comptes/api/app.py
import logging
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str
from rest_framework import viewsets, mixins, status
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import permissions
from django.db import models

logger = logging.getLogger(__name__)

from .serialiser import (
    UserSerializer,
    UserProfileSerializer,
    UserCreateUpdateSerializer,
)
from ..emails import (
    envoyer_email_activation,
    envoyer_email_renvoyer_activation,
    envoyer_email_password_reset,
)
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError

CustomUser = get_user_model()


class NoDeleteModelViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    pass


class UserViewSet(NoDeleteModelViewSet):
    queryset = CustomUser.objects.all()

    def get_queryset(self):
        user = self.request.user
        base_qs = CustomUser.objects.all()

        if self.action == 'retrieve':
            base_qs = base_qs.prefetch_related(
                models.Prefetch('itineraires'),
                models.Prefetch('demandes_colis'),
            )

        if user.is_authenticated and user.user_type == 'ADMIN':
            return base_qs
        return base_qs.filter(id=user.id) if user.is_authenticated else base_qs.none()

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return UserProfileSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return UserCreateUpdateSerializer
        return UserSerializer

    def get_permissions(self):
        if self.action == 'create':
            return [AllowAny()]
        if self.action in ['resend_activation', 'activate', 'password_reset', 'password_reset_confirm']:
            return [AllowAny()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        user = serializer.save()
        # Comportement comme le web : compte inactif jusqu'à activation (sauf ADMIN créé par un admin)
        if user.user_type != 'ADMIN':
            user.is_active = False
            user.save(update_fields=['is_active'])
            try:
                envoyer_email_activation(user, self.request)
                if getattr(settings, 'DEBUG', False):
                    logger.info(
                        "Email d'activation envoyé pour %s (DEBUG: voir la console si EMAIL_BACKEND=console)",
                        user.email,
                    )
            except Exception as e:
                # Ne pas faire échouer la création, mais tracer l'échec pour diagnostic
                logger.exception(
                    "Échec envoi email d'activation à %s: %s. "
                    "Vérifiez EMAIL_BACKEND, SMTP (DEBUG=False) ou consultez la console (DEBUG=True).",
                    user.email,
                    e,
                )

    @action(detail=False, methods=['post'], url_path='resend-activation')
    def resend_activation(self, request):
        """
        Renvoie l'email d'activation pour un compte inactif.
        Body: { "email": "user@example.com" }
        """
        email = (request.data.get('email') or '').strip().lower()
        if not email:
            return Response(
                {'error': "Veuillez saisir une adresse email."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            user = CustomUser.objects.get(email=email, is_active=False)
        except CustomUser.DoesNotExist:
            return Response(
                {'error': "Aucun compte inactif trouvé pour cet email."},
                status=status.HTTP_404_NOT_FOUND,
            )
        try:
            envoyer_email_renvoyer_activation(user, request)
            return Response({
                'success': True,
                'message': "Un lien d'activation a été envoyé à votre adresse email.",
            })
        except Exception as e:
            return Response(
                {'error': f"L'envoi de l'email a échoué: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=['post'], url_path='activate')
    def activate(self, request):
        """
        Active un compte à partir du lien reçu par email.
        Body: { "uidb64": "...", "token": "..." }
        """
        uidb64 = request.data.get('uidb64') or ''
        token = request.data.get('token') or ''
        if not uidb64 or not token:
            return Response(
                {'error': "Paramètres uidb64 et token requis."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = CustomUser.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
            return Response(
                {'error': "Lien d'activation invalide ou expiré."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not default_token_generator.check_token(user, token):
            return Response(
                {'error': "Lien d'activation invalide ou expiré."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user.is_active = True
        user.save(update_fields=['is_active'])
        return Response({
            'success': True,
            'message': "Votre compte a été activé. Vous pouvez vous connecter.",
        })

    @action(detail=False, methods=['post'], url_path='password-reset')
    def password_reset(self, request):
        """
        Mot de passe oublié : envoie un email avec un lien de réinitialisation.
        Body: { "email": "user@example.com" }
        """
        email = (request.data.get('email') or '').strip().lower()
        if not email:
            return Response(
                {'error': "Veuillez saisir une adresse email."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user = CustomUser.objects.filter(email=email, is_active=True).first()
        if not user:
            return Response(
                {'error': "Aucun compte actif n'est associé à cette adresse email."},
                status=status.HTTP_404_NOT_FOUND,
            )
        try:
            envoyer_email_password_reset(user, request)
            return Response({
                'success': True,
                'message': "Un lien de réinitialisation a été envoyé à votre adresse email.",
            })
        except Exception as e:
            logger.exception("Échec envoi email mot de passe oublié: %s", e)
            return Response(
                {'error': f"L'envoi de l'email a échoué: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=['post'], url_path='password-reset-confirm')
    def password_reset_confirm(self, request):
        """
        Réinitialise le mot de passe avec le token reçu par email.
        Body: { "uidb64": "...", "token": "...", "new_password": "..." }
        """
        uidb64 = request.data.get('uidb64') or ''
        token = request.data.get('token') or ''
        new_password = request.data.get('new_password')
        if not uidb64 or not token:
            return Response(
                {'error': "Paramètres uidb64 et token requis."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not new_password:
            return Response(
                {'error': "Le champ new_password est requis."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = CustomUser.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
            return Response(
                {'error': "Lien de réinitialisation invalide ou expiré."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not default_token_generator.check_token(user, token):
            return Response(
                {'error': "Lien de réinitialisation invalide ou expiré."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            validate_password(new_password, user)
        except DjangoValidationError as e:
            messages = list(e.messages) if e.messages else [str(e)]
            return Response(
                {'error': messages[0], 'details': messages},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user.set_password(new_password)
        user.save(update_fields=['password'])
        return Response({
            'success': True,
            'message': "Votre mot de passe a été réinitialisé. Vous pouvez vous connecter.",
        })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def current_user_profile(request):
    serializer = UserProfileSerializer(request.user, context={'request': request})
    return Response(serializer.data)


# --- Assistant chatbox (pour Flutter / API) ---

REPONSES_ASSISTANT = [
    {
        'mots': ['laverie', 'machine', 'laver', 'réservation', 'reservation', 'ticket'],
        'texte': 'Réservez une machine à laver depuis "Laverie" : choisissez la machine, le programme (coton, jeans, etc.) et le créneau. Vous pouvez aussi consulter "Mes tickets laverie".',
    },
    {
        'mots': ['message', 'discuter', 'contact', 'chat'],
        'texte': 'Vos conversations sont dans "Mes messages".',
    },
    {
        'mots': ['profil', 'compte', 'modifier', 'photo'],
        'texte': 'Modifiez vos informations dans "Mon profil".',
    },
    {
        'mots': ['aide', 'comment', 'quoi', 'ou', 'où', 'ouverture', 'fonctionnement'],
        'texte': "Dortoir 3 vous permet de réserver les machines à laver en ligne. Utilisez les boutons ci-dessous pour accéder à la Laverie, vos tickets ou votre profil.",
    },
    {
        'mots': ['recherche', 'réserver', 'reserver', 'disponible', 'créneau', 'creneau'],
        'texte': "Allez dans \"Laverie\" pour voir les machines et prendre un ticket. Choisissez le créneau qui vous convient.",
    },
    {
        'mots': ['connexion', 'connecter', 'inscription', 'login'],
        'texte': "Connectez-vous pour accéder à la Laverie, vos tickets et votre profil. Vous pouvez aussi créer un compte si vous n'en avez pas.",
    },
]


def _obtenir_reponse_assistant(texte_utilisateur):
    t = (texte_utilisateur or '').lower().strip()
    if not t:
        return None
    for r in REPONSES_ASSISTANT:
        if any(m in t for m in r['mots']):
            return r['texte']
    return "Je n'ai pas trouvé de réponse précise. Utilisez les boutons ci-dessous pour accéder à la Laverie, vos tickets ou votre profil."


def _get_assistant_buttons(request):
    from django.urls import reverse
    base = request.build_absolute_uri('/')[:-1]  # ex: https://api.example.com

    def btn(label, view_name):
        path = reverse(view_name)
        return {'label': label, 'path': path, 'url': base + path}

    buttons = [btn('Laverie', 'laverie:accueil')]
    if request.user.is_authenticated:
        buttons.extend([
            btn('Mes tickets laverie', 'laverie:mes_tickets'),
            btn('Mes messages', 'chat:mes_conversations'),
            btn('Mon profil', 'profile'),
        ])
    else:
        buttons.extend([
            btn('Se connecter', 'login'),
            btn('Créer un compte', 'creation_compte'),
        ])
    return buttons


@api_view(['POST', 'GET'])
@permission_classes([AllowAny])
def assistant_chat(request):
    """
    API pour l'assistant chatbox (Flutter / front).

    - GET ou POST sans body : retourne le message de bienvenue (sans boutons).
    - POST avec body JSON { "message": "texte" } : retourne la réponse + liste de boutons (path pour navigation).

    Réponse (quand message fourni) :
    {
      "reply": "...",
      "buttons": [ { "label": "...", "path": "/..." }, ... ]
    }

    Réponse (bienvenue, pas de message) :
    {
      "welcome": "...",
      "buttons": []
    }
    """
    is_auth = request.user.is_authenticated
    welcome_authenticated = 'Bonjour ! Comment puis-je vous aider ? Tapez une question (laverie, réservation, messages, profil…) et je vous proposerai des actions.'
    welcome_anonymous = 'Bonjour ! Bienvenue au Dortoir 3. Tapez une question (laverie, inscription…) ou utilisez les boutons pour réserver une machine à laver.'

    if request.method == 'GET':
        return Response({
            'welcome': welcome_authenticated if is_auth else welcome_anonymous,
            'buttons': [],
        })

    message = (request.data.get('message') if request.data else None) or ''
    message = message.strip() if isinstance(message, str) else ''

    if not message:
        return Response({
            'welcome': welcome_authenticated if is_auth else welcome_anonymous,
            'buttons': [],
        })

    reply = _obtenir_reponse_assistant(message)
    buttons = _get_assistant_buttons(request)
    return Response({
        'reply': reply,
        'buttons': buttons,
    })
