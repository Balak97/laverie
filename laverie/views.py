from datetime import timedelta
from typing import Any
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.urls import reverse
from django.db.models import Max
from django.utils.translation import gettext_lazy as _, gettext
from .models import Machine, FonctionMachine, Reservation, MessageLaverie, MAX_TICKETS_SAME_DAY_SAME_MACHINE
from .forms import MachineForm, FonctionMachineForm, ReservationForm, MessageLaverieForm


def is_agent(user):
    """Les agents (administration) peuvent gérer machines et fonctions."""
    return user.is_authenticated and user.user_type == 'ADMIN'


# ——— Étudiants : voir machines, créneaux, réserver ———


@login_required
def accueil(request):
    """Liste des machines avec leurs fonctions, 10 derniers tickets et ticket en cours."""
    Reservation.marquer_tickets_termines()
    Reservation.marquer_tickets_en_cours()
    now = timezone.now()
    machines = Machine.objects.filter(active=True).prefetch_related('fonctions').order_by('ordre', 'nom')
    for m in machines:
        file_attente = (
            Reservation.objects.filter(
                machine=m,
                statut__in=('reserve', 'en_cours'),
                fin__gt=now,
            )
            .select_related('utilisateur', 'fonction')
            .order_by('debut')
        )
        full_list = list(file_attente)
        m.fin_dernier_ticket = max((r.fin for r in full_list), default=None)
        m.file_attente = full_list[:10]
    annonces = MessageLaverie.objects.filter(active=True).order_by('ordre', '-date_creation')
    tickets_en_cours_qs = Reservation.objects.filter(
        utilisateur=request.user,
        statut__in=('reserve', 'en_cours'),
        debut__lte=now,
        fin__gte=now,
    ).select_related('machine', 'fonction').order_by('debut')
    mes_tickets_en_cours = list(tickets_en_cours_qs)
    mon_ticket_en_cours = mes_tickets_en_cours[0] if mes_tickets_en_cours else None
    # Ticket à afficher en haut : paramètre ?focus=ID pour naviguer entre les tickets en cours
    focus_id = request.GET.get('focus')
    ticket_affiche = mon_ticket_en_cours
    if focus_id and mes_tickets_en_cours:
        try:
            pk = int(focus_id)
            for t in mes_tickets_en_cours:
                if t.pk == pk:
                    ticket_affiche = t
                    break
        except (ValueError, TypeError):
            pass
    return render(request, 'laverie/accueil.html', {
        'machines': machines, 'now': now, 'annonces': annonces,
        'mon_ticket_en_cours': mon_ticket_en_cours,
        'ticket_affiche': ticket_affiche,
        'mes_tickets_en_cours': mes_tickets_en_cours,
        'user_display_default': _('User'),
    })


@login_required
def reserver(request):
    """Prendre un ticket : machine (depuis l’accueil ou URL), fonction, créneau."""
    Reservation.marquer_tickets_termines()
    Reservation.marquer_tickets_en_cours()
    machine_prechoice = None
    machine_id = request.GET.get('machine') or (request.POST.get('machine') if request.method == 'POST' else None)
    if machine_id:
        try:
            machine_prechoice = Machine.objects.get(pk=machine_id, active=True)
        except Machine.DoesNotExist:
            pass
    initial = {'machine': machine_prechoice} if machine_prechoice else None
    form = ReservationForm(request.POST or None, initial=initial)
    if request.method == 'POST' and form.is_valid():
        resa = form.save(commit=False)
        resa.utilisateur = request.user
        nb_meme_jour = Reservation.count_user_same_day_machine(request.user, resa.machine, resa.debut.date())
        if nb_meme_jour >= MAX_TICKETS_SAME_DAY_SAME_MACHINE:
            form.add_error(
                None,
                gettext('You cannot take more than %(max)s tickets on the same day on the same machine.')
                % {'max': MAX_TICKETS_SAME_DAY_SAME_MACHINE}
            )
        else:
            resa.save()
            msg = gettext('Ticket #%(num)s enregistré : %(machine)s — %(prog)s le %(date)s. Activez la machine à l\'heure exacte indiquée.') % {
                'num': resa.numero, 'machine': resa.machine.nom, 'prog': resa.fonction.nom, 'date': resa.debut.strftime('%d/%m/%Y à %H:%M')
            }
            messages.success(request, msg)
            return redirect('laverie:mes_tickets')
    machines = Machine.objects.filter(active=True).prefetch_related('fonctions').order_by('ordre', 'nom')
    prochain_debut = None
    if machine_prechoice:
        from datetime import timedelta
        dernier = (
            Reservation.objects.filter(
                machine=machine_prechoice,
                statut__in=('reserve', 'en_cours'),
                fin__gt=timezone.now(),
            )
            .order_by('-fin')
            .first()
        )
        if dernier:
            prochain_debut = dernier.fin + timedelta(minutes=5)
        else:
            # Personne sur la machine : premier créneau dans 5 minutes
            prochain_debut = timezone.now() + timedelta(minutes=5)
    programmes_par_machine = {}
    for m in machines:
        programmes_par_machine[str(m.id)] = [
            {'id': f.id, 'nom': f.nom, 'duree': f.duree_affichage()}
            for f in m.fonctions.filter(active=True).order_by('ordre', 'nom')
        ]
    return render(request, 'laverie/reserver.html', {
        'form': form, 'machines': machines, 'machine_prechoice': machine_prechoice,
        'prochain_debut': prochain_debut,
        'programmes_par_machine': programmes_par_machine,
    })


