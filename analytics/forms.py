from django import forms
from .models import SurveyResponse
import re


class SurveyResponseForm(forms.ModelForm):  # Form for collecting user survey responses with validation and spam protection
    honeypot = forms.CharField(
        required=False,
        widget=forms.HiddenInput(),
        label='Leave this field empty'
    )

    class Meta:  # Meta class implementation
        model = SurveyResponse
        fields = [
            'email',
            'country',
            'city',
            'profession',
            'sex',
            'suggested_price',
            'currency',
            'feature_suggestion',
            'other_suggestion',
        ]
        error_messages = {
            'email': {
                'unique': 'Cet email a déjà été utilisé pour participer au sondage. Chaque email ne peut participer qu\'une seule fois.',
            }
        }
        widgets = {
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'votre@email.com',
                'required': True,
                'maxlength': '254'
            }),
            'country': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Pays',
                'required': True,
                'maxlength': '100'
            }),
            'city': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ville',
                'required': True,
                'maxlength': '100'
            }),
            'profession': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Profession',
                'required': True,
                'maxlength': '100'
            }),
            'sex': forms.Select(attrs={
                'class': 'form-control',
                'required': True
            }),
            'suggested_price': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Prix suggéré',
                'step': '0.01',
                'min': '0',
                'max': '99999999.99'
            }),
            'currency': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'EUR, XOF, USD, etc.',
                'maxlength': '10'
            }),
            'feature_suggestion': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Suggérez de nouvelles fonctionnalités...',
                'rows': 4,
                'maxlength': '5000'
            }),
            'other_suggestion': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Autres suggestions...',
                'rows': 4,
                'maxlength': '5000'
            }),
        }
        labels = {
            'email': 'Email',
            'country': 'Pays',
            'city': 'Ville',
            'profession': 'Profession',
            'sex': 'Sexe',
            'suggested_price': 'Prix de consultation suggéré',
            'currency': 'Devise',
            'feature_suggestion': 'Suggestions de fonctionnalités',
            'other_suggestion': 'Autres suggestions',
        }

    def clean_honeypot(self):  # Validate honeypot field to detect and reject bot submissions
        honeypot = self.cleaned_data.get('honeypot')
        if honeypot:
            raise forms.ValidationError('Bot detected. Submission rejected.')
        return honeypot

    def clean_email(self):  # Validate email format and reject disposable email addresses
        email = self.cleaned_data.get('email')
        if email:
            email = email.lower().strip()
            if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
                raise forms.ValidationError('Veuillez entrer une adresse email valide.')

            disposable_domains = ['tempmail.com', '10minutemail.com', 'guerrillamail.com', 'mailinator.com', 'yopmail.com', 'throwaway.email']
            domain = email.split('@')[1]
            if domain in disposable_domains:
                raise forms.ValidationError('Les adresses email temporaires ne sont pas autorisées.')

        return email

    def clean_country(self):  # Validate country name format and length
        country = self.cleaned_data.get('country')
        if country:
            country = country.strip()
            if len(country) < 2:
                raise forms.ValidationError('Le nom du pays est trop court.')
            if not re.match(r'^[a-zA-ZÀ-ÿ\s\-]+$', country):
                raise forms.ValidationError('Le nom du pays contient des caractères invalides.')
        return country

    def clean_city(self):  # Validate city name format and length
        city = self.cleaned_data.get('city')
        if city:
            city = city.strip()
            if len(city) < 2:
                raise forms.ValidationError('Le nom de la ville est trop court.')
            if not re.match(r'^[a-zA-ZÀ-ÿ\s\-\.]+$', city):
                raise forms.ValidationError('Le nom de la ville contient des caractères invalides.')
        return city

    def clean_profession(self):  # Validate profession name format and length
        profession = self.cleaned_data.get('profession')
        if profession:
            profession = profession.strip()
            if len(profession) < 2:
                raise forms.ValidationError('Le nom de la profession est trop court.')
            if not re.match(r'^[a-zA-ZÀ-ÿ\s\-]+$', profession):
                raise forms.ValidationError('Le nom de la profession contient des caractères invalides.')
        return profession

    def clean_suggested_price(self):  # Validate price is non-negative and within reasonable range
        price = self.cleaned_data.get('suggested_price')
        if price is not None:
            if price < 0:
                raise forms.ValidationError('Le prix ne peut pas être négatif.')
            if price > 999999:
                raise forms.ValidationError('Le prix est trop élevé.')
        return price

    def clean_currency(self):  # Validate currency code is valid ISO 3-letter format
        currency = self.cleaned_data.get('currency')
        if currency:
            currency = currency.upper().strip()
            if not re.match(r'^[A-Z]{3}$', currency):
                raise forms.ValidationError('Le code de devise doit être un code ISO de 3 lettres (ex: USD, EUR, XOF).')
        return currency

    def clean_feature_suggestion(self):  # Validate feature suggestion length and check for suspicious content
        suggestion = self.cleaned_data.get('feature_suggestion')
        if suggestion:
            suggestion = suggestion.strip()
            if len(suggestion) > 5000:
                raise forms.ValidationError('La suggestion est trop longue (max 5000 caractères).')

            suspicious_patterns = ['<script', 'javascript:', 'onerror=', 'onclick=', '<iframe']
            for pattern in suspicious_patterns:
                if pattern.lower() in suggestion.lower():
                    raise forms.ValidationError('Contenu suspect détecté.')
        return suggestion

    def clean_other_suggestion(self):  # Validate other suggestion length and check for suspicious content
        suggestion = self.cleaned_data.get('other_suggestion')
        if suggestion:
            suggestion = suggestion.strip()
            if len(suggestion) > 5000:
                raise forms.ValidationError('La suggestion est trop longue (max 5000 caractères).')

            suspicious_patterns = ['<script', 'javascript:', 'onerror=', 'onclick=', '<iframe']
            for pattern in suspicious_patterns:
                if pattern.lower() in suggestion.lower():
                    raise forms.ValidationError('Contenu suspect détecté.')
        return suggestion
