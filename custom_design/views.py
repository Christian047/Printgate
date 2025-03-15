from django.shortcuts import render

# Create your views here.


def Customize(request):
    return render(request, 'custom_design.html')