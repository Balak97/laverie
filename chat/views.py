from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from .models import Conversation, Message


@login_required
def mes_conversations(request):
    """Liste des conversations (stub minimal)."""
    conversations = Conversation.objects.filter(
        Q(participant1=request.user) | Q(participant2=request.user)
    ).distinct().order_by('-date_creation')[:50]
    return render(request, 'chat/mes_conversations.html', {'conversations': conversations})


@login_required
def conversation_detail(request, pk):
    """Détail d'une conversation (stub minimal)."""
    conv = get_object_or_404(Conversation, pk=pk)
    if request.user != conv.participant1 and request.user != conv.participant2:
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden()
    messages = conv.messages.all()[:100]
    return render(request, 'chat/conversation.html', {'conversation': conv, 'messages': messages})
