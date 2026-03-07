from django.urls import path, include
from django.views.i18n import set_language
from . import views
from rest_framework.routers import DefaultRouter
# api
from .api.app import UserViewSet, current_user_profile, assistant_chat

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')

# Endpoints API comptes (préfixe /api/) :
#   POST   /api/users/                      → Inscription (body: email, password, password2, ...)
#   POST   /api/users/resend-activation/    → Renvoyer lien d'activation (body: email) si mail non reçu
#   POST   /api/users/activate/             → Activer le compte (body: uidb64, token)
#   POST   /api/users/password-reset/       → Mot de passe oublié, envoi email (body: email)
#   POST   /api/users/password-reset-confirm/ → Confirmer nouveau mot de passe (body: uidb64, token, new_password)
#   GET    /me/                             → Profil utilisateur connecté
#   GET    /api/assistant/                  → Message de bienvenue (buttons: [])
#   POST   /api/assistant/                  → Réponse + boutons (body: { "message": "..." })

urlpatterns = [
    path('i18n/setlang/', set_language, name='set_language'),
    path('', views.home, name='home'),
    path('accounts/login/', views.login_f, name='login'),
    path('logout/', views.log_out, name='logout'),

    path('creer_un_compte/', views.register, name='creation_compte'),
    path('inscription-en-attente/', views.registration_pending, name='registration_pending'),
    path('activate/<uidb64>/<token>/', views.activate, name='activate'),
    path('renvoyer-activation/', views.resend_activation_view, name='resend_activation'),

    # Réinitialisation mot de passe
    path('password-reset/', views.password_reset_view, name='password_reset'),
    path('password-reset/done/', views.password_reset_done_view, name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/', views.password_reset_confirm_view, name='password_reset_confirm'),
    path('password-reset-complete/', views.password_reset_complete_view, name='password_reset_complete'),

    # Dashboards
    path('dashboard/', views.dashboard, name='dashboard'),
    path('dashboard/admin/', views.dashboard_admin, name='dashboard_admin'),
    path('dashboard/admin/renvoyer-emails/', views.renvoyer_emails_non_envoyes, name='renvoyer_emails_non_envoyes'),
 
    
    # Gestion des coursiers
    path('users/', views.list_users, name='list_users'),
   
    
    # Profil utilisateur
    path('profile/', views.profile, name='profile'),

    # Laverie (salle à laver du dortoir)
    path('laverie/', include('laverie.urls')),

    # Signalements (problèmes signalés par les utilisateurs)
    path('signalements/', include('signalements.urls')),

    # Chat (messagerie)
    path('chat/', include('chat.urls')),

    # api
    path('api/', include(router.urls)),
    path('api/assistant/', assistant_chat, name='api-assistant'),
    path('me/', current_user_profile, name='current-user-profile'),
]
