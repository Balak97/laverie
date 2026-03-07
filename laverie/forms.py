from django import forms
from django.utils import timezone
from .models import Machine, FonctionMachine, Reservation, MessageLaverie


class MessageLaverieForm(forms.ModelForm):
    class Meta:
        model = MessageLaverie
        fields = ('texte', 'ordre', 'active')
        widgets = {
            'texte': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2.5 border border-gray-300 rounded-xl focus:ring-2 focus:ring-teal-500 focus:border-teal-500',
                'placeholder': 'Ex: Pensez à récupérer votre linge à l\'heure.',
                'maxlength': 500,
            }),
            'ordre': forms.NumberInput(attrs={'class': 'w-full px-4 py-2.5 border border-gray-300 rounded-xl focus:ring-2 focus:ring-teal-500 focus:border-teal-500', 'min': 0}),
            'active': forms.CheckboxInput(attrs={'class': 'rounded border-gray-300 text-teal-600 focus:ring-teal-500'}),
        }


class MachineForm(forms.ModelForm):
    class Meta:
        model = Machine
        fields = ('nom', 'ordre', 'active')
        widgets = {
            'nom': forms.TextInput(attrs={'class': 'w-full px-4 py-2.5 border border-gray-300 rounded-xl focus:ring-2 focus:ring-teal-500 focus:border-teal-500', 'placeholder': 'Ex: Machine 1'}),
            'ordre': forms.NumberInput(attrs={'class': 'w-full px-4 py-2.5 border border-gray-300 rounded-xl focus:ring-2 focus:ring-teal-500 focus:border-teal-500', 'min': 0}),
            'active': forms.CheckboxInput(attrs={'class': 'rounded border-gray-300 text-teal-600 focus:ring-teal-500'}),
        }


class FonctionMachineForm(forms.ModelForm):
    class Meta:
        model = FonctionMachine
        fields = ('machine', 'nom', 'duree_minutes', 'ordre', 'active')
        widgets = {
            'machine': forms.Select(attrs={'class': 'w-full px-4 py-2.5 border border-gray-300 rounded-xl focus:ring-2 focus:ring-teal-500 focus:border-teal-500'}),
            'nom': forms.TextInput(attrs={'class': 'w-full px-4 py-2.5 border border-gray-300 rounded-xl focus:ring-2 focus:ring-teal-500 focus:border-teal-500', 'placeholder': 'Ex: Coton, Jeans'}),
            'duree_minutes': forms.NumberInput(attrs={'class': 'w-full px-4 py-2.5 border border-gray-300 rounded-xl focus:ring-2 focus:ring-teal-500 focus:border-teal-500', 'min': 1}),
            'ordre': forms.NumberInput(attrs={'class': 'w-full px-4 py-2.5 border border-gray-300 rounded-xl focus:ring-2 focus:ring-teal-500 focus:border-teal-500', 'min': 0}),
            'active': forms.CheckboxInput(attrs={'class': 'rounded border-gray-300 text-teal-600 focus:ring-teal-500'}),
        }


class ReservationForm(forms.ModelForm):
    """Réservation : choix machine et programme. Le créneau est placé automatiquement après le dernier ticket actif."""
    class Meta:
        model = Reservation
        fields = ('machine', 'fonction')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        initial_machine = (kwargs.get('initial') or {}).get('machine')
        self.fields['machine'].queryset = Machine.objects.filter(active=True)
        self.fields['machine'].widget.attrs['class'] = 'w-full px-4 py-2.5 border border-gray-300 rounded-xl focus:ring-2 focus:ring-teal-500 focus:border-teal-500'
        if initial_machine:
            self.fields['fonction'].queryset = FonctionMachine.objects.filter(machine=initial_machine, active=True)
        else:
            self.fields['fonction'].queryset = FonctionMachine.objects.filter(active=True)
        self.fields['fonction'].required = True
        self.fields['fonction'].label_from_instance = lambda obj: f"{obj.nom} — {obj.duree_affichage()}"
        self.fields['fonction'].widget.attrs['class'] = 'select-resa w-full pl-4 pr-10 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-teal-500 focus:border-teal-500 bg-white cursor-pointer text-gray-900 shadow-sm appearance-none'
        self.fields['machine'].widget.attrs['class'] = 'select-resa w-full pl-4 pr-10 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-teal-500 focus:border-teal-500 bg-white cursor-pointer text-gray-900 shadow-sm appearance-none'

    def _get_debut_apres_dernier_ticket(self, machine):
        """Retourne le début du prochain créneau = fin du dernier ticket + 5 min (retrait/remise du linge)."""
        from datetime import timedelta
        now = timezone.now()
        dernier = (
            Reservation.objects.filter(
                machine=machine,
                statut__in=('reserve', 'en_cours'),
                fin__gt=now,
            )
            .order_by('-fin')
            .first()
        )
        if dernier:
            return dernier.fin + timedelta(minutes=5)
        return now

    def clean(self):
        data = super().clean()
        machine = data.get('machine')
        fonction = data.get('fonction')

        if not machine or not fonction:
            return data
        if fonction.machine_id != machine.id:
            self.add_error('fonction', 'Cette fonction n\'appartient pas à la machine choisie.')
        return data

    def save(self, commit=True):
        from datetime import timedelta
        instance = super().save(commit=False)
        instance.debut = self._get_debut_apres_dernier_ticket(instance.machine)
        instance.fin = instance.debut + timedelta(minutes=instance.fonction.duree_minutes)
        if commit:
            instance.save()
        return instance