@login_required
def tickets_machine(request, pk):
    """Affiche les tickets en cours (en attente + en cours) pour une machine ; lien vers le chat pour échanger avec chaque titulaire."""
    Reservation.marquer_tickets_termines()
    Reservation.marquer_tickets_en_cours()
    machine = get_object_or_404(Machine, pk=pk, active=True)
    now = timezone.now()
    tickets = list(
        Reservation.objects.filter(
            machine=machine,
            statut__in=('reserve', 'en_cours'),
            fin__gt=now,
        )
        .select_related('utilisateur', 'fonction')
        .order_by('debut')
    )
    fin_dernier = max((r.fin for r in tickets), default=None)
    return render(request, 'laverie/tickets_machine.html', {
        'machine': machine,
        'tickets': tickets,
        'fin_dernier_ticket': fin_dernier,
        'user_display_default': _('User'),
    })


# Chaînes page « Mes tickets » (ru/fr/en) pour affichage correct même sans .mo
_MES_TICKETS_STRINGS = {
    'ru': {
        'my_tickets': 'Мои талоны',
        'your_reservations': 'Ваши резервации стиральных машин.',
        'new_reservation': 'Новая резервация',
        'ticket': 'Талон',
        'at': 'в',
        'min': 'мин',
        'show_ticket': 'Показать талон',
        'extend': 'Продлить',
        'cancel_this_reservation': 'Отменить эту резервацию?',
        'cancel': 'Отменить',
        'no_reservations': 'У вас нет резерваций.',
        'book_slot': 'Забронировать слот',
        'status_reserve': 'Забронировано',
        'status_en_cours': 'В процессе',
        'status_termine': 'Завершено',
        'status_annule': 'Отменено',
    },
    'fr': {
        'my_tickets': 'Mes tickets',
        'your_reservations': 'Vos réservations de machine à laver.',
        'new_reservation': 'Nouvelle réservation',
        'ticket': 'Ticket',
        'at': 'à',
        'min': 'min',
        'show_ticket': 'Afficher le ticket',
        'extend': 'Prolonger',
        'cancel_this_reservation': 'Annuler cette réservation ?',
        'cancel': 'Annuler',
        'no_reservations': "Vous n'avez aucune réservation.",
        'book_slot': 'Réserver un créneau',
        'status_reserve': 'Réservé',
        'status_en_cours': 'En cours',
        'status_termine': 'Terminé',
        'status_annule': 'Annulé',
    },
    'en': {
        'my_tickets': 'My tickets',
        'your_reservations': 'Your washing machine reservations.',
        'new_reservation': 'New reservation',
        'ticket': 'Ticket',
        'at': 'at',
        'min': 'min',
        'show_ticket': 'Show ticket',
        'extend': 'Extend',
        'cancel_this_reservation': 'Cancel this reservation?',
        'cancel': 'Cancel',
        'no_reservations': 'You have no reservations.',
        'book_slot': 'Book a slot',
        'status_reserve': 'Reserved',
        'status_en_cours': 'In progress',
        'status_termine': 'Completed',
        'status_annule': 'Cancelled',
    },
}

