from django.urls import path
from . import views

app_name = 'laverie'

urlpatterns = [
    path('', views.accueil, name='accueil'),
    path('reserver/', views.reserver, name='reserver'),
    path('mes-tickets/', views.mes_tickets, name='mes_tickets'),
    path('machine/<int:pk>/tickets/', views.tickets_machine, name='tickets_machine'),
    path('ticket/<int:pk>/', views.afficher_ticket, name='afficher_ticket'),
    path('mes-tickets/<int:pk>/annuler/', views.annuler_ticket, name='annuler_ticket'),
    path('api/creneaux/', views.api_creneaux, name='api_creneaux'),
    path('api/fonctions/', views.api_fonctions_machine, name='api_fonctions'),
    # Agent
    path('agent/machines/', views.agent_machines, name='agent_machines'),
    path('agent/machines/ajout/', views.agent_machine_ajout, name='agent_machine_ajout'),
    path('agent/machines/<int:pk>/', views.agent_machine_modifier, name='agent_machine_modifier'),
    path('agent/fonctions/ajout/', views.agent_fonction_ajout, name='agent_fonction_ajout'),
    path('agent/fonctions/<int:pk>/', views.agent_fonction_modifier, name='agent_fonction_modifier'),
    path('agent/fonctions/<int:pk>/toggle/', views.agent_fonction_toggle_active, name='agent_fonction_toggle_active'),
    path('agent/fonctions/copier/', views.agent_fonction_copier, name='agent_fonction_copier'),
    path('agent/messages/', views.agent_messages, name='agent_messages'),
    path('agent/messages/ajout/', views.agent_message_ajout, name='agent_message_ajout'),
    path('agent/messages/<int:pk>/', views.agent_message_modifier, name='agent_message_modifier'),
    path('agent/messages/<int:pk>/supprimer/', views.agent_message_supprimer, name='agent_message_supprimer'),
]
