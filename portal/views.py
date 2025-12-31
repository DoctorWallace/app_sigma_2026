from django.shortcuts import render
from django.http import HttpResponse

def home(request):
    return render(request, "portal/home.html")

def faq(request):
    return render(request, "portal/faq.html")