# Chaînes page détail ticket (afficher_ticket) — ru/fr/en
_AFFICHER_TICKET_STRINGS = {
    'ru': {
        'close': 'Закрыть',
        'dortoir_laverie': 'Общежитие 3 — Прачечная',
        'ticket': 'Талон',
        'time_remaining': 'Осталось времени',
        'machine': 'Машина',
        'programme': 'Программа',
        'time_slot': 'Временной слот',
        'holder': 'Владелец',
        'show_at_machine': 'Покажите этот талон на машине, чтобы избежать конфликтов.',
        'activate_at_time': 'Включите машину точно в указанное выше время.',
        'change_duration': 'Изменить длительность',
        'extend_slot_info_fmt': 'Вы можете продлить слот (макс. +%(max)s мин). Следующие талоны на этой машине будут сдвинуты.',
        'extend_by': 'Продлить на',
        'min': 'мин',
        'extend': 'Продлить',
    },
    'fr': {
        'close': 'Fermer',
        'dortoir_laverie': 'Dortoir 3 — Laverie',
        'ticket': 'Ticket',
        'time_remaining': 'Temps restant',
        'machine': 'Machine',
        'programme': 'Programme',
        'time_slot': 'Créneau',
        'holder': 'Titulaire',
        'show_at_machine': 'Montrez ce ticket à la machine pour éviter les conflits.',
        'activate_at_time': 'Activez la machine à l\'heure exacte indiquée ci-dessus.',
        'change_duration': 'Modifier la durée',
        'extend_slot_info_fmt': 'Vous pouvez prolonger votre créneau (max +%(max)s min). Les tickets suivants sur la même machine seront décalés.',
        'extend_by': 'Prolonger de',
        'min': 'min',
        'extend': 'Prolonger',
    },
    'en': {
        'close': 'Close',
        'dortoir_laverie': 'Dorm 3 — Laundry',
        'ticket': 'Ticket',
        'time_remaining': 'Time remaining',
        'machine': 'Machine',
        'programme': 'Programme',
        'time_slot': 'Time slot',
        'holder': 'Holder',
        'show_at_machine': 'Show this ticket at the machine to avoid conflicts.',
        'activate_at_time': 'Activate the machine at the exact time shown above.',
        'change_duration': 'Change duration',
        'extend_slot_info_fmt': 'You can extend your slot (max +%(max)s min). The following tickets on the same machine will be shifted.',
        'extend_by': 'Extend by',
        'min': 'min',
        'extend': 'Extend',
    },
}


@login_required
def mes_tickets(request):
    """Liste des réservations de l'utilisateur, triées du plus récent au plus ancien."""
    Reservation.marquer_tickets_termines()
    Reservation.marquer_tickets_en_cours()
    reservations = list(
        Reservation.objects.filter(utilisateur=request.user)
        .select_related('machine', 'fonction')
        .order_by('-date_creation')
    )
    extensible_pks = set()
    for r in reservations:
        if r.statut in ('reserve', 'en_cours') and _max_fin_prolongation(r) > r.fin:
            extensible_pks.add(r.pk)
    lang = request.LANGUAGE_CODE or 'ru'
    i18n = _MES_TICKETS_STRINGS.get(lang, _MES_TICKETS_STRINGS['en'])
    return render(request, 'laverie/mes_tickets.html', {
        'reservations': reservations,
        'extensible_pks': extensible_pks,
        'i18n': i18n,
    })


