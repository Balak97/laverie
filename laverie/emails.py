"""
Envoi d'e-mails pour la laverie (notification de changement d'horaire après annulation).
"""
import logging
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from django.contrib.sites.shortcuts import get_current_site

logger = logging.getLogger(__name__)


def get_domain(request=None):
    """Retourne le domaine pour les liens."""
    if request:
        try:
            return get_current_site(request).domain
        except Exception:
            pass
    if getattr(settings, 'ALLOWED_HOSTS', None):
        host = settings.ALLOWED_HOSTS[0]
        return host if ':' not in host else host.split(':')[0]
    return 'localhost:8000'


# Courriel rédigé en russe (sujet et corps)
SUBJECT_RU = 'Изменение времени — прачечная Дортуар 3'

BODY_PLAIN_RU = """Здравствуйте!

Одна из резерваций на той же стиральной машине была отменена. Время слотов могло измениться.

Пожалуйста, зайдите на сайт и проверьте актуальное расписание и время вашей резервации.

С уважением,
Сервис прачечной Дортуар 3
"""


def envoyer_email_changement_horaire(utilisateur, request=None):
    """
    Envoie un e-mail en russe à l'utilisateur pour l'informer qu'un changement
    d'horaire a eu lieu (annulation d'une réservation avant la sienne sur la même machine).
    """
    domain = get_domain(request)
    protocol = request.scheme if request else 'https'
    url_site = f'{protocol}://{domain}/laverie/'

    body_plain = BODY_PLAIN_RU + f'\nСайт: {url_site}\n'

    html_content = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: sans-serif; line-height: 1.5;">
<p>Здравствуйте!</p>
<p>Одна из резерваций на той же стиральной машине была отменена. Время слотов могло измениться.</p>
<p><strong>Пожалуйста, зайдите на сайт и проверьте актуальное расписание и время вашей резервации.</strong></p>
<p><a href="{url_site}">Перейти к прачечной</a></p>
<p>С уважением,<br>Сервис прачечной Дортуар 3</p>
</body>
</html>"""

    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@localhost')
    to_email = utilisateur.email
    if not to_email:
        logger.warning("Laverie: pas d'email pour l'utilisateur %s, notification non envoyée.", utilisateur.pk)
        return

    email = EmailMultiAlternatives(
        SUBJECT_RU,
        body_plain,
        from_email,
        [to_email],
    )
    email.attach_alternative(html_content, 'text/html')
    try:
        email.send(fail_silently=False)
        logger.info("Laverie: email changement horaire envoyé à %s", to_email)
    except Exception as e:
        logger.exception("Laverie: échec envoi email changement horaire à %s: %s", to_email, e)
