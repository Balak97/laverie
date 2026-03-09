"""
API REST Signalements pour Flutter.
"""
from rest_framework import serializers, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Signalement


class SignalementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Signalement
        fields = ['id', 'description', 'statut', 'date_creation']
        read_only_fields = ['statut', 'date_creation']


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def signalement_list(request):
    """Liste des signalements de l'utilisateur connecté."""
    qs = Signalement.objects.filter(utilisateur=request.user).order_by('-date_creation')
    return Response(SignalementSerializer(qs, many=True).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def signalement_create(request):
    """Créer un signalement. Body: { "description": "..." }"""
    serializer = SignalementSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    serializer.save(utilisateur=request.user)
    return Response(serializer.data, status=status.HTTP_201_CREATED)
