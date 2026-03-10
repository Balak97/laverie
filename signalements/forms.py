from django import forms
from .models import Signalement


class SignalementForm(forms.ModelForm):
    """Formulaire pour signaler un problème (indépendant du lavage)."""
    def __init__(self, *args, lang=None, i18n=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._i18n = i18n or {}
        if self._i18n:
            self.fields['description'].label = self._i18n.get('problem_description', 'Problem description')
            self.fields['description'].widget.attrs['placeholder'] = self._i18n.get(
                'placeholder_description', 'Describe the problem you encountered…'
            )
        self.fields['description'].widget.attrs['class'] = (
            'w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-indigo-500 '
            'focus:border-indigo-500 min-h-[120px]'
        )
        self.fields['description'].widget.attrs['rows'] = 4

    class Meta:
        model = Signalement
        fields = ('description',)
