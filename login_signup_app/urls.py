from django.urls import path
from . import views

urlpatterns = [
    path('', views.login_signup_home, name='login_home'),
    path('profile/', views.profile, name='profile'),
]
