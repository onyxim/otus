from django.contrib.auth import login
from django.contrib.auth.views import LogoutView as DjangoLogoutView
from django.views.generic import CreateView, UpdateView

from hasker_accounts.forms import SignupForm, SettingsForm
from hasker_accounts.models import User
from hasker_qa.views import common_context


class SignupView(CreateView):
    template_name = 'bootstrap_form.html'
    form_class = SignupForm
    success_url = '/'

    def form_valid(self, form):
        result = super().form_valid(form)
        login(request=self.request, user=self.object)
        return result

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(object_list=None, **kwargs)
        common_context(context, 'signup')
        return context


class SettingsView(UpdateView):
    template_name = 'bootstrap_form.html'
    form_class = SettingsForm
    success_url = '/'
    model = User

    def get_object(self, queryset=None):
        return self.request.user

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(object_list=None, **kwargs)
        common_context(context, 'settings')
        return context


class LogoutView(DjangoLogoutView):
    next_page = 'index'
