from django.urls import path
from . import views



urlpatterns = [
    path('', views.Customize, name='customize'),
]