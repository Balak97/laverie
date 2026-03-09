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
    mon_ticket_en_cours = tickets_en_cours_qs.first()
    return render(request, 'laverie/accueil.html', {
        'machines': machines, 'now': now, 'annonces': annonces,
        'mon_ticket_en_cours': mon_ticket_en_cours,
        'mes_tickets_en_cours': list(tickets_en_cours_qs),
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


@login_required
def mes_tickets(request):
    """Liste des réservations de l'utilisateur."""
    Reservation.marquer_tickets_termines()
    Reservation.marquer_tickets_en_cours()
    reservations = Reservation.objects.filter(utilisateur=request.user).select_related(
        'machine', 'fonction'
    ).order_by('-debut')
    return render(request, 'laverie/mes_tickets.html', {'reservations': reservations})


@login_required
def afficher_ticket(request, pk):
    """Page pour montrer son ticket à l'écran (présentation à la machine, évite les conflits)."""
    Reservation.marquer_tickets_termines()
    Reservation.marquer_tickets_en_cours()
    resa = get_object_or_404(Reservation, pk=pk, utilisateur=request.user)
    return render(request, 'laverie/afficher_ticket.html', {'resa': resa, 'user_display_default': _('User')})


@login_required
def annuler_ticket(request, pk):
    """Annuler une réservation (si encore réservée). Notifie par e-mail (en russe) les utilisateurs qui suivent sur la même machine."""
    resa = get_object_or_404(Reservation, pk=pk, utilisateur=request.user)
    if resa.statut not in ('reserve',):
        messages.warning(request, 'Cette réservation ne peut plus être annulée.')
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

    messages.success(request, 'Réservation annulée.')
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


