from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from .forms import CustomUserCreationForm, CustomAuthenticationForm
from .models import CustomUser
# users/views.py
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout as django_logout
from .forms import CustomUserCreationForm, CustomAuthenticationForm
from .models import CustomUser
from marketing_dashboard.action_logger import log_action  # Ajout de l'import
# Page d'accueil
def home(request):
    return render(request, 'users/home.html')

# Connexion des utilisateurs
def user_login(request):
    if request.method == 'POST':
        form = CustomAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            
            # Log de la connexion
            log_action(
                request=request,
                action_type='LOGIN',
                description=f"Connexion réussie de l'utilisateur {user.username}",
                target_type='user',
                target_id=user.id,
                user=user
            )
            
            # Redirection en fonction du type d'utilisateur
            if user.user_type == CustomUser.ADMIN:
                return redirect('admin_dashboard:home')
            elif user.user_type == CustomUser.EMPLOYEE:
                return redirect('marketing_dashboard:home')
    else:
        form = CustomAuthenticationForm()
    return render(request, 'users/login.html', {'form': form})

# Inscription des utilisateurs
def user_register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Connecter automatiquement l'utilisateur
            login(request, user)
            
            # Log de l'inscription
            log_action(
                request=request,
                action_type='REGISTER',
                description=f"Inscription réussie de l'utilisateur {user.username}",
                target_type='user',
                target_id=user.id,
                user=user
            )
            
            # Rediriger vers le tableau de bord approprié
            if user.user_type == CustomUser.ADMIN:
                return redirect('admin_dashboard:home')
            else:
                return redirect('marketing_dashboard:home')
    else:
        form = CustomUserCreationForm()
    return render(request, 'users/register.html', {'form': form})
#logout
from django.contrib.auth import logout as django_logout

def user_logout(request):
    # Enregistrer la déconnexion avant de déconnecter l'utilisateur
    if request.user.is_authenticated:
        log_action(
            request=request,
            action_type='LOGOUT',
            description=f"Déconnexion de l'utilisateur {request.user.username}",
            target_type='user',
            target_id=request.user.id,
            user=request.user
        )
    
    # Déconnecter l'utilisateur
    django_logout(request)
    return redirect('users:login')  # Utilisez le namespace 'users:login'
