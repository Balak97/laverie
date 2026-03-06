from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse
from .models import Machine, FonctionMachine, Reservation, MessageLaverie
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
    mon_ticket_en_cours = (
        Reservation.objects.filter(
            utilisateur=request.user,
            statut__in=('reserve', 'en_cours'),
            debut__lte=now,
            fin__gte=now,
        )
        .select_related('machine', 'fonction')
        .first()
    )
    return render(request, 'laverie/accueil.html', {
        'machines': machines, 'now': now, 'annonces': annonces,
        'mon_ticket_en_cours': mon_ticket_en_cours,
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
        resa.save()
        messages.success(request, f'Ticket #{resa.numero} enregistré : {resa.machine.nom} — {resa.fonction.nom} le {resa.debut.strftime("%d/%m/%Y à %H:%M")}.')
        return redirect('laverie:mes_tickets')
    machines = Machine.objects.filter(active=True).prefetch_related('fonctions').order_by('ordre', 'nom')
    return render(request, 'laverie/reserver.html', {'form': form, 'machines': machines, 'machine_prechoice': machine_prechoice})


@login_required
def tickets_machine(request, pk):
    """Affiche les tickets en cours (en attente + en cours) pour une machine."""
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
    return render(request, 'laverie/afficher_ticket.html', {'resa': resa})


@login_required
def annuler_ticket(request, pk):
    """Annuler une réservation (si encore réservée)."""
    resa = get_object_or_404(Reservation, pk=pk, utilisateur=request.user)
    if resa.statut not in ('reserve',):
        messages.warning(request, 'Cette réservation ne peut plus être annulée.')
        return redirect('laverie:mes_tickets')
    resa.statut = 'annule'
    resa.save()
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


