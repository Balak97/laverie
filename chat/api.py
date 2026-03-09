"""
API REST Chat pour Flutter.
"""
from rest_framework import serializers, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from django.db.models import Q

from .models import Conversation, Message
from .views import _get_or_create_conversation

User = get_user_model()


class MessageSerializer(serializers.ModelSerializer):
    sender_id = serializers.IntegerField(source='sender.id', read_only=True)
    sender_display_name = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = ['id', 'conversation', 'sender_id', 'sender_display_name', 'contenu', 'lu', 'date_envoi']

    def get_sender_display_name(self, obj):
        return getattr(obj.sender, 'display_name', None) or obj.sender.get_full_name() or obj.sender.email


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def conversation_list(request):
    """Liste des conversations de l'utilisateur connecté."""
    convs = Conversation.objects.filter(
        Q(participant1=request.user) | Q(participant2=request.user)
    ).distinct().order_by('-date_creation').prefetch_related('messages')[:50]
    return Response(_conversation_list_response(request, convs))


def _conversation_list_response(request, convs):
    out = []
    for conv in convs:
        other = conv.participant2 if request.user == conv.participant1 else conv.participant1
        last_msg = conv.messages.order_by('-date_envoi').first()
        last_activity = last_msg.date_envoi if last_msg else conv.date_creation
        unread_count = conv.messages.filter(lu=False).exclude(sender=request.user).count()
        out.append({
            'id': conv.id,
            'other_participant_id': other.id,
            'other_participant_display_name': getattr(other, 'display_name', None) or other.get_full_name() or other.email,
            'last_activity': last_activity,
            'unread_count': unread_count,
            'last_message': {
                'id': last_msg.id,
                'contenu': (last_msg.contenu or '')[:80],
                'date_envoi': last_msg.date_envoi,
                'sender_id': last_msg.sender_id,
            } if last_msg else None,
        })
    return out


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def conversation_messages(request, pk):
    """Messages d'une conversation. Marque les messages reçus comme lus."""
    conv = get_object_or_404(Conversation, pk=pk)
    if request.user != conv.participant1 and request.user != conv.participant2:
        return Response({'detail': 'Non autorisé.'}, status=status.HTTP_403_FORBIDDEN)
    conv.messages.filter(lu=False).exclude(sender=request.user).update(lu=True)
    messages = conv.messages.select_related('sender').order_by('date_envoi')[:100]
    return Response(MessageSerializer(messages, many=True).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def conversation_send_message(request, pk):
    """Envoyer un message dans la conversation. Body: { "contenu": "..." }"""
    conv = get_object_or_404(Conversation, pk=pk)
    if request.user != conv.participant1 and request.user != conv.participant2:
        return Response({'detail': 'Non autorisé.'}, status=status.HTTP_403_FORBIDDEN)
    contenu = (request.data.get('contenu') or '').strip()
    if not contenu:
        return Response({'error': 'Message vide.'}, status=status.HTTP_400_BAD_REQUEST)
    msg = Message.objects.create(conversation=conv, sender=request.user, contenu=contenu)
    return Response(MessageSerializer(msg).data, status=status.HTTP_201_CREATED)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def conversation_with_user_api(request, user_id):
    """
    GET: détail d'une conversation avec l'utilisateur donné (crée si besoin).
    POST: idem (pour compat). Retourne { "id": <conv_id>, "other_participant": {...} } puis rediriger côté client vers /api/chat/conversations/<id>/messages/
    """
    other = get_object_or_404(User, pk=user_id)
    if other == request.user:
        return Response({'error': 'Impossible de créer une conversation avec soi-même.'}, status=status.HTTP_400_BAD_REQUEST)
    conv = _get_or_create_conversation(request.user, other)
    other_display = getattr(other, 'display_name', None) or other.get_full_name() or other.email
    return Response({
        'id': conv.id,
        'other_participant_id': other.id,
        'other_participant_display_name': other_display,
    })
