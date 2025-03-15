from django.urls import path
from . import views



urlpatterns = [
    path('', views.order_list, name='orders'),
    path('confirm<int:pending_id>/', views.confirm_order, name='confirm'),

]