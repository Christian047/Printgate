from django.contrib import admin
from .models import ProductType, ProductVariant, DesignTemplate, DesignAsset, UserDesign,DesignCategory,Font,ColorPalette

# Register your models here.




@admin.register(ProductType)
class ProductTypeAdmin(admin.ModelAdmin):
    list_display = ("description", "slug", "name")


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ("print_areas", "active", "is_default", "price_adjustment", "color_hex", "back_image", "base_image", "description", "name", "product_type")


@admin.register(DesignTemplate)
class DesignTemplateAdmin(admin.ModelAdmin):
    list_display = ( "active", "updated_at", "created_at", "is_premium", "is_featured", "canvas_json", "preview_image", "description", "category", "product_type", "slug", "name")


@admin.register(DesignAsset)
class DesignAssetAdmin(admin.ModelAdmin):
    list_display = ("active", "created_at", "tags", "is_premium", "svg_data", "image", "category", "name", "ASSET_CATEGORIES")


@admin.register(UserDesign)
class UserDesignAdmin(admin.ModelAdmin):
    list_display = ( "design_side", "is_draft", "updated_at", "created_at", "preview_image", "canvas_json", "template", "product_variant", "product_type", "name", "user")


@admin.register(DesignCategory)
class DesignCategoryAdmin(admin.ModelAdmin):
    list_display = ("description", "slug", "name")


@admin.register(Font)
class FontAdmin(admin.ModelAdmin):
    list_display = ( "active", "is_premium", "css_url", "font_file", "display_name", "name")


@admin.register(ColorPalette)
class ColorPaletteAdmin(admin.ModelAdmin):
    list_display = ("is_premium", "colors", "name")
