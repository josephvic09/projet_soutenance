from django import forms
from .models import Logement, Avis, Reservation


class RechercheForm(forms.Form):

    q = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Quartier, ville, type de logement...',
        })
    )
    ville = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ville',
        })
    )
    quartier = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Quartier',
        })
    )
    type_logement = forms.ChoiceField(
        required=False,
        choices=[('', 'Tous types')] + Logement.TYPE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    type_offre = forms.ChoiceField(
        required=False,
        choices=[('', 'Location / Vente')] + Logement.OFFRE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    prix_min = forms.IntegerField(
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Prix min (FCFA)',
        })
    )
    prix_max = forms.IntegerField(
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Prix max (FCFA)',
        })
    )
    nb_chambres = forms.IntegerField(
        required=False,
        min_value=1,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Chambres min',
        })
    )
    standing = forms.ChoiceField(
        required=False,
        choices=[('', 'Tout standing')] + Logement.STANDING_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    # Équipements
    wifi          = forms.BooleanField(required=False)
    parking       = forms.BooleanField(required=False)
    climatisation = forms.BooleanField(required=False)
    gardien       = forms.BooleanField(required=False)
    piscine       = forms.BooleanField(required=False)
    generateur    = forms.BooleanField(required=False)


class LogementForm(forms.ModelForm):

    class Meta:
        model = Logement
        fields = [
            'titre', 'description', 'type_logement', 'type_offre',
            'standing', 'meuble', 'ville', 'quartier', 'adresse',
            'latitude', 'longitude', 'surface', 'nb_chambres',
            'nb_salles_bain', 'nb_toilettes', 'etage',
            'prix', 'prix_negociable', 'charges', 'caution',
            'eau_courante', 'electricite', 'internet', 'climatisation',
            'parking', 'gardien', 'generateur', 'piscine',
            'cuisine_equipee', 'balcon', 'securite',
            'disponible', 'date_disponibilite',
        ]
        widgets = {
            'titre':       forms.TextInput(attrs={
                            'class': 'form-control',
                            'placeholder': 'Ex: Bel appartement F3 à Bastos'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
            'type_logement': forms.Select(attrs={'class': 'form-select'}),
            'type_offre':    forms.Select(attrs={'class': 'form-select'}),
            'standing':      forms.Select(attrs={'class': 'form-select'}),
            'meuble':        forms.Select(attrs={'class': 'form-select'}),
            'ville':         forms.Select(attrs={'class': 'form-select'}),
            'quartier':      forms.Select(attrs={'class': 'form-select'}),
            'adresse':       forms.TextInput(attrs={'class': 'form-control'}),
            'surface':       forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'm²'}),
            'nb_chambres':   forms.NumberInput(attrs={'class': 'form-control'}),
            'nb_salles_bain':forms.NumberInput(attrs={'class': 'form-control'}),
            'nb_toilettes':  forms.NumberInput(attrs={'class': 'form-control'}),
            'etage':         forms.NumberInput(attrs={'class': 'form-control'}),
            'prix':          forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'FCFA'}),
            'charges':       forms.NumberInput(attrs={'class': 'form-control'}),
            'caution':       forms.NumberInput(attrs={'class': 'form-control'}),
            'date_disponibilite': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'latitude':      forms.HiddenInput(),
            'longitude':     forms.HiddenInput(),
        }


class AvisForm(forms.ModelForm):

    class Meta:
        model = Avis
        fields = ['note', 'commentaire']
        widgets = {
            'note': forms.RadioSelect(
                choices=[(i, f'{i} ⭐') for i in range(1, 6)]
            ),
            'commentaire': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Partagez votre expérience...',
            }),
        }


class ReservationForm(forms.ModelForm):

    class Meta:
        model = Reservation
        fields = ['type_demande', 'date_debut', 'date_fin', 'message']
        widgets = {
            'type_demande': forms.Select(attrs={'class': 'form-select'}),
            'date_debut':   forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'date_fin':     forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'message':      forms.Textarea(attrs={
                                'class': 'form-control',
                                'rows': 3,
                                'placeholder': 'Message au bailleur (optionnel)',
                            }),
        }