"""
URLs API REST Chat.
"""
from django.urls import path
from . import api

urlpatterns = [
    path('conversations/', api.conversation_list),
    path('conversations/<int:pk>/messages/', api.conversation_messages),
    path('conversations/<int:pk>/send/', api.conversation_send_message),
    path('conversation-with-user/<int:user_id>/', api.conversation_with_user_api),
]
