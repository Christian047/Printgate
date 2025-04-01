from django.urls import path
from . import views

# This is how it might be defined in your urls.py
# app_name = 'custom_design'  # This defines the namespace

urlpatterns = [
    # Design home page
    path('', views.design_home, name='custom-home'),
    path('products/<slug:product_slug>/', views.product_templates, name='product_templates'),
    
    # Create a new design
    path('new/', views.new_design, name='new_design'),
    
    # Design editor
    path('editor/', views.design_editor, name='editor'),
    
    # API endpoints for saving and loading designs
    path('api/save-design/', views.save_design, name='save_design'),
    path('api/load-design/<int:design_id>/', views.load_design, name='load_design'),
    path('api/get-assets/', views.get_assets, name='get_assets'),
    
    # User's saved designs
    path('my-designs/', views.my_designs, name='my_designs'),
    path('my-designs/<int:design_id>/', views.design_detail, name='design_detail'),
    path('my-designs/<int:design_id>/delete/', views.delete_design, name='delete_design'),
    
    # --------------------------------------------------------------------------------------------------
    
    path('purchase-template/<int:template_id>/', views.purchase_template, name='purchase_template'),
    path('customverify-template-payment/template_<str:payment_ref>/', views.verify_template_payment, name='verify_template_payment'),
    path('template-payment/<int:template_id>/', views.template_payment, name='template_payment'),

]