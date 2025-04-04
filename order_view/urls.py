from django.urls import path
from . import views



urlpatterns = [
    path('', views.order_list, name='orders'),
    # path('confirm<int:pending_id>/', views.confirm_order, name='confirm'),
    path('dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('sales-report/', views.sales_report, name='sales_report'),
    
    # Order management
    path('orders/', views.order_list, name='order_list'),
    path('orders/<int:order_id>/', views.order_detail, name='order_detail'),
    path('pending-orders/<int:pending_id>/', views.pending_order_detail, name='pending_order_detail'),
    
    # Order actions
    path('verify-order/<int:pending_id>/', views.verify_order, name='verify_order'),
    path('mark-complete/<int:order_id>/', views.mark_order_complete, name='mark_order_complete'),
    path('order/<int:order_id>/full-details/', views.order_full_details, name='order_full_details'),

]