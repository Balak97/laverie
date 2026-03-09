"""
URLs API REST Signalements.
"""
from django.urls import path
from . import api

urlpatterns = [
    path('', api.signalement_list),
    path('create/', api.signalement_create),
]
