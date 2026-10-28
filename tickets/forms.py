from django import forms
from django.contrib.auth.forms import UserCreationForm


class EntrarFilaForm(forms.Form):
    chave_vale = forms.CharField(
        label='Chave primária do vale-alimentação',
        max_length=50,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Digite a chave primária do vale',
            'autocomplete': 'off'
        })
    )


class ValidarQRForm(forms.Form):
    token = forms.UUIDField(
        label='Token do QR Code',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Cole ou digite o token do QR Code'
        })
    )


class CriarUsuarioForm(UserCreationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'
