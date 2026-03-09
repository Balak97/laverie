"""
URLs API REST Laverie.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .api import MachineViewSet, ReservationViewSet

router = DefaultRouter()
router.register(r'machines', MachineViewSet, basename='api-laverie-machine')
router.register(r'reservations', ReservationViewSet, basename='api-laverie-reservation')

urlpatterns = [
    path('', include(router.urls)),
]
