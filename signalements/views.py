from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.translation import gettext as _

from .models import Signalement
from .forms import SignalementForm


def is_agent(user):
    """Accès réservé aux agents (administration)."""
    return user.is_authenticated and getattr(user, 'user_type', None) == 'ADMIN'


# Chaînes des pages signalements (fallback si .mo non compilés)
_SIGNALEMENTS_STRINGS = {
    'ru': {
        'back_to_home': 'На главную',
        'view_my_reports': 'Мои сообщения о проблемах',
        'report_a_problem': 'Сообщить о проблеме',
        'describe_team': 'Опишите проблему. Команда ознакомится с ней.',
        'problem_description': 'Описание проблемы',
        'submit_report': 'Отправить сообщение',
        'cancel': 'Отменить',
        'placeholder_description': 'Опишите проблему, с которой вы столкнулись…',
        'success_message': 'Ваше сообщение зафиксировано. Вы можете отслеживать его статус ниже.',
        'my_reports': 'Мои сообщения о проблемах',
        'track_status_subtitle': 'Отслеживайте статус ваших сообщений.',
        'new_report': 'Новое сообщение',
        'no_reports': 'Нет сообщений',
        'empty_message': 'Ваши сообщения о проблемах появятся здесь с их статусом (новое, в работе, решено).',
        'status_nouveau': 'Новое',
        'status_en_cours': 'В работе',
        'status_resolu': 'Решено',
        'agent_title': 'Сообщённые проблемы',
        'agent_subtitle': 'Просматривайте сообщения и обновляйте статус (в работе / решено).',
        'user_default': 'Пользователь',
        'mark_in_progress': 'Отметить в работе',
        'mark_resolved': 'Отметить решённым',
        'resolved_label': 'Решено',
        'agent_empty': 'Сообщения появятся здесь.',
    },
    'fr': {
        'back_to_home': "Retour à l'accueil",
        'view_my_reports': 'Voir mes signalements',
        'report_a_problem': 'Signaler un problème',
        'describe_team': "Décrivez le problème. L'équipe en prendra connaissance.",
        'problem_description': 'Description du problème',
        'submit_report': 'Envoyer le signalement',
        'cancel': 'Annuler',
        'placeholder_description': 'Décrivez le problème rencontré…',
        'success_message': 'Votre signalement a bien été enregistré. Vous pouvez suivre son état ci-dessous.',
        'my_reports': 'Mes signalements',
        'track_status_subtitle': "Suivez l'état de traitement de vos problèmes signalés.",
        'new_report': 'Nouveau signalement',
        'no_reports': 'Aucun signalement',
        'empty_message': "Vos problèmes signalés apparaîtront ici avec leur état (nouveau, en cours, résolu).",
        'status_nouveau': 'Nouveau',
        'status_en_cours': 'En cours',
        'status_resolu': 'Résolu',
        'agent_title': 'Problèmes signalés',
        'agent_subtitle': 'Consultez les signalements et mettez à jour le statut (en cours / résolu).',
        'user_default': 'Utilisateur',
        'mark_in_progress': 'Marquer en cours',
        'mark_resolved': 'Marquer résolu',
        'resolved_label': 'Résolu',
        'agent_empty': 'Les signalements apparaîtront ici.',
    },
    'en': {
        'back_to_home': 'Back to home',
        'view_my_reports': 'View my reports',
        'report_a_problem': 'Report a problem',
        'describe_team': 'Describe the problem. The team will take note of it.',
        'problem_description': 'Problem description',
        'submit_report': 'Submit report',
        'cancel': 'Cancel',
        'placeholder_description': 'Describe the problem you encountered…',
        'success_message': 'Your report has been recorded. You can track its status below.',
        'my_reports': 'My reports',
        'track_status_subtitle': 'Track the status of your reported problems.',
        'new_report': 'New report',
        'no_reports': 'No reports',
        'empty_message': 'Your reported problems will appear here with their status (new, in progress, resolved).',
        'status_nouveau': 'New',
        'status_en_cours': 'In progress',
        'status_resolu': 'Resolved',
        'agent_title': 'Reported problems',
        'agent_subtitle': 'View reports and update status (in progress / resolved).',
        'user_default': 'User',
        'mark_in_progress': 'Mark in progress',
        'mark_resolved': 'Mark resolved',
        'resolved_label': 'Resolved',
        'agent_empty': 'Reports will appear here.',
    },
}


@login_required
def signaler(request):
    """Formulaire pour signaler un problème (indépendant du lavage)."""
    lang = request.LANGUAGE_CODE or 'ru'
    i18n = _SIGNALEMENTS_STRINGS.get(lang, _SIGNALEMENTS_STRINGS['en'])
    form = SignalementForm(request.POST or None, lang=lang, i18n=i18n)
    if request.method == 'POST' and form.is_valid():
        obj = form.save(commit=False)
        obj.utilisateur = request.user
        obj.save()
        messages.success(request, i18n['success_message'])
        return redirect('signalements:mes_signalements')
    return render(request, 'signalements/signaler.html', {'form': form, 'i18n': i18n})


def _statut_display(s, i18n):
    """Retourne le libellé traduit du statut."""
    key = f'status_{s.statut}'
    return i18n.get(key, s.get_statut_display())


@login_required
def mes_signalements(request):
    """Liste des signalements de l'utilisateur pour suivre l'état de traitement."""
    lang = request.LANGUAGE_CODE or 'ru'
    i18n = _SIGNALEMENTS_STRINGS.get(lang, _SIGNALEMENTS_STRINGS['en'])
    signalements = Signalement.objects.filter(utilisateur=request.user).order_by('-date_creation')
    signalements = [(s, _statut_display(s, i18n)) for s in signalements]
    return render(request, 'signalements/mes_signalements.html', {'signalements': signalements, 'i18n': i18n})


@login_required
def agent_liste(request):
    """Liste des signalements (agents uniquement)."""
    if not is_agent(request.user):
        messages.error(request, _('Access restricted to agents.'))
        return redirect('signalements:signaler')
    lang = request.LANGUAGE_CODE or 'ru'
    i18n = _SIGNALEMENTS_STRINGS.get(lang, _SIGNALEMENTS_STRINGS['en'])
    signalements = list(Signalement.objects.all().order_by('-date_creation'))
    signalements = [(s, _statut_display(s, i18n)) for s in signalements]
    return render(request, 'signalements/agent/liste.html', {'signalements': signalements, 'i18n': i18n})


@login_required
def agent_changer_statut(request, pk):
    """Changer le statut d'un signalement (agents uniquement)."""
    if not is_agent(request.user):
        messages.error(request, 'Accès réservé aux agents.')
        return redirect('signalements:signaler')
    sig = get_object_or_404(Signalement, pk=pk)
    nouveau = request.POST.get('statut')
    if request.method == 'POST' and nouveau in ('en_cours', 'resolu'):
        sig.statut = nouveau
        sig.save()
        messages.success(request, f'Signalement marqué comme « {sig.get_statut_display()} ».')
    return redirect('signalements:agent_liste')
