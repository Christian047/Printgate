from django.db import models
from django.contrib.auth.models import User
from django.core.validators import FileExtensionValidator

# Create your models here.

class Customer(models.Model):
	user = models.OneToOneField(User, null=True, blank=True, on_delete=models.CASCADE)
	name = models.CharField(max_length=200, null=True)
	email = models.CharField(max_length=200)

	def __str__(self):
		return self.name if self.name else "unknown"


class Categories(models.Model):
    name = models.CharField(max_length=20, default=None, blank=True, null=True, )   
    
    class Meta:
        verbose_name_plural = 'Categories'
        
    def __str__(self):
            return self.name



allowed_files = FileExtensionValidator(
    allowed_extensions=['pdf', 'jpg', 'jpeg', 'png']
            )

# --------------------------------------------------------------------------------------------------------

class Product(models.Model):
    title = models.CharField(max_length=200)
    base_price = models.IntegerField(null=True, blank=True)
    digital = models.BooleanField(default=False,null=True, blank=True)
    image =  models.ImageField(
        upload_to='product/', default='default.jpg', null=True, blank=True
        
    )
    category = models.ForeignKey(Categories, on_delete=models.SET_NULL, null=True, blank=True, related_name= 'product_category')
    product_type = models.ForeignKey('custom_design.ProductType', on_delete=models.SET_NULL, null=True, blank=True, related_name='store_products')

    def __str__(self):
        return self.title

    @property
    def imageURL(self):
        try:
            url = self.image.url
        except:
            url = ''
        return url


# --------------------------------------------------------------------------------------------------------



class ProductVariant(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    name = models.CharField(max_length=100)
    price_adjustment = models.FloatField(default=0.0, help_text="Amount to add/subtract from base price")
    image =  models.ImageField(
        upload_to='product_variant/', default='default.jpg', null=True, blank=True
        
    )
    
    def __str__(self):
        return f"{self.product.title} - {self.name}"

# --------------------------------------------------------------------------------------------------------


# Product Specifications - defines what fields are needed for each product type
class ProductSpecField(models.Model):
    FIELD_TYPES = [
        ('text', 'Text Input'),
        ('number', 'Number Input'),
        ('select', 'Select Dropdown'),
        ('file', 'File Upload'),
        ('color', 'Color Picker'),
        ('textarea', 'Text Area'),
    ]
    
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='spec_fields')
    name = models.CharField(max_length=100)
    field_type = models.CharField(max_length=20, choices=FIELD_TYPES)
    required = models.BooleanField(default=True)
    help_text = models.CharField(max_length=255, blank=True, null=True)
    order = models.PositiveIntegerField(default=0)
    
    # For select fields, store options as comma-separated values
    options = models.TextField(blank=True, null=True, help_text="For select fields, enter options separated by commas")
    
    def __str__(self):
        return f"{self.product.title} - {self.name}"
    
    class Meta:
        ordering = ['order']




# ---------------------------------------------------------------

class PendingOrder(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, null=True) 
    
    
    
    user_design = models.ForeignKey('custom_design.UserDesign', on_delete=models.SET_NULL, null=True, blank=True, related_name='custom_design')
    
    
    
    variant = models.ForeignKey(ProductVariant, on_delete=models.SET_NULL, null=True, blank=True) 
    width = models.FloatField(null=True,blank=True)
    height = models.FloatField(null=True,blank=True)
    
    dimension_unit = models.CharField(max_length=10, choices=[('inches', 'Inches'), ('feet', 'Feet')], default='inches')
    design_file = models.ImageField(upload_to='print_jobs/', validators=[allowed_files], null=True, blank=True)
    special_instructions = models.TextField(blank=True)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, null=True,blank=True)
    date_ordered = models.DateTimeField(auto_now_add=True)
    complete = models.BooleanField(default=False)
    transaction_id = models.CharField(max_length=100, null=True, blank=True) 
    designer_instructions = models.TextField(blank=True, null=True)
    
    
    order_type = models.CharField(
        max_length=20, 
        choices=[('print', 'Print Only'), ('designer', 'Hire Designer'), ('design', 'Created Design')],
        default='print'
    )
    designer_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0) 
    
    def __str__(self):
        return f"Pending Order {self.id} - {self.customer.name if self.customer else 'Guest'}"
    
    # Method to convert pending order to confirmed order
    def convert_to_order(self):
        order = Order.objects.create(
            customer=self.customer,
            product=self.product,
            width=self.width,
            height=self.height,
            dimension_unit=self.dimension_unit,
            special_instructions=self.special_instructions,
            total_price=self.total_price,
        )
        
        # Copy the design file to the new order
        if self.design_file:
            from django.core.files.base import ContentFile
            order.design_file.save(
                self.design_file.name,
                ContentFile(self.design_file.read()),
                save=True
            )
        
        return order
    
        class Meta:
              ordering = ['-date_ordered']


