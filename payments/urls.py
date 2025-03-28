from django.urls import path
from . import views

urlpatterns = [
	path('', views.initiate_payment, name='initiate_payment'),
	path('verify-payment/<str:ref>/', views.verify_payment, name='verify_payment'),
]