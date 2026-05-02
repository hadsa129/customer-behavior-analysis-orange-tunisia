from django.contrib import admin
from django.urls import path, include
from users import views as users_views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', users_views.home, name='home'),  # Page d'accueil racine

    path('admin/', admin.site.urls),
    path('accounts/', include('users.urls', namespace='users')),  # Ajoutez cette ligne
    path('admin_panel/', include('admin_dashboard.urls')),
    path('marketing_panel/', include('marketing_dashboard.urls', namespace='marketing_dashboard')),
    path('marketing_panel/signout/', users_views.user_logout, name='signout_compat'),
] + static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)