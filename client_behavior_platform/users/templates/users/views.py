from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from .forms import CustomUserCreationForm, CustomAuthenticationForm
from .models import CustomUser

# Page d'accueil
def home(request):
    return render(request, 'accounts/home.html')

# Connexion des utilisateurs
def user_login(request):
    if request.method == 'POST':
        form = CustomAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            # Redirection en fonction du type d'utilisateur
            if user.user_type == CustomUser.ADMIN:
                return redirect('admin_dashboard_home')
            elif user.user_type == CustomUser.EMPLOYEE:
                return redirect('employee_dashboard_home')
    else:
        form = CustomAuthenticationForm()
    return render(request, 'accounts/login.html', {'form': form})

# Inscription des utilisateurs
def user_register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('login')
    else:
        form = CustomUserCreationForm()
    return render(request, 'accounts/register.html', {'form': form})

# Déconnexion des utilisateurs
from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import CustomUser

class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    user_type = forms.ChoiceField(choices=CustomUser.USER_TYPE_CHOICES, required=True, label='Account Type')
    
    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'password1', 'password2', 'user_type']

class CustomAuthenticationForm(AuthenticationForm):
    username = forms.CharField(label='Username', max_length=100)
    password = forms.CharField(label='Password', widget=forms.PasswordInput)