@login_required
def afficher_ticket(request, pk):
    """Page pour montrer son ticket à l'écran (présentation à la machine, évite les conflits)."""
    Reservation.marquer_tickets_termines()
    Reservation.marquer_tickets_en_cours()
    resa = get_object_or_404(Reservation, pk=pk, utilisateur=request.user)
    now = timezone.now()
    # Prolongation : plafond global = durée programme + 60 min (reste à ajouter possible)
    max_extend_minutes = 0
    if resa.statut in ('reserve', 'en_cours'):
        max_fin = _max_fin_prolongation(resa)
        restant = int((max_fin - resa.fin).total_seconds() / 60)
        max_extend_minutes = max(0, min(MAX_EXTEND_MINUTES, restant))
    lang = request.LANGUAGE_CODE or 'ru'
    i18n = _AFFICHER_TICKET_STRINGS.get(lang, _AFFICHER_TICKET_STRINGS['en']).copy()
    i18n['extend_slot_info'] = i18n['extend_slot_info_fmt'] % {'max': max_extend_minutes}
    context = {
        'resa': resa,
        'user_display_default': _('User'),
        'max_extend_minutes': max_extend_minutes,
        'i18n': i18n,
    }
    return render(request, 'laverie/afficher_ticket.html', context)


# Maximum de minutes qu'on peut ajouter en plus de la durée du programme (plafond global, pas par requête)
MAX_EXTEND_MINUTES = 20


def _max_fin_prolongation(resa):
    """Heure de fin max pour ce ticket : début + durée du programme + 60 min. Évite les abus par requêtes multiples."""
    duree_prog = resa.fonction.duree_minutes if resa.fonction else 60
    return resa.debut + timedelta(minutes=duree_prog + MAX_EXTEND_MINUTES)


@login_required
@require_POST
def modifier_duree_ticket(request, pk):
    """
    Prolonger la durée d'un ticket (max +60 min). Les tickets suivants sur la machine sont décalés.
    Autorisé pour les statuts 'reserve' et 'en_cours'.
    """
    Reservation.marquer_tickets_termines()
    Reservation.marquer_tickets_en_cours()
    resa = get_object_or_404(Reservation, pk=pk, utilisateur=request.user)
    if resa.statut not in ('reserve', 'en_cours'):
        messages.error(request, gettext('This ticket can no longer be modified.'))
        return redirect('laverie:afficher_ticket', pk=pk)

    now = timezone.now()
    action = request.POST.get('action')
    new_fin = None

    if action == 'extend':
        try:
            add_minutes = int(request.POST.get('add_minutes', 0))
        except (TypeError, ValueError):
            add_minutes = 0
        add_minutes = max(0, add_minutes)
        max_fin = _max_fin_prolongation(resa)
        max_ajout_restant = int((max_fin - resa.fin).total_seconds() / 60)
        add_minutes = min(add_minutes, max(0, max_ajout_restant))
        if add_minutes <= 0:
            messages.warning(
                request,
                gettext('Total duration cannot exceed program duration + %(max)s minutes.') % {'max': MAX_EXTEND_MINUTES},
            )
            return redirect('laverie:afficher_ticket', pk=pk)
        old_fin = resa.fin
        new_fin = old_fin + timedelta(minutes=add_minutes)
        delta = timedelta(minutes=add_minutes)
        # Décaler tous les tickets qui suivent sur la même machine (début et fin + add_minutes)
        suivants = Reservation.objects.filter(
            machine=resa.machine,
            statut__in=('reserve', 'en_cours'),
            debut__gte=old_fin,
        ).exclude(pk=resa.pk).order_by('debut')
        for r in suivants:
            r.debut += delta
            r.fin += delta
            r.save(update_fields=['debut', 'fin'])
        resa.fin = new_fin
        resa.save(update_fields=['fin'])
        messages.success(request, gettext('Your slot has been extended.'))
        return redirect('laverie:afficher_ticket', pk=pk)

    messages.warning(request, gettext('Invalid action.'))
    return redirect('laverie:afficher_ticket', pk=pk)


