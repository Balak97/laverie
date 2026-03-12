from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str
from .forms import CustomUserCreationForm, ModifierCustomUserCreationForm
from .models import CustomUser
from django.conf import settings
from .emails import envoyer_email_activation, envoyer_email_renvoyer_activation
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth import views as auth_views
from django.urls import reverse_lazy
from django.utils.translation import gettext
from .forms import CustomPasswordResetForm

# Vues de réinitialisation du mot de passe (pour éviter import circulaire dans urls)
password_reset_view = auth_views.PasswordResetView.as_view(
    form_class=CustomPasswordResetForm,
    template_name='comptes/reset/password_reset_form.html',
    email_template_name='comptes/emails/password_reset_email.html',
    success_url=reverse_lazy('password_reset_done'),
)
password_reset_done_view = auth_views.PasswordResetDoneView.as_view(
    template_name='comptes/reset/password_reset_done.html',
)
password_reset_confirm_view = auth_views.PasswordResetConfirmView.as_view(
    template_name='comptes/reset/password_reset_confirm.html',
    success_url=reverse_lazy('password_reset_complete'),
)
password_reset_complete_view = auth_views.PasswordResetCompleteView.as_view(
    template_name='comptes/reset/password_reset_complete.html',
)


def home(request):
    """Page d'accueil Dortoir 3."""
    return render(request, 'home.html')


def register(request):
    """
    Inscription d'un nouvel utilisateur avec validation par e-mail.
    """
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.username = user.email  # l'identifiant sera l'email
            user.is_active = False       # compte inactif jusqu’à validation
            user.save()

            # Génération du lien d’activation
            try:
                envoyer_email_activation(user, request)
            except Exception:
                pass

            return redirect('registration_pending')
        else:
            messages.error(request, "Veuillez corriger les erreurs dans le formulaire.")
    else:
        form = CustomUserCreationForm()

    return render(request, 'comptes/register.html', {'form': form})


def registration_pending(request):
    """
    Page affichée après une inscription réussie (accès en GET uniquement).
    Utiliser une redirection après POST évite le renvoi des données au rechargement (F5).
    """
    return render(request, 'comptes/emails/registration_pending.html')


@login_required
def modifier_compte(request):
    """
    Modification du profil utilisateur (seulement si actif).
    """
    user = request.user
    form = ModifierCustomUserCreationForm(request.POST or None, request.FILES or None, instance=user)

    if request.method == 'POST':
        if not user.is_active:
            messages.warning(request, "Votre compte est inactif. Modification refusée.")
        elif form.is_valid():
            form.save()
            messages.success(request, "Votre compte a bien été modifié.")
            return redirect('modifier_compte')
        else:
            messages.error(request, "Veuillez corriger les erreurs dans le formulaire.")

    return render(request, 'comptes/modifier.html', {'form': form})




User = get_user_model()

def resend_activation_view(request):
    if request.method == "POST":
        email = request.POST.get("email")

        if not email:
            return render(request, "comptes/emails/renvoyer_activation.html", {
                "error": "Veuillez saisir une adresse email."
            })

        try:
            user = User.objects.get(email=email, is_active=False)
        except User.DoesNotExist:
            return render(request, "comptes/emails/renvoyer_activation.html", {
                "error": "Aucun compte inactif trouvé pour cet email."
            })

        try:
            envoyer_email_renvoyer_activation(user, request)
        except Exception:
            return render(request, "comptes/emails/renvoyer_activation.html", {
                "error": "L'envoi de l'email a échoué. Réessayez plus tard."
            })

        return render(request, "comptes/emails/registration_pending.html")

    return render(request, "comptes/emails/renvoyer_activation.html")


def activate(request, uidb64, token):
    """
    Activation du compte après clic sur le lien reçu par e-mail.
    """
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = CustomUser.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
        user = None

    if user and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save()
        return render(request, 'comptes/emails/activation_success.html')
    else:
        return render(request, 'comptes/emails/activation_invalid.html')



def login_f(request):
  
    if request.method == 'POST':
        identifier = request.POST.get('username', '').strip()  # username ou email
        password = request.POST.get('password', '')

        # Par défaut on essaye directement l'identifiant fourni
        username_to_try = identifier

        # Si l'identifiant ressemble à un email, on essaye de récupérer l'utilisateur
        # pour utiliser son username (utile si ton backend ne supporte pas l'email directement)
        if '@' in identifier:
            try:
                u = User.objects.get(email__iexact=identifier)
                username_to_try = u.get_username()
            except User.DoesNotExist:
                # on laisse username_to_try tel quel, authenticate retournera None
                pass

        # APPEL IMPORTANT : authenticate(request=...) -> axes peut compter les échecs
        user = authenticate(request=request, username=username_to_try, password=password)

        if user is not None:
            # authenticate() a défini user.backend -> login() nève pas d'erreur
            
            # Fusionner le panier de session avec le panier de l'utilisateur
          
            
            # Récupérer le panier de session (anonyme) avant la connexion
            session_key = request.session.session_key
        
            
            # Connecter l'utilisateur
            login(request, user)
            
            # Mettre à jour la dernière activité
            user.update_activity()
            
            # Récupérer ou créer le panier de l'utilisateur
            # OneToOneField : un seul panier par utilisateur (actif ou inactif)
            #user_cart, created = Cart.objects.get_or_create(user=user)
            # Réactiver le panier s'il était inactif
            return redirect('home')
            
            
        else:
            # authenticate a échoué -> axes enregistre l'échec automatiquement
            messages.error(request, "Nom d'utilisateur ou mot de passe incorrect.")
    return render(request, 'comptes/login.html')


