"""
API REST Laverie pour Flutter.
"""
from datetime import timedelta
from rest_framework import serializers, viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.utils.translation import gettext as _
from .models import Machine, FonctionMachine, Reservation, MAX_TICKETS_SAME_DAY_SAME_MACHINE

MAX_EXTEND_MINUTES = 20


# ——— Serializers ———

class FonctionMachineSerializer(serializers.ModelSerializer):
    duree_affichage = serializers.SerializerMethodField()

    class Meta:
        model = FonctionMachine
        fields = ['id', 'nom', 'duree_minutes', 'duree_affichage', 'ordre']

    def get_duree_affichage(self, obj):
        return obj.duree_affichage()

class MachineSerializer(serializers.ModelSerializer):
    fonctions = FonctionMachineSerializer(many=True, read_only=True)

    class Meta:
        model = Machine
        fields = ['id', 'nom', 'ordre', 'fonctions']


class ReservationSerializer(serializers.ModelSerializer):
    machine_nom = serializers.CharField(source='machine.nom', read_only=True)
    fonction_nom = serializers.CharField(source='fonction.nom', read_only=True, allow_null=True)
    duree_minutes = serializers.SerializerMethodField()

    class Meta:
        model = Reservation
        fields = [
            'id', 'numero', 'machine', 'machine_nom', 'fonction', 'fonction_nom',
            'debut', 'fin', 'statut', 'date_creation', 'duree_minutes',
        ]
        read_only_fields = ['numero', 'debut', 'fin', 'statut', 'date_creation']

    def get_duree_minutes(self, obj):
        return obj.duree_minutes()


class ReservationCreateSerializer(serializers.Serializer):
    machine = serializers.PrimaryKeyRelatedField(queryset=Machine.objects.filter(active=True))
    fonction = serializers.PrimaryKeyRelatedField(queryset=FonctionMachine.objects.filter(active=True))

    def validate_fonction(self, value):
        machine = self.initial_data.get('machine')
        if isinstance(machine, Machine):
            mid = machine.id
        else:
            mid = machine
        if value.machine_id != mid:
            raise serializers.ValidationError(_("This function does not belong to the selected machine."))
        return value

    def create(self, validated_data):
        request = self.context['request']
        Reservation.marquer_tickets_termines()
        Reservation.marquer_tickets_en_cours()
        machine = validated_data['machine']
        fonction = validated_data['fonction']
        now = timezone.now()
        dernier = (
            Reservation.objects.filter(
                machine=machine,
                statut__in=('reserve', 'en_cours'),
                fin__gt=now,
            )
            .order_by('-fin')
            .first()
        )
        if dernier:
            debut = dernier.fin + timedelta(minutes=5)
        else:
            # Personne sur la machine : premier créneau dans 5 minutes
            debut = now + timedelta(minutes=5)
        nb_meme_jour = Reservation.count_user_same_day_machine(request.user, machine, debut.date())
        if nb_meme_jour >= MAX_TICKETS_SAME_DAY_SAME_MACHINE:
            raise serializers.ValidationError(
                _('You cannot take more than %(max)s tickets on the same day on the same machine.') % {'max': MAX_TICKETS_SAME_DAY_SAME_MACHINE}
            )
        fin = debut + timedelta(minutes=fonction.duree_minutes)
        return Reservation.objects.create(
            utilisateur=request.user,
            machine=machine,
            fonction=fonction,
            debut=debut,
            fin=fin,
            statut='reserve',
        )


# ——— ViewSets ———

class MachineViewSet(viewsets.ReadOnlyModelViewSet):
    """Liste et détail des machines (lecture seule)."""
    permission_classes = [IsAuthenticated]
    serializer_class = MachineSerializer
    queryset = Machine.objects.filter(active=True).prefetch_related('fonctions').order_by('ordre', 'nom')

    @action(detail=True, methods=['get'], url_path='tickets')
    def tickets(self, request, pk=None):
        """Tickets (en attente + en cours) pour cette machine."""
        Reservation.marquer_tickets_termines()
        Reservation.marquer_tickets_en_cours()
        machine = self.get_object()
        now = timezone.now()
        tickets = Reservation.objects.filter(
            machine=machine,
            statut__in=('reserve', 'en_cours'),
            fin__gt=now,
        ).select_related('utilisateur', 'fonction').order_by('debut')
        data = []
        for r in tickets:
            data.append({
                **ReservationSerializer(r).data,
                'utilisateur_id': r.utilisateur_id,
                'utilisateur_display_name': getattr(r.utilisateur, 'display_name', None) or r.utilisateur.get_full_name() or r.utilisateur.email,
            })
        return Response(data)


