"""
URLs racine du projet Dortoir 3.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

admin.site.site_header = "Dortoir 3 — Administration"
admin.site.site_title = "Dortoir 3"

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('comptes.urls')),
]

if settings.DEBUG and settings.MEDIA_ROOT:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
