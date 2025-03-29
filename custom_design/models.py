from django.db import models
from django.conf import settings
from django.utils.text import slugify
from django.core.validators import MinValueValidator
import uuid
import os

def product_template_path(instance, filename):
    """Generate file path for product base images"""
    ext = filename.split('.')[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    return os.path.join('product_bases', str(instance.product_type.id), filename)

def design_template_path(instance, filename):
    """Generate file path for design templates"""
    ext = filename.split('.')[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    return os.path.join('design_templates', str(instance.product_type.id), filename)

def design_asset_path(instance, filename):
    """Generate file path for design assets"""
    ext = filename.split('.')[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    return os.path.join('design_assets', instance.category.lower(), filename)

def user_design_path(instance, filename):
    """Generate file path for saved user designs"""
    ext = filename.split('.')[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    return os.path.join('user_designs', str(instance.user.id), filename)


class ProductType(models.Model):
    """Category of product that can be customized (t-shirt, business card, poster, etc.)"""
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True, help_text="Font Awesome icon class")
    active = models.BooleanField(default=True)
    order = models.IntegerField(default=0, help_text="Display order")
    
    # Canvas specifications
    default_width = models.IntegerField(help_text="Default canvas width in pixels", default=1800)
    default_height = models.IntegerField(help_text="Default canvas height in pixels", default=1600)
    
    # Printable area constraints
    has_print_area = models.BooleanField(default=True, help_text="Whether this product has defined print areas")
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    
    class Meta:
        verbose_name_plural = "Product Types"
        ordering = ['order', 'name']
    
    def __str__(self):
        return self.name


class ProductVariant(models.Model):
    """Specific variant of a product type (color, material, etc.)"""
    product_type = models.ForeignKey(ProductType, on_delete=models.CASCADE, related_name='variants')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    base_image = models.ImageField(upload_to=product_template_path, help_text="Base product image for customization")
    back_image = models.ImageField(upload_to=product_template_path, blank=True, null=True, 
                                 help_text="Back image for double-sided products")
    color_hex = models.CharField(max_length=7, blank=True, help_text="Hex color code for variant")
    price_adjustment = models.DecimalField(max_digits=10, decimal_places=2, default=0.00,
                                        help_text="Price adjustment relative to base price")
    is_default = models.BooleanField(default=False)
    active = models.BooleanField(default=True)
    
    # Print area definitions (JSON containing print area coordinates for different sides)
    # e.g. {'front': {'x': 100, 'y': 100, 'width': 300, 'height': 400}, 'back': {...}}
    print_areas = models.JSONField(blank=True, null=True)
    
    class Meta:
        ordering = ['product_type', 'name']
        unique_together = ['product_type', 'name']
    
    def __str__(self):
        return f"{self.product_type.name} - {self.name}"


class DesignCategory(models.Model):
    """Categories for design templates (business, sports, holidays, etc.)"""
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True, help_text="Font Awesome icon class")
    active = models.BooleanField(default=True)
    order = models.IntegerField(default=0, help_text="Display order")
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    
    class Meta:
        verbose_name_plural = "Design Categories"
        ordering = ['order', 'name']
    
    def __str__(self):
        return self.name

def default_canvas_json():
    return {
        "version": "5.3.1", 
        "objects": [], 
        "background": "#ffffff"
    }



class DesignTemplate(models.Model):
    """Pre-designed templates that users can customize"""
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=250, unique=True, blank=True)
    product_type = models.ForeignKey(ProductType, on_delete=models.CASCADE, related_name='templates')
    category = models.ForeignKey(DesignCategory, on_delete=models.CASCADE, related_name='templates')
    description = models.TextField(blank=True)
    preview_image = models.ImageField(upload_to=design_template_path)
    canvas_json = models.JSONField(help_text="Fabric.js canvas data in JSON format",  default=default_canvas_json)
    is_featured = models.BooleanField(default=False)
    is_premium = models.BooleanField(default=False, help_text="Whether this template requires premium access", )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    active = models.BooleanField(default=True)
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    
    class Meta:
        ordering = ['-is_featured', '-created_at']
    
    def __str__(self):
        return f"{self.name} ({self.product_type.name})"


class DesignAsset(models.Model):
    """Assets that can be added to designs (clipart, shapes, frames, etc.)"""
    ASSET_CATEGORIES = [
        ('clipart', 'Clipart'),
        ('shape', 'Shape'),
        ('frame', 'Frame'),
        ('background', 'Background'),
        ('element', 'Design Element'),
        ('logo', 'Logo'),
    ]
    
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=20, choices=ASSET_CATEGORIES)
    image = models.ImageField(upload_to=design_asset_path)
    svg_data = models.TextField(blank=True, help_text="SVG data for vector assets")
    is_premium = models.BooleanField(default=False)
    tags = models.CharField(max_length=255, blank=True, help_text="Comma-separated tags")
    created_at = models.DateTimeField(auto_now_add=True)
    active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['category', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.get_category_display()})"


class Font(models.Model):
    """Custom fonts available for design customization"""
    name = models.CharField(max_length=100)
    display_name = models.CharField(max_length=100, blank=True)
    font_file = models.FileField(upload_to='design_fonts/', help_text="Upload .ttf, .otf, or .woff file")
    css_url = models.URLField(blank=True, help_text="URL to font CSS if using external font service")
    is_premium = models.BooleanField(default=False)
    active = models.BooleanField(default=True)
    
    def save(self, *args, **kwargs):
        if not self.display_name:
            self.display_name = self.name
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.display_name


class ColorPalette(models.Model):
    """Predefined color palettes for templates"""
    name = models.CharField(max_length=100)
    colors = models.JSONField(help_text="JSON array of hex color codes")
    is_premium = models.BooleanField(default=False)
    
    def __str__(self):
        return self.name


class UserDesign(models.Model):
    """User's customized designs saved to their account"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='designs')
    name = models.CharField(max_length=200)
    product_type = models.ForeignKey(ProductType, on_delete=models.CASCADE)
    product_variant = models.ForeignKey(ProductVariant, on_delete=models.SET_NULL, null=True, blank=True)
    template = models.ForeignKey(DesignTemplate, on_delete=models.SET_NULL, null=True, blank=True)
    canvas_json = models.JSONField(help_text="Fabric.js canvas data in JSON format")
    preview_image = models.ImageField(upload_to=user_design_path, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_draft = models.BooleanField(default=True)
    
    # Design settings
    design_side = models.CharField(max_length=20, default='front', 
                               help_text="Which side of the product this design is for")
    
    class Meta:
        ordering = ['-updated_at']
    
    def __str__(self):
        return f"{self.name} by {self.user.username}"