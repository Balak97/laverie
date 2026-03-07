from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from .models import Conversation, Message


def _get_or_create_conversation(user1, user2):
    """Retourne la conversation entre user1 et user2, la crée si nécessaire (p1.pk <= p2.pk)."""
    p1, p2 = (user1, user2) if user1.pk <= user2.pk else (user2, user1)
    conv, _ = Conversation.objects.get_or_create(
        participant1=p1,
        participant2=p2,
    )
    return conv


@login_required
def conversation_with_user(request, user_id):
    """Ouvre ou crée la conversation avec l'utilisateur donné, puis redirige vers la page de conversation."""
    User = get_user_model()
    other = get_object_or_404(User, pk=user_id)
    if other == request.user:
        return redirect('chat:mes_conversations')
    conv = _get_or_create_conversation(request.user, other)
    return redirect('chat:conversation_detail', pk=conv.pk)


def _other_participant(conv, current_user):
    """Retourne l'autre participant de la conversation."""
    return conv.participant2 if current_user == conv.participant1 else conv.participant1


@login_required
def mes_conversations(request):
    """Liste des conversations avec l'autre participant et la dernière activité."""
    convs = Conversation.objects.filter(
        Q(participant1=request.user) | Q(participant2=request.user)
    ).distinct().order_by('-date_creation').prefetch_related('messages')[:50]
    conversations = []
    for conv in convs:
        other = _other_participant(conv, request.user)
        last_msg = conv.messages.order_by('-date_envoi').first()
        last_activity = last_msg.date_envoi if last_msg else conv.date_creation
        unread_count = conv.messages.filter(lu=False).exclude(sender=request.user).count()
        conversations.append({
            'conversation': conv,
            'other_participant': other,
            'last_activity': last_activity,
            'unread_count': unread_count,
            'last_message': last_msg,
        })
    return render(request, 'chat/mes_conversations.html', {'conversations': conversations})


@login_required
def conversation_detail(request, pk):
    """Détail d'une conversation : messages et l'autre participant."""
    conv = get_object_or_404(Conversation, pk=pk)
    if request.user != conv.participant1 and request.user != conv.participant2:
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden()
    other_participant = conv.participant2 if request.user == conv.participant1 else conv.participant1
    chat_messages = list(conv.messages.select_related('sender').all()[:100])
    return render(request, 'chat/conversation.html', {
        'conversation': conv,
        'messages': chat_messages,
        'chat_messages': chat_messages,
        'other_participant': other_participant,
    })


@login_required
@require_http_methods(['GET'])
def conversation_messages_json(request, pk):
    """Retourne les messages de la conversation en JSON (pour le rechargement AJAX). Marque les messages reçus comme lus."""
    conv = get_object_or_404(Conversation, pk=pk)
    if request.user != conv.participant1 and request.user != conv.participant2:
        return JsonResponse({'success': False, 'error': 'Forbidden'}, status=403)
    other = conv.participant2 if request.user == conv.participant1 else conv.participant1
    # Marquer comme lus les messages reçus (émetteur = l'autre), pour mise à jour du badge en temps réel
    Message.objects.filter(conversation=conv).exclude(sender=request.user).update(lu=True)
    messages_qs = conv.messages.select_related('sender').order_by('date_envoi')[:100]
    messages = []
    for m in messages_qs:
        sender_name = getattr(m.sender, 'display_name', None) or m.sender.get_full_name() or m.sender.email or ''
        messages.append({
            'id': m.id,
            'is_sender': m.sender_id == request.user.pk,
            'sender_name': sender_name,
            'date_envoi': m.date_envoi.strftime('%d/%m/%Y %H:%M'),
            'contenu': m.contenu or '',
            'message_type': 'text',
        })
    return JsonResponse({
        'success': True,
        'messages': messages,
        'other_participant_online': getattr(other, 'is_online', False),
    })


@login_required
@require_http_methods(['POST'])
def conversation_send(request, pk):
    """Envoie un message dans la conversation (POST contenu=...). Retourne JSON {success: true} ou {success: false, error: ...}."""
    try:
        conv = get_object_or_404(Conversation, pk=pk)
        if request.user != conv.participant1 and request.user != conv.participant2:
            return JsonResponse({'success': False, 'error': 'Accès refusé.'}, status=403)
        contenu = (request.POST.get('contenu') or '').strip()
        if not contenu:
            return JsonResponse({'success': False, 'error': 'Message vide.'})
        Message.objects.create(
            conversation=conv,
            sender=request.user,
            contenu=contenu,
        )
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
