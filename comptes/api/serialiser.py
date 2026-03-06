# comptes/serializers.py
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password

CustomUser = get_user_model()

# Import des serializers de colis (optionnel, pour UserProfileSerializer)
try:
    from monkilo.api.serialiser import ItineraireListSerializer, DemandeColisListSerializer
except ImportError:
    ItineraireListSerializer = DemandeColisListSerializer = None


class UserSerializer(serializers.ModelSerializer):
    """Version légère : utilisée pour la liste des utilisateurs (admins seulement)"""
    photo_url = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = [
            'id', 'username', 'email', 'telephone', 'user_type',
            'is_premium', 'genre', 'date_inscription',
            'display_name', 'is_online', 'photo', 'photo_url'
        ]
        read_only_fields = fields

    def get_photo_url(self, obj):
        """URL complète de la photo de profil pour le front (Flutter)."""
        if not obj.photo:
            return None
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(obj.photo.url)
        return obj.photo.url if obj.photo else None


class UserProfileSerializer(serializers.ModelSerializer):
    """Version complète : utilisée pour le détail (retrieve)"""
    mes_itineraires = serializers.SerializerMethodField()
    mes_demandes = serializers.SerializerMethodField()
    photo_url = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = [
            'id', 'username', 'email', 'telephone', 'user_type',
            'is_premium', 'genre', 'date_inscription',
            'display_name', 'is_online', 'photo', 'photo_url',
            'mes_itineraires', 'mes_demandes'
        ]
        read_only_fields = fields

    def get_photo_url(self, obj):
        """URL complète de la photo de profil pour le front (Flutter)."""
        if not obj.photo:
            return None
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(obj.photo.url)
        return obj.photo.url if obj.photo else None

    def get_mes_itineraires(self, obj):
        # Seulement si le serializer existe et si l'utilisateur est premium
        if ItineraireListSerializer and obj.is_premium:
            return ItineraireListSerializer(
                obj.itineraires.all(), many=True, context=self.context
            ).data
        return []

    def get_mes_demandes(self, obj):
        if DemandeColisListSerializer:
            return DemandeColisListSerializer(
                obj.demandes_colis.all(), many=True, context=self.context
            ).data
        return []



class UserCreateUpdateSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(required=True)
    telephone = serializers.CharField(required=False, allow_blank=True, max_length=20)
    password = serializers.CharField(
        write_only=True,
        min_length=6,
        required=True,
        validators=[validate_password]
    )
    password2 = serializers.CharField(write_only=True, required=True)
    genre = serializers.ChoiceField(choices=CustomUser.GENRE, required=False, allow_blank=True)

    class Meta:
        model = CustomUser
        fields = [
            'email', 'telephone', 'password', 'password2',
            'first_name', 'last_name', 'genre'
        ]
        extra_kwargs = {
            'email': {'required': True},
            'first_name': {'required': False},
            'last_name': {'required': False},
        }

    def validate(self, attrs):
        """Validation globale"""
        # Vérifier que les mots de passe correspondent
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({
                "password": "Les mots de passe ne correspondent pas."
            })
        return attrs
    
    def validate_email(self, value):
        """Validation email unique"""
        if CustomUser.objects.filter(email=value).exists():
            raise serializers.ValidationError("Un utilisateur avec cet email existe déjà.")
        return value
    
    def validate_telephone(self, value):
        """Validation téléphone unique (vide autorisé pour inscription par email)"""
        value = (value or '').strip()
        if not value:
            return value
        if CustomUser.objects.filter(telephone=value).exists():
            raise serializers.ValidationError("Ce numéro de téléphone est déjà utilisé.")
        if CustomUser.objects.filter(username=value).exists():
            raise serializers.ValidationError("Ce numéro est déjà utilisé.")
        return value
    
    def create(self, validated_data):
        """Création d'un nouvel utilisateur"""
        request = self.context.get('request')

        validated_data.pop('password2')
        if request and request.user.is_authenticated and request.user.user_type == 'ADMIN':
            user_type = validated_data.pop('user_type', 'client')
        else:
            user_type = 'client'

        validated_data['user_type'] = user_type
        password = validated_data.pop('password')
        telephone = (validated_data.get('telephone') or '').strip()
        email = validated_data.get('email', '').strip().lower()
        # Username = email pour cohérence avec le web et pour que le login avec email fonctionne
        validated_data['username'] = email if email else (telephone or email)
        if not telephone:
            validated_data['telephone'] = ''

        user = CustomUser(**validated_data)
        user.set_password(password)
        user.save()
        return user
    
    def update(self, instance, validated_data):
        """Mise à jour d'un utilisateur existant"""
        request = self.context.get('request')
        
        # Gérer password2 si présent
        if 'password2' in validated_data:
            validated_data.pop('password2')
        
        # Ne pas permettre la modification du téléphone (car c'est le username)
        if 'telephone' in validated_data:
            raise serializers.ValidationError({
                "telephone": "Le numéro de téléphone ne peut pas être modifié."
            })
        
        # Ne pas permettre la modification de l'email sans admin
        if 'email' in validated_data and validated_data['email'] != instance.email:
            if not (request and request.user.is_authenticated and request.user.user_type == 'ADMIN'):
                raise serializers.ValidationError({
                    "email": "Seul un administrateur peut modifier l'email."
                })
        
        # Restrictions pour non-admins
        if not (request and request.user.is_authenticated and request.user.user_type == 'ADMIN'):
            validated_data.pop('user_type', None)
            validated_data.pop('is_premium', None)
        
        # Mettre à jour le mot de passe si fourni
        if 'password' in validated_data:
            password = validated_data.pop('password')
            instance.set_password(password)
        
        # Mettre à jour les autres champs
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        instance.save()
        return instance