def log_out(request):
    # Mettre à jour la dernière activité avant déconnexion (optionnel)
    if request.user.is_authenticated:
        request.user.last_activity = None
        request.user.save(update_fields=['last_activity'])
    logout(request)
    return redirect('home')


@login_required
def dashboard(request):
    """
    Dashboard principal : admin → dashboard admin, sinon → espace étudiant (Dortoir 3).
    """
    if getattr(request.user, 'user_type', None) == 'ADMIN':
        return redirect('dashboard_admin')
    # Espace étudiant : laverie + signalements
    from laverie.models import Reservation
    from signalements.models import Signalement
    from django.utils import timezone
    now = timezone.now()
    mes_tickets = Reservation.objects.filter(utilisateur=request.user, statut__in=('reserve', 'en_cours'), fin__gt=now).count()
    mes_signalements = Signalement.objects.filter(utilisateur=request.user).count()
    signalements_non_resolus = Signalement.objects.filter(utilisateur=request.user).exclude(statut='resolu').count()
    return render(request, 'comptes/dashboards/client_dashboard.html', {
        'mes_tickets': mes_tickets,
        'mes_signalements': mes_signalements,
        'signalements_non_resolus': signalements_non_resolus,
    })


@login_required
def dashboard_admin(request):
    """
    Dashboard administrateur Dortoir 3 : utilisateurs, laverie, signalements.
    """
    if request.user.user_type != 'ADMIN':
        from django.contrib import messages
        messages.error(request, gettext("Access denied. You must be an administrator."))
        return redirect('home')
    
    from django.utils import timezone
    from comptes.models import CustomUser
    from laverie.models import Machine, Reservation
    from signalements.models import Signalement
    
    now = timezone.now()
    
    total_users = CustomUser.objects.count()
    recent_users = CustomUser.objects.order_by('-date_joined')[:10]
    
    total_machines = Machine.objects.count()
    reservations_actives = Reservation.objects.filter(
        statut__in=('reserve', 'en_cours'), fin__gt=now
    ).count()
    
    total_signalements = Signalement.objects.count()
    signalements_nouveaux = Signalement.objects.filter(statut='nouveau').count()
    signalements_en_cours = Signalement.objects.filter(statut='en_cours').count()
    signalements_resolus = Signalement.objects.filter(statut='resolu').count()
    recent_signalements = Signalement.objects.select_related('utilisateur').order_by('-date_creation')[:10]
    
    context = {
        'total_users': total_users,
        'recent_users': recent_users,
        'total_machines': total_machines,
        'reservations_actives': reservations_actives,
        'total_signalements': total_signalements,
        'signalements_nouveaux': signalements_nouveaux,
        'signalements_en_cours': signalements_en_cours,
        'signalements_resolus': signalements_resolus,
        'recent_signalements': recent_signalements,
    }
    return render(request, 'comptes/dashboards/admin_dashboard.html', context)


@login_required
@require_POST
def renvoyer_emails_non_envoyes(request):
    """Désactivé : ce projet (Dortoir 3) ne gère pas les emails Monkilo."""
    if request.user.user_type != 'ADMIN':
        messages.error(request, gettext("Access denied. You must be an administrator."))
        return redirect('dashboard_admin')
    messages.info(request, gettext("This feature is not used in this project."))
    return redirect('dashboard_admin')





@login_required
def list_users(request):
    """
    Liste les utilisateurs pour permettre aux vendeurs/admin de les promouvoir en coursiers
    """
    # Vérifier que l'utilisateur est vendeur ou admin
    if request.user.user_type not in ['vendeur', 'ADMIN']:
        messages.error(request, gettext("Access denied. You must be a seller or administrator."))
        return redirect('home')
    
    # Liste des utilisateurs (clients) qui peuvent être promus en coursiers
    users = CustomUser.objects.filter(user_type='client').order_by('-date_joined')
    
    context = {
        'users': users,
        'user_display_default': gettext('User'),
    }
    return render(request, 'comptes/list_users.html', context)


@login_required
def profile(request):
    """
    Page de profil utilisateur avec modification des informations et du mot de passe
    """
    from .forms import ProfileUpdateForm, PasswordChangeForm
    
    user = request.user
    profile_form = ProfileUpdateForm(instance=user)
    password_form = PasswordChangeForm(user)
    
    active_tab = request.GET.get('tab', 'profile')  # 'profile' ou 'password'
    
    if request.method == 'POST':
        if 'update_profile' in request.POST:
            profile_form = ProfileUpdateForm(request.POST, request.FILES, instance=user)
            if profile_form.is_valid():
                profile_form.save()
                messages.success(request, gettext("Your profile has been updated successfully."))
                return redirect('profile')
            else:
                active_tab = 'profile'
                messages.error(request, gettext("Please correct the errors in the form."))
        
        elif 'change_password' in request.POST:
            password_form = PasswordChangeForm(user, request.POST)
            if password_form.is_valid():
                password_form.save()
                # Ré-authentifier l'utilisateur après changement de mot de passe
                from django.contrib.auth import update_session_auth_hash
                update_session_auth_hash(request, user)
                messages.success(request, gettext("Your password has been changed successfully."))
                return redirect('profile?tab=password')
            else:
                active_tab = 'password'
                messages.error(request, gettext("Please correct the errors in the form."))
    
    context = {
        'profile_form': profile_form,
        'password_form': password_form,
        'active_tab': active_tab,
        'user': user,
        'phone_not_provided': gettext('Not provided'),
    }
    return render(request, 'comptes/profile.html', context)