@login_required
def annuler_ticket(request, pk):
    """Annuler une réservation (si encore réservée). Notifie par e-mail (en russe) les utilisateurs qui suivent sur la même machine."""
    resa = get_object_or_404(Reservation, pk=pk, utilisateur=request.user)
    if resa.statut not in ('reserve',):
        messages.warning(request, gettext('This reservation can no longer be cancelled.'))
        return redirect('laverie:mes_tickets')
    machine = resa.machine
    debut_annule = resa.debut
    resa.statut = 'annule'
    resa.save()

    # Envoyer un message (e-mail en russe) à tous ceux qui nous suivent dans la file sur la même machine
    import logging
    from .emails import envoyer_email_changement_horaire
    from django.contrib.auth import get_user_model

    logger = logging.getLogger(__name__)
    # Personnes dont le créneau commence après le nôtre sur la même machine (ceux qui nous suivent dans la file)
    suivants = set(
        Reservation.objects.filter(
            machine=machine,
            statut__in=('reserve', 'en_cours'),
            debut__gt=debut_annule,
        )
        .values_list('utilisateur', flat=True)
        .distinct()
    )
    destinataires = suivants - {request.user.pk}
    logger.info("Laverie annulation: machine=%s, debut_annule=%s, destinataires (suivants)=%s", machine.pk, debut_annule, destinataires)

    User = get_user_model()
    for user_id in destinataires:
        try:
            user = User.objects.get(pk=user_id)
            envoyer_email_changement_horaire(user, request=request)
        except Exception:
            pass

    messages.success(request, gettext('Reservation cancelled.'))
    return redirect('laverie:mes_tickets')


# ——— API créneaux (pour afficher les créneaux disponibles) ———

@login_required
def api_creneaux(request):
    """Retourne les créneaux déjà pris pour une machine (pour affichage calendrier)."""
    machine_id = request.GET.get('machine_id')
    if not machine_id:
        return JsonResponse({'creneaux': []})
    from django.db.models import Q
    now = timezone.now()
    resas = Reservation.objects.filter(
        machine_id=machine_id,
        statut__in=('reserve', 'en_cours'),
        fin__gt=now
    ).values('debut', 'fin')
    creneaux = [{'debut': r['debut'].isoformat(), 'fin': r['fin'].isoformat()} for r in resas]
    return JsonResponse({'creneaux': creneaux})


@login_required
def api_fonctions_machine(request):
    """Retourne les fonctions d'une machine (pour select dynamique)."""
    machine_id = request.GET.get('machine_id')
    if not machine_id:
        return JsonResponse({'fonctions': []})
    fonctions = FonctionMachine.objects.filter(machine_id=machine_id, active=True).order_by('ordre', 'nom')
    data = [{'id': f.id, 'nom': f.nom, 'duree_minutes': f.duree_minutes} for f in fonctions]
    return JsonResponse({'fonctions': data})


# ——— Agents : ajouter machines et fonctions ———

@login_required
def agent_machines(request):
    """Liste des machines (agents uniquement)."""
    if not is_agent(request.user):
        messages.error(request, 'Accès réservé aux agents.')
        return redirect('laverie:accueil')
    machines = Machine.objects.all().prefetch_related('fonctions').order_by('ordre', 'nom')
    return render(request, 'laverie/agent/machines.html', {'machines': machines})


@login_required
def agent_machine_ajout(request):
    """Ajouter une machine."""
    if not is_agent(request.user):
        messages.error(request, 'Accès réservé aux agents.')
        return redirect('laverie:accueil')
    form = MachineForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Machine ajoutée.')
        return redirect('laverie:agent_machines')
    return render(request, 'laverie/agent/machine_form.html', {'form': form})


@login_required
def agent_machine_modifier(request, pk):
    """Modifier une machine."""
    if not is_agent(request.user):
        messages.error(request, 'Accès réservé aux agents.')
        return redirect('laverie:accueil')
    machine = get_object_or_404(Machine, pk=pk)
    form = MachineForm(request.POST or None, instance=machine)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Machine mise à jour.')
        return redirect('laverie:agent_machines')
    return render(request, 'laverie/agent/machine_form.html', {'form': form, 'machine': machine})


@login_required
def agent_fonction_ajout(request):
    """Ajouter une fonction à une machine."""
    if not is_agent(request.user):
        messages.error(request, 'Accès réservé aux agents.')
        return redirect('laverie:accueil')
    form = FonctionMachineForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Fonction ajoutée.')
        return redirect('laverie:agent_machines')
    return render(request, 'laverie/agent/fonction_form.html', {'form': form})


