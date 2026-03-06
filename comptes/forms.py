from django import forms
from django.contrib.auth.forms import UserCreationForm, PasswordResetForm
from django.utils.translation import gettext_lazy as _
from .models import CustomUser


class CustomUserCreationForm(UserCreationForm):
    password1 = forms.CharField(
        label=_("Password"),
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl '
                     'focus:outline-none focus:ring-2 focus:ring-indigo-200 focus:border-indigo-500',
            'placeholder': _("Enter your password"),
        })
    )
    password2 = forms.CharField(
        label=_("Confirm password"),
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl '
                     'focus:outline-none focus:ring-2 focus:ring-indigo-200 focus:border-indigo-500',
            'placeholder': _("Confirm your password"),
        })
    )

    class Meta:
        model = CustomUser
        fields = ['email', 'first_name', 'last_name', 'telephone', 'photo']
        labels = {
            'email': _("Email address"),
            'first_name': _("First name"),
            'last_name': _("Last name"),
            'telephone': _("Phone number"),
            'photo': _("Photo"),
        }
        widgets = {
            'email': forms.EmailInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl '
                         'focus:outline-none focus:ring-2 focus:ring-indigo-200 focus:border-indigo-500',
                'placeholder': _("Email address"),
            }),
            'first_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl '
                         'focus:outline-none focus:ring-2 focus:ring-indigo-200 focus:border-indigo-500',
                'placeholder': _("First name"),
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl '
                         'focus:outline-none focus:ring-2 focus:ring-indigo-200 focus:border-indigo-500',
                'placeholder': _("Last name"),
            }),
            'telephone': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl '
                         'focus:outline-none focus:ring-2 focus:ring-indigo-200 focus:border-indigo-500',
                'placeholder': _("Phone number"),
            }),
            'photo': forms.ClearableFileInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl '
                         'focus:outline-none focus:ring-2 focus:ring-indigo-200 focus:border-indigo-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:bg-indigo-50 file:text-indigo-600',
            }),
        }

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        if CustomUser.objects.filter(email=email).exists():
            raise forms.ValidationError(_("This email is already in use."))
        return email

    def clean_photo(self):
        photo = self.cleaned_data.get('photo')
        if photo and photo.size > 2 * 1024 * 1024:  # 2 Mo max
            raise forms.ValidationError(_("Photo must not exceed 2 MB."))
        return photo


class ModifierCustomUserCreationForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'user_type', 'telephone', 'photo']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'user_type': forms.Select(attrs={'class': 'form-control'}),
            'telephone': forms.TextInput(attrs={'class': 'form-control'}),
            'photo': forms.FileInput(attrs={'class': 'form-control'}),
        }


class LoginForm(forms.Form):
    username = forms.CharField(
        label="Nom d'utilisateur ou e-mail",
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    password = forms.CharField(
        label="Mot de passe",
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )


class ProfileUpdateForm(forms.ModelForm):
    """Formulaire pour modifier les informations du profil"""
    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'genre', 'photo']
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-transparent',
                'placeholder': 'Prénom'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-transparent',
                'placeholder': 'Nom'
            }),
            'genre': forms.Select(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-transparent'
            }),
            'photo': forms.ClearableFileInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-transparent file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-cyan-50 file:text-cyan-700 hover:file:bg-cyan-100'
            }),
        }

    def clean_photo(self):
        photo = self.cleaned_data.get('photo')
        if photo:
            if photo.size > 2 * 1024 * 1024:  # 2 Mo max
                raise forms.ValidationError("La photo ne doit pas dépasser 2 Mo.")
            # Vérifier l'extension
            valid_extensions = ['.jpg', '.jpeg', '.png', '.gif']
            ext = photo.name.lower().split('.')[-1]
            if f'.{ext}' not in valid_extensions:
                raise forms.ValidationError("Format d'image non supporté. Utilisez JPG, PNG ou GIF.")
        return photo


class PasswordChangeForm(forms.Form):
    """Formulaire pour changer le mot de passe"""
    old_password = forms.CharField(
        label="Ancien mot de passe",
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-transparent',
            'placeholder': 'Entrez votre ancien mot de passe'
        })
    )
    new_password1 = forms.CharField(
        label="Nouveau mot de passe",
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-transparent',
            'placeholder': 'Entrez votre nouveau mot de passe'
        }),
        min_length=8,
        help_text="Le mot de passe doit contenir au moins 8 caractères."
    )
    new_password2 = forms.CharField(
        label="Confirmer le nouveau mot de passe",
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-transparent',
            'placeholder': 'Confirmez votre nouveau mot de passe'
        })
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_old_password(self):
        old_password = self.cleaned_data.get('old_password')
        if not self.user.check_password(old_password):
            raise forms.ValidationError("L'ancien mot de passe est incorrect.")
        return old_password

    def clean_new_password2(self):
        password1 = self.cleaned_data.get('new_password1')
        password2 = self.cleaned_data.get('new_password2')
        if password1 and password2:
            if password1 != password2:
                raise forms.ValidationError("Les deux mots de passe ne correspondent pas.")
        return password2

    def save(self):
        password = self.cleaned_data['new_password1']
        self.user.set_password(password)
        self.user.save()
        return self.user


class CustomPasswordResetForm(PasswordResetForm):
    """Formulaire personnalisé pour la réinitialisation de mot de passe utilisant l'email"""
    email = forms.EmailField(
        label="Adresse e-mail",
        max_length=254,
        widget=forms.EmailInput(attrs={
            'class': 'w-full pl-10 pr-4 py-3 bg-gray-50 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition text-gray-700 placeholder-gray-500 text-sm',
            'placeholder': 'votre@email.com',
            'autocomplete': 'email'
        })
    )

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            email = email.lower().strip()
            # Vérifier que l'utilisateur existe avec cet email
            if not CustomUser.objects.filter(email=email).exists():
                raise forms.ValidationError(
                    "Aucun compte n'est associé à cette adresse e-mail."
                )
        return email

    def get_users(self, email):
        """Retourne les utilisateurs correspondant à l'email"""
        return CustomUser.objects.filter(email__iexact=email, is_active=True)