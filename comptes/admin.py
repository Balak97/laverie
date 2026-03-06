from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _
from .models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    # ✅ Champs affichés dans la liste des utilisateurs
    list_display = ('email', 'first_name', 'last_name', 'user_type', 'is_active', 'is_staff', 'date_inscription')
    list_filter = ('user_type', 'is_active', 'is_staff', 'is_superuser', 'is_premium')
    search_fields = ('email', 'first_name', 'last_name', 'telephone')
    ordering = ('email',)

    # ✅ Champs éditables directement depuis la liste
    list_editable = ('is_active', 'user_type')

    # ✅ Structure des champs dans le formulaire admin
    fieldsets = (
        (_('Informations de connexion'), {
            'fields': ('email', 'password')
        }),
        (_('Informations personnelles'), {
            'fields': ('first_name', 'last_name', 'telephone', 'photo', 'genre', 'user_type', 'is_premium')
        }),
        (_('Permissions'), {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')
        }),
        (_('Dates importantes'), {
            'fields': ('last_login', 'date_joined')
        }),
        (_('Localisation'), {
            'fields': ('latitude', 'longitude')
        }),
    )

    # ✅ Champs à remplir lors de la création d’un nouvel utilisateur dans l’admin
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'first_name', 'last_name', 'telephone', 'password1', 'password2', 'user_type', 'is_active'),
        }),
    )

    # ✅ Pour permettre la connexion avec l’email (au lieu du username)
    def get_fieldsets(self, request, obj=None):
        if not obj:
            return self.add_fieldsets
        return super().get_fieldsets(request, obj)

    def get_readonly_fields(self, request, obj=None):
        # Empêche la modification de l'email si le compte existe déjà
        if obj:
            return ('email',)
        return ()
