from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    path('signup/', views.SignupView.as_view(), name='signup'),
    path('login/', auth_views.LoginView.as_view(template_name='hasker_accounts/login.html'), name='login'),
    path('settings/', views.SettingsView.as_view(), name='settings'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
]
