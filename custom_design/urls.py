from django.urls import path
from . import views



urlpatterns = [
    # Design home page
    path('', views.design_home, name='custom-home'),
    path('products/<slug:product_slug>/', views.product_templates, name='product_templates'),
    
    # Create a new design
    path('new/', views.new_design, name='new_design'),
    
    # Design editor
    path('editor/', views.design_editor, name='editor'),
    # For the regular editor with query parameters


# For the admin editor with template ID in the path
path('design-editor/<int:template_id>/', views.design_editor, name='design_editor'),
    
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
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    path('product-types/', views.product_type_list, name='product_type_list'),
    path('product-types/add/', views.product_type_create, name='product_type_create'),
    path('product-types/<int:pk>/edit/', views.product_type_edit, name='product_type_edit'),
    path('product-types/<int:pk>/delete/', views.product_type_delete, name='product_type_delete'),
    
    # Design Template URLs
    path('design-templates/', views.design_template_list, name='design_template_list'),
    path('design-templates/add/', views.design_template_create, name='design_template_create'),
    path('design-templates/<int:pk>/edit/', views.design_template_edit, name='design_template_edit'),
    path('design-templates/<int:pk>/delete/', views.design_template_delete, name='design_template_delete'),
    
    # Design Editor URL (for the editor tab functionality)
    path('design-editor/<int:template_id>/', views.design_editor, name='design_editor'),
    path('design-editor/<int:template_id>/save/', views.save_template_canvas, name='save_template_canvas'),
    path('delete-design/<int:design_id>/', views.delete_design, name='delete_design'),
    
    
    # path('design-templates/', views.design_templates_list, name='design_templates_list'),
    
    
    
    
    
    
    # path('product-types/', views.product_type_list, name='product_type_list'),
    # path('product-types/add/', views.product_type_create, name='product_type_create'),
    # path('product-types/<int:pk>/edit/', views.product_type_edit, name='product_type_edit'),
    # path('product-types/<int:pk>/delete/', views.product_type_delete, name='product_type_delete'),
    
    # # Design Template URLs
    # path('design-templates/', views.design_template_list, name='design_template_list'),
    # path('design-templates/add/', views.design_template_create, name='design_template_create'),
    # path('design-templates/<int:pk>/edit/', views.design_template_edit, name='design_template_edit'),
    # path('design-templates/<int:pk>/delete/', views.design_template_delete, name='design_template_delete'),
    
    # # Design Editor URL (for the editor tab functionality)
    # path('design-editor/<int:template_id>/', views.design_editor, name='design_editor'),
    # path('design-editor/<int:template_id>/save/', views.save_template_canvas, name='save_template_canvas'),
    
    # # User Designs URLs
    # path('my-designs/', views.UserDesignListView.as_view(), name='user_designs'),
    # path('my-designs/<int:design_id>/delete/', views.delete_design, name='delete_design'),
    # path('my-designs/bulk-delete/', views.bulk_delete_designs, name='bulk_delete_designs'),
    # path('my-designs/bulk-archive/', views.bulk_archive_designs, name='bulk_archive_designs'),
    # path('my-designs/create/', views.create_design, name='new_design'),
    # path('my-designs/<int:design_id>/edit/', views.edit_design, name='edit_design'),
    # path('my-designs/<int:design_id>/', views.design_detail, name='design_detail'),

]