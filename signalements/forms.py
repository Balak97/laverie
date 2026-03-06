from django import forms
from .models import Signalement


class SignalementForm(forms.ModelForm):
    """Formulaire pour signaler un problème (indépendant du lavage)."""
    class Meta:
        model = Signalement
        fields = ('description',)
        widgets = {
            'description': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 min-h-[120px]',
                'placeholder': 'Décrivez le problème rencontré…',
                'rows': 4,
            }),
        }
