from django.contrib import admin
from .models import *

# Register your models here.

@admin.register(PrintJob)
class PrintJobAdmin(admin.ModelAdmin):  
    list_display = ['quantity', 'width', 'height', 'dimension_unit', 'design_file', 'special_instructions', 'total_price', 'created_at']

# @admin.register(Products)
# class PrintJobAdmin(admin.ModelAdmin):  
#     list_display = ['name', 'product_picture', 'category']  
    
# @admin.register(Categories)
# class CategoriesAdmin(admin.ModelAdmin):  
#     list_display = ['name']  
    
    

