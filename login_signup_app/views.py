
# Create your views here.
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required

def login_signup_home(request):
    """
    A landing page for auth — offers links to:
      - email/password login & signup
      - Google OAuth
    """
    return render(request, 'login_signup_app/home.html')

@login_required
def profile(request):
    return render(request, 'login_signup_app/profile.html')
