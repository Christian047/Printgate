# urls.py
from django.urls import path
from . import views



urlpatterns = [
    path('', views.Home, name='home'),
    path('product/<int:product_id>/', views.product_detail, name='product_detail'),
    path('cart', views.cart, name='cart'),
    path('options/<int:pk>/', views.design_options, name='options'),
    path('list', views.list_Prints, name='list'),
    path('order-confirmation/<int:order_id>/', views.order_confirmation, name='order_confirmation'),
    path('create_order/<int:pk>/', views.create_print_order, name='create_order'),
    path('hire-designer/<int:pk>/', views.hire_designer, name='hire_designer'),
    path('design/', views.design_options_page, name='design'),
    path('convert/', views.covert_size, name='convert'),
    path('autocomplete/', views.autocomplete, name='autocomplete'),
    
    
    
    
    
    
    path('products/<int:pk>/design/', views.create_design_order, name='create_design_order'),
    path('my-designs/', views.user_designs, name='user_designs'),  # View for listing user's saved designs
]