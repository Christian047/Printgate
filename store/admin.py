from django.contrib import admin
from .models import *
from .models import OrderSpecification,PendingOrderSpecification,Categories,ReferenceImage,OrderItem,Customer

from django.utils.safestring import mark_safe



@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):  
    list_display = ('title', 'base_price', 'bulk_quantity', 'digital', 'category_image', 'get_categories')
    filter_horizontal = ('category',)
    
    # Optional: Add fieldsets to organize the form better
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'base_price', 'bulk_quantity', 'digital', 'category', 'product_type')
        }),
        ('Images', {
            'fields': ('image', 'image_2', 'image_3', 'image_4'),
            'description': 'Upload main image and up to 3 additional images for the product carousel'
        }),
    )
    
    def category_image(self, obj):
        if obj.image:
            return mark_safe(f'<img src="{obj.image.url}" width="50" height="50" />')
        return "No Image"
    
    def get_categories(self, obj):
        return ", ".join([cat.name for cat in obj.category.all()])
    
    # Set a display name for the column
    get_categories.short_description = 'Categories'

    
@admin.register(ProductVariant)
class ProductAdmin(admin.ModelAdmin):  
    list_display = ('product', 'name', 'price_adjustment','image' )

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):  
    list_display = ('customer', 'product', 'pending_order',  'special_instructions', 'total_price', 'date_ordered', 'complete', 'transaction_id', )
    
    
@admin.register(PendingOrder)
class OrderAdmin(admin.ModelAdmin):  
    list_display = ('customer', 'product', 'user_design', 'dimension_unit', 'special_instructions', 'total_price', 'date_ordered','variant', 'category_image','designer_instructions','order_type' ,'width', 'height',)

    def category_image(self, obj):
        if obj.design_file:  # Ensure there's an image
            return mark_safe(f'<img src="{obj.design_file.url}" width="50" height="50" />')
        return "No Image"
        
    
@admin.register(ProductSpecField)
class OrderAdmin(admin.ModelAdmin):  
    list_display = ('product', 'name', 'field_type', 'required', 'help_text', 'order', 'options', )


@admin.register(OrderSpecification)
class OrderSpecificationAdmin(admin.ModelAdmin):
    list_display = ("field_file", "field_value", "field_name", "order")


@admin.register(PendingOrderSpecification)
class PendingOrderSpecificationAdmin(admin.ModelAdmin):
    list_display = ("pending_order","field_name","field_value", "field_file",  "spec_field", )


@admin.register(Categories)
class CategoriesAdmin(admin.ModelAdmin):
    list_display = ("name",)


@admin.register(ReferenceImage)
class ReferenceImageAdmin(admin.ModelAdmin):
    list_display = ("uploaded_at", "image", "pending_order")


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ("date_added", 'designer_service' ,"variant", "quantity", "order", "product")


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("email", "name", "user")