@login_required
def agent_fonction_modifier(request, pk):
    """Modifier une fonction."""
    if not is_agent(request.user):
        messages.error(request, 'Accès réservé aux agents.')
        return redirect('laverie:accueil')
    fonction = get_object_or_404(FonctionMachine, pk=pk)
    form = FonctionMachineForm(request.POST or None, instance=fonction)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Fonction mise à jour.')
        return redirect('laverie:agent_machines')
    return render(request, 'laverie/agent/fonction_form.html', {'form': form, 'fonction': fonction})


@login_required
def agent_fonction_toggle_active(request, pk):
    """Active ou désactive une fonction (masquée du potentiomètre de réservation)."""
    if not is_agent(request.user):
        messages.error(request, 'Accès réservé aux agents.')
        return redirect('laverie:accueil')
    fonction = get_object_or_404(FonctionMachine, pk=pk)
    fonction.active = not fonction.active
    fonction.save()
    status = 'affichée' if fonction.active else 'masquée'
    messages.success(request, f'Programme « {fonction.nom } » {status} sur la réservation.')
    return redirect('laverie:agent_machines')


@login_required
@require_POST
def agent_fonction_copier(request):
    """Copie une fonction vers une autre machine (glisser-déposer)."""
    if not is_agent(request.user):
        return JsonResponse({'success': False, 'error': 'Accès refusé'}, status=403)
    fonction_id = request.POST.get('fonction_id')
    machine_id = request.POST.get('machine_id')
    if not fonction_id or not machine_id:
        return JsonResponse({'success': False, 'error': 'Paramètres manquants'}, status=400)
    source = get_object_or_404(FonctionMachine, pk=fonction_id)
    target_machine = get_object_or_404(Machine, pk=machine_id)
    if source.machine_id == int(machine_id):
        return JsonResponse({'success': False, 'error': 'Même machine'}, status=400)
    nom = source.nom
    if target_machine.fonctions.filter(nom=nom).exists():
        nom = f"{source.nom} (copie)"
    ordre_max = target_machine.fonctions.aggregate(Max('ordre'))['ordre__max'] or 0
    FonctionMachine.objects.create(
        machine=target_machine,
        nom=nom,
        duree_minutes=source.duree_minutes,
        ordre=ordre_max + 1,
        active=True,
    )
    messages.success(request, f'Programme « {source.nom } » copié sur {target_machine.nom}.')
    return JsonResponse({
        'success': True,
        'redirect': reverse('laverie:agent_machines'),
    })


@login_required
def agent_messages(request):
    """Liste des messages affichés en haut des machines (agents uniquement)."""
    if not is_agent(request.user):
        messages.error(request, 'Accès réservé aux agents.')
        return redirect('laverie:accueil')
    annonces = MessageLaverie.objects.all().order_by('ordre', '-date_creation')
    return render(request, 'laverie/agent/messages.html', {'annonces': annonces})


@login_required
def agent_message_ajout(request):
    """Publier un message (agents uniquement)."""
    if not is_agent(request.user):
        messages.error(request, 'Accès réservé aux agents.')
        return redirect('laverie:accueil')
    form = MessageLaverieForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        obj = form.save(commit=False)
        obj.auteur = request.user
        obj.save()
        messages.success(request, 'Message publié. Il défile en haut de la page laverie.')
        return redirect('laverie:agent_messages')
    return render(request, 'laverie/agent/message_form.html', {'form': form})


@login_required
def agent_message_modifier(request, pk):
    """Modifier un message."""
    if not is_agent(request.user):
        messages.error(request, 'Accès réservé aux agents.')
        return redirect('laverie:accueil')
    msg = get_object_or_404(MessageLaverie, pk=pk)
    form = MessageLaverieForm(request.POST or None, instance=msg)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Message mis à jour.')
        return redirect('laverie:agent_messages')
    return render(request, 'laverie/agent/message_form.html', {'form': form, 'message_obj': msg})


@login_required
def agent_message_supprimer(request, pk):
    """Supprimer un message."""
    if not is_agent(request.user):
        messages.error(request, 'Accès réservé aux agents.')
        return redirect('laverie:accueil')
    msg = get_object_or_404(MessageLaverie, pk=pk)
    if request.method == 'POST':
        msg.delete()
        messages.success(request, 'Message supprimé.')
        return redirect('laverie:agent_messages')
    return redirect('laverie:agent_messages')


