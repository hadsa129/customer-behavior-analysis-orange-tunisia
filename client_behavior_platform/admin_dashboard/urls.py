from django.urls import path
from . import views

app_name = 'admin_dashboard'

urlpatterns = [
    path('', views.dashboard_home, name='home'),
    path('upload/', views.upload_file, name='upload_file'),
    path('launch-job/', views.launch_job, name='launch_job'),
    path('history/', views.job_history, name='job_history'),
    path('logs/<str:job_name>/', views.job_log_detail, name='job_log_detail'),
    path('employee-management/', views.employee_management, name='employee_management'),
    path('signout/', views.signout_view, name='signout'),
    path('profile/', views.profile_view, name='profile'),
]