class PendingOrderSpecification(models.Model):
    pending_order = models.ForeignKey(PendingOrder, on_delete=models.CASCADE, related_name='specifications')
    spec_field = models.ForeignKey(ProductSpecField, on_delete=models.CASCADE, null=True, blank=True)  # Explicit link
    field_name = models.CharField(max_length=100)
    field_value = models.TextField(blank=True, null=True)
    field_file = models.FileField(upload_to='pending_specs/', validators=[allowed_files], null=True, blank=True)
    
    def __str__(self):
        return f"{self.pending_order.id} - {self.field_name}"




class ReferenceImage(models.Model):
    pending_order = models.ForeignKey('PendingOrder', on_delete=models.CASCADE, related_name='reference_images')
    image = models.FileField(upload_to='reference_images/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Reference image for order {self.pending_order.id}"




class Order(models.Model):
    pending_order = models.OneToOneField(PendingOrder,  on_delete=models.SET_NULL, null=True, blank=True,related_name='confirmed_order')
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, null=True) 
    width = models.FloatField(null=True)
    height = models.FloatField(null=True)
    dimension_unit = models.CharField(max_length=10, choices=[('inches', 'Inches'), ('feet', 'Feet')], default='inches')
    design_file = models.ImageField(upload_to='print_jobs/', validators=[allowed_files], null=True)
    special_instructions = models.TextField(blank=True)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    date_ordered = models.DateTimeField(auto_now_add=True)
    complete = models.BooleanField(default=False)
    transaction_id = models.CharField(max_length=100, null=True, blank=True)  

    def __str__(self):
        return str(self.id)  # ✅ Fixed indentation

    @property
    def shipping(self):
        shipping = False
        orderitems = self.orderitem_set.all()
        for i in orderitems:
            if i.product.digital == False:
                shipping = True
        return shipping

    @property
    def get_cart_total(self):
        orderitems = self.orderitem_set.all()
        total = sum([item.get_total for item in orderitems])
        return total 

    @property
    def get_cart_items(self):
        orderitems = self.orderitem_set.all()
        total = sum([item.quantity for item in orderitems])
        return total
    
    class Meta:
        ordering = ['-date_ordered']


# ----------------------------------------------------------------------------------------------------------------


class OrderItem(models.Model):
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    order = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True)
    quantity = models.IntegerField(default=0, null=True, blank=True)
    variant = models.ForeignKey(ProductVariant, on_delete=models.SET_NULL, null=True, blank=True)
    date_added = models.DateTimeField(auto_now_add=True)
    designer_service = models.BooleanField(default= False)


    @property
    def get_total(self):
        base_total = self.product.base_price * self.quantity
        variant_adjustment = 0
        if self.variant:
            variant_adjustment = self.variant.price_adjustment * self.quantity
        
        # Add design fee if this is a designer service
        designer_fee = 5000 if self.designer_service else 0
        
        return base_total + variant_adjustment + designer_fee
        
    
    @property
    def get_unit_price(self):
        base_price = self.product.base_price
        variant_adjustment = 0
        if self.variant:
            variant_adjustment = self.variant.price_adjustment
        return base_price + variant_adjustment
    


class OrderSpecification(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='specifications')
    field_name = models.CharField(max_length=100)
    field_value = models.TextField(blank=True, null=True)
    field_file = models.FileField(upload_to='order_specs/', validators=[allowed_files], null=True, blank=True)
    
    def __str__(self):
        return f"{self.order.id} - {self.field_name}"
    

class ShippingAddress(models.Model):
	customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True)
	order = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True)
	address = models.CharField(max_length=200, null=False)
	city = models.CharField(max_length=200, null=False)
	state = models.CharField(max_length=200, null=False)
	zipcode = models.CharField(max_length=200, null=False)
	date_added = models.DateTimeField(auto_now_add=True)

	def __str__(self):
		return self.address