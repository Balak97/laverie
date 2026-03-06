"""
Envoi des e-mails pour les comptes (activation, renvoi d'activation).
Utilisable depuis les vues web et l'API.
"""
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.utils.html import strip_tags
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from django.contrib.sites.shortcuts import get_current_site


def get_domain(request=None):
    """Retourne le domaine pour les liens (request ou fallback settings)."""
    if request:
        try:
            return get_current_site(request).domain
        except Exception:
            pass
    if getattr(settings, 'ALLOWED_HOSTS', None):
        host = settings.ALLOWED_HOSTS[0]
        return host if ':' not in host else host.split(':')[0]
    return 'localhost:8000'


def envoyer_email_activation(user, request=None):
    """
    Envoie l'email d'activation du compte (inscription).
    À appeler après la création d'un utilisateur avec is_active=False.
    """
    domain = get_domain(request)
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)

    subject = 'Activation de votre compte'
    html_message = render_to_string('comptes/emails/activation_email.html', {
        'user': user,
        'domain': domain,
        'uid': uid,
        'token': token,
    })
    plain_message = strip_tags(html_message)

    email = EmailMultiAlternatives(
        subject,
        plain_message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
    )
    email.attach_alternative(html_message, 'text/html')
    email.send(fail_silently=False)


def envoyer_email_renvoyer_activation(user, request=None):
    """
    Renvoie l'email d'activation (lien d'activation) à un utilisateur inactif.
    """
    domain = get_domain(request)
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)

    subject = "Renvoyer votre lien d'activation"
    html_message = render_to_string('comptes/emails/activation_email.html', {
        'user': user,
        'domain': domain,
        'uid': uid,
        'token': token,
    })
    plain_message = strip_tags(html_message)

    email = EmailMultiAlternatives(
        subject,
        plain_message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
    )
    email.attach_alternative(html_message, 'text/html')
    email.send(fail_silently=False)


def envoyer_email_password_reset(user, request=None):
    """
    Envoie l'email de réinitialisation du mot de passe (mot de passe oublié).
    Utilisable depuis les vues web et l'API.
    """
    domain = get_domain(request)
    protocol = request.scheme if request else 'https'
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)

    subject = 'Réinitialisation de votre mot de passe KiloConnect'
    html_message = render_to_string('comptes/emails/password_reset_email.html', {
        'user': user,
        'domain': domain,
        'protocol': protocol,
        'uid': uid,
        'token': token,
    })
    plain_message = strip_tags(html_message)

    email = EmailMultiAlternatives(
        subject,
        plain_message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
    )
    email.attach_alternative(html_message, 'text/html')
    email.send(fail_silently=False)
