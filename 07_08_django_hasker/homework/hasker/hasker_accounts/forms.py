from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm

from hasker_accounts.models import User


class SignupForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields + ('email', 'password1', 'password2', 'avatar',)


class SettingsForm(forms.ModelForm):
    class Meta(UserChangeForm.Meta):
        model = User
        fields = ('username', 'email', 'avatar',)

    username = forms.CharField(required=False, disabled=True)
