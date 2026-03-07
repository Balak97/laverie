from django.urls import path
from . import views

app_name = 'chat'

urlpatterns = [
    path('conversations/', views.mes_conversations, name='mes_conversations'),
    path('conversation/<int:pk>/', views.conversation_detail, name='conversation_detail'),
    path('conversation/<int:pk>/messages/', views.conversation_messages_json, name='conversation_messages_json'),
    path('conversation/<int:pk>/send/', views.conversation_send, name='conversation_send'),
    path('conversation/with/<int:user_id>/', views.conversation_with_user, name='conversation_with_user'),
]
