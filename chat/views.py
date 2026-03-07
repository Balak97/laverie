from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.db.models import Q
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


@login_required
def mes_conversations(request):
    """Liste des conversations (stub minimal)."""
    conversations = Conversation.objects.filter(
        Q(participant1=request.user) | Q(participant2=request.user)
    ).distinct().order_by('-date_creation')[:50]
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
