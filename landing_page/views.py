from django.shortcuts import render

# Create your views here.

def landing_page(request):
    return render(request, 'page.html')

def pricing_page(request):
    return render(request, 'pricing_page.html')