class ReservationViewSet(viewsets.ModelViewSet):
    """Mes réservations : liste, détail, créer, annuler (pas de update)."""
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Reservation.objects.filter(utilisateur=self.request.user).select_related(
            'machine', 'fonction'
        ).order_by('-debut')

    def get_serializer_class(self):
        if self.action == 'create':
            return ReservationCreateSerializer
        return ReservationSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reservation = serializer.save()
        return Response(
            ReservationSerializer(reservation).data,
            status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        return Response({'detail': 'Méthode non autorisée.'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def partial_update(self, request, *args, **kwargs):
        return Response({'detail': 'Méthode non autorisée.'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def destroy(self, request, *args, **kwargs):
        """Annuler une réservation (si statut = reserve)."""
        reservation = self.get_object()
        if reservation.statut != 'reserve':
            return Response(
                {'error': 'Cette réservation ne peut plus être annulée.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        reservation.statut = 'annule'
        reservation.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'], url_path='creneaux')
    def creneaux(self, request):
        """Créneaux occupés pour une machine. Query: ?machine_id=1"""
        machine_id = request.query_params.get('machine_id')
        if not machine_id:
            return Response({'creneaux': []})
        now = timezone.now()
        resas = Reservation.objects.filter(
            machine_id=machine_id,
            statut__in=('reserve', 'en_cours'),
            fin__gt=now,
        ).values('debut', 'fin')
        creneaux = [{'debut': r['debut'].isoformat(), 'fin': r['fin'].isoformat()} for r in resas]
        return Response({'creneaux': creneaux})

    @action(detail=False, methods=['get'])
    def ticket_en_cours(self, request):
        """Ticket actuellement en cours pour l'utilisateur connecté."""
        Reservation.marquer_tickets_termines()
        Reservation.marquer_tickets_en_cours()
        now = timezone.now()
        resa = (
            Reservation.objects.filter(
                utilisateur=request.user,
                statut__in=('reserve', 'en_cours'),
                debut__lte=now,
                fin__gte=now,
            )
            .select_related('machine', 'fonction')
            .first()
        )
        if not resa:
            return Response(None)
        return Response(ReservationSerializer(resa).data)

    @action(detail=True, methods=['post'], url_path='modify-duration')
    def modify_duration(self, request, pk=None):
        """Prolonger (max +60 min) ou raccourcir le créneau. Autorisé en reserve et en_cours."""
        Reservation.marquer_tickets_termines()
        Reservation.marquer_tickets_en_cours()
        resa = self.get_object()
        if resa.statut not in ('reserve', 'en_cours'):
            return Response(
                {'error': _('This ticket can no longer be modified.')},
                status=status.HTTP_400_BAD_REQUEST,
            )
        now = timezone.now()
        add_minutes = request.data.get('add_minutes')
        subtract_minutes = request.data.get('subtract_minutes')

        if add_minutes is not None:
            try:
                add_minutes = max(0, int(add_minutes))
            except (TypeError, ValueError):
                add_minutes = 0
            duree_prog = resa.fonction.duree_minutes if resa.fonction else 60
            max_fin = resa.debut + timedelta(minutes=duree_prog + MAX_EXTEND_MINUTES)
            max_ajout_restant = int((max_fin - resa.fin).total_seconds() / 60)
            add_minutes = min(add_minutes, max(0, max_ajout_restant))
            if add_minutes <= 0:
                return Response(
                    {'error': _('Total duration cannot exceed program duration + %(max)s minutes.') % {'max': MAX_EXTEND_MINUTES}},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            old_fin = resa.fin
            new_fin = old_fin + timedelta(minutes=add_minutes)
            delta = timedelta(minutes=add_minutes)
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
            return Response(ReservationSerializer(resa).data)

        return Response(
            {'error': _('Invalid action.')},
            status=status.HTTP_400_BAD_REQUEST,
        )
