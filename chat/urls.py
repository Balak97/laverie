from django.urls import path
from . import views

app_name = 'chat'

urlpatterns = [
    path('conversations/', views.mes_conversations, name='mes_conversations'),
    path('conversation/<int:pk>/', views.conversation_detail, name='conversation_detail'),
]
