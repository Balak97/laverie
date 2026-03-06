from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from .models import Signalement
from .forms import SignalementForm


def is_agent(user):
    """Accès réservé aux agents (administration)."""
    return user.is_authenticated and getattr(user, 'user_type', None) == 'ADMIN'


@login_required
def signaler(request):
    """Formulaire pour signaler un problème (indépendant du lavage)."""
    form = SignalementForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        obj = form.save(commit=False)
        obj.utilisateur = request.user
        obj.save()
        messages.success(request, 'Votre signalement a bien été enregistré. Vous pouvez suivre son état ci-dessous.')
        return redirect('signalements:mes_signalements')
    return render(request, 'signalements/signaler.html', {'form': form})


@login_required
def mes_signalements(request):
    """Liste des signalements de l'utilisateur pour suivre l'état de traitement."""
    signalements = Signalement.objects.filter(utilisateur=request.user).order_by('-date_creation')
    return render(request, 'signalements/mes_signalements.html', {'signalements': signalements})


@login_required
def agent_liste(request):
    """Liste des signalements (agents uniquement)."""
    if not is_agent(request.user):
        messages.error(request, 'Accès réservé aux agents.')
        return redirect('signalements:signaler')
    signalements = Signalement.objects.all().order_by('-date_creation')
    return render(request, 'signalements/agent/liste.html', {'signalements': signalements})


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
