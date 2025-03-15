from django.db import models
from django.core.validators import FileExtensionValidator


allowed_files = FileExtensionValidator(
    allowed_extensions=['pdf', 'jpg', 'jpeg', 'png']
            )
    
    
    
class PrintJob(models.Model): 
    quantity = models.IntegerField(null=True)
    price = models.DecimalField(max_digits=10, decimal_places=0,null=True,blank=True,default= 0)
    width = models.FloatField(null=True)
    height = models.FloatField(null=True)
    dimension_unit = models.CharField(max_length=10, choices=[('inches', 'Inches'), ('feet', 'Feet')], null=True,default='inches')
    design_file = models.ImageField(upload_to='print_jobs/',validators=[ allowed_files ], null=True)
    special_instructions = models.TextField(blank=True)
    total_price = models.DecimalField(max_digits=10, decimal_places=2,null=True) 
    created_at = models.DateTimeField(auto_now_add = True, null = True) 
    
    def __str__(self):
        return f"Order {self.id} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"

    
    
    
    
# class Categories(models.Model):
#     name = models.CharField(max_length=20, default=None, blank=True, null=True, )   
    
#     class Meta:
#         verbose_name_plural = 'Categories'
        
#     def __str__(self):
#             return self.name
    
    
# class Products(models.Model):
#     name = models.CharField(max_length=100 , null=True, blank=True)
#     product_picture = models.ImageField(
#         upload_to='products/',
#     )
#     category = models.ForeignKey(Categories, on_delete=models.CASCADE, null=True, blank=True, related_name= 'product_category')
    
#     class Meta:
#         verbose_name_plural= "Products"
    
    
#     def __str__(self):
#         return self.name
    
    