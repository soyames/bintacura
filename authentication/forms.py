"""
Authentication forms with hCaptcha integration
"""
from django import forms
from hcaptcha_field import hCaptchaField


class RegistrationForm(forms.Form):
    """Registration form with hCaptcha verification"""

    role = forms.ChoiceField(
        choices=[
            ('', 'Sélectionnez votre type de compte'),
            ('patient', 'Patient'),
            ('doctor', 'Médecin'),
            ('hospital', 'Hôpital'),
            ('pharmacy', 'Pharmacie'),
            ('insurance_company', "Compagnie d'assurance"),
        ],
        required=True,
        widget=forms.Select(attrs={
            'class': 'form-input',
            'aria-label': 'Type de compte'
        })
    )

    last_name = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Nom de famille',
            'autocomplete': 'family-name',
            'aria-label': 'Nom de famille'
        })
    )

    first_name = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Prénom(s)',
            'autocomplete': 'given-name',
            'aria-label': 'Prénom'
        })
    )

    country_code = forms.ChoiceField(
        choices=[
            ('', 'Sélectionnez votre pays'),
            ('BJ', '🇧🇯 Bénin'),
            ('TG', '🇹🇬 Togo'),
            ('CI', '🇨🇮 Côte d\'Ivoire'),
            ('SN', '🇸🇳 Sénégal'),
            ('ML', '🇲🇱 Mali'),
            ('NE', '🇳🇪 Niger'),
            ('BF', '🇧🇫 Burkina Faso'),
            ('GH', '🇬🇭 Ghana'),
            ('NG', '🇳🇬 Nigeria'),
            ('CM', '🇨🇲 Cameroun'),
            ('FR', '🇫🇷 France'),
            ('US', '🇺🇸 États-Unis'),
            ('CA', '🇨🇦 Canada'),
        ],
        required=True,
        widget=forms.Select(attrs={
            'class': 'form-input',
            'id': 'country_code',
            'aria-label': 'Pays'
        })
    )

    phone_number = forms.CharField(
        max_length=15,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'id': 'phone_number',
            'placeholder': '97000000',
            'autocomplete': 'tel',
            'aria-label': 'Numéro de téléphone',
            'pattern': '[0-9]{8,10}',
            'title': 'Veuillez entrer un numéro valide (8-10 chiffres)'
        })
    )

    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-input',
            'placeholder': 'Votre couriel ou email',
            'autocomplete': 'email',
            'aria-label': 'Email'
        })
    )

    password = forms.CharField(
        min_length=8,
        required=True,
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Votre mot de passe',
            'autocomplete': 'new-password',
            'aria-label': 'Mot de passe'
        })
    )

    # hCaptcha field
    hcaptcha = hCaptchaField()


class LoginForm(forms.Form):
    """Login form with hCaptcha verification"""

    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-input',
            'placeholder': 'Votre couriel ou email',
            'autocomplete': 'email',
            'aria-label': 'Email'
        })
    )

    password = forms.CharField(
        required=True,
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Entrez votre mode de passe ici',
            'autocomplete': 'current-password',
            'aria-label': 'Mot de passe'
        })
    )

    # hCaptcha field
    hcaptcha = hCaptchaField()
