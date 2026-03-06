from django.urls import path
from . import views

app_name = 'signalements'

urlpatterns = [
    path('', views.signaler, name='signaler'),
    path('mes-signalements/', views.mes_signalements, name='mes_signalements'),
    path('agent/', views.agent_liste, name='agent_liste'),
    path('agent/<int:pk>/statut/', views.agent_changer_statut, name='agent_changer_statut'),
]
