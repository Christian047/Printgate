from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.http import require_POST
from django.urls import reverse
from django.utils.html import escape
import json
import base64
from PIL import Image
import io
import logging

from .models import (
    ProductType, ProductVariant, DesignCategory, DesignTemplate,
    DesignAsset, Font, ColorPalette, UserDesign
)

logger = logging.getLogger(__name__)

def design_home(request):
    """Landing page for the design customization system"""
    product_types = ProductType.objects.filter(active=True).order_by('order')
    featured_templates = DesignTemplate.objects.filter(is_featured=True, active=True)[:8]
    design_categories = DesignCategory.objects.filter(active=True)
    
    context = {
        'product_types': product_types,
        'featured_templates': featured_templates,
        'design_categories': design_categories,
    }
    return render(request, 'custom_design/home.html', context)


def product_templates(request, product_slug):
    """Display available templates for a specific product type"""
    product_type = get_object_or_404(ProductType, slug=product_slug, active=True)
    templates = DesignTemplate.objects.filter(product_type=product_type, active=True)
    categories = DesignCategory.objects.filter(templates__product_type=product_type).distinct()
    
    selected_category = request.GET.get('category')
    if selected_category:
        templates = templates.filter(category__slug=selected_category)
    
    context = {
        'product_type': product_type,
        'templates': templates,
        'categories': categories,
        'selected_category': selected_category,
    }
    return render(request, 'custom_design/product_templates.html', context)


def new_design(request):
    """Start a new design - select product type and optional template"""
    product_types = ProductType.objects.filter(active=True)
    
    if request.method == 'POST':
        product_type_id = request.POST.get('product_type')
        template_id = request.POST.get('template')
        variant_id = request.POST.get('variant')
        
        if not product_type_id:
            return HttpResponseBadRequest("Product type is required")
        
        # Build the URL for the editor
        editor_url = reverse('designs:editor')
        params = f'?product_type={product_type_id}'
        
        if template_id:
            params += f'&template={template_id}'
        
        if variant_id:
            params += f'&variant={variant_id}'
        
        return redirect(f"{editor_url}{params}")
    
    # If GET request, show product type selection page
    product_templates = {}
    for product_type in product_types:
        product_templates[product_type.id] = DesignTemplate.objects.filter(
            product_type=product_type,
            is_featured=True,
            active=True
        )[:4]
    
    context = {
        'product_types': product_types,
        'product_templates': product_templates,
    }
    return render(request, 'custom_design/new_design.html', context)


def design_editor(request):
    """Main design editor using Fabric.js"""
    product_type_id = request.GET.get('product_type')
    template_id = request.GET.get('template')
    variant_id = request.GET.get('variant')
    design_id = request.GET.get('design_id')  # For editing existing designs
    
    # Validate required parameters
    if not product_type_id and not design_id:
        return HttpResponseBadRequest("Product type or design ID is required")
    
    # Initialize with defaults
    product_type = None
    template = None
    variant = None
    user_design = None
    initial_json = None
    
    if design_id and request.user.is_authenticated:
        # Load existing design
        user_design = get_object_or_404(
            UserDesign, id=design_id, user=request.user
        )
        product_type = user_design.product_type
        variant = user_design.product_variant
        template = user_design.template
        initial_json = user_design.canvas_json
    else:
        # New design
        product_type = get_object_or_404(ProductType, id=product_type_id, active=True)
        
        if template_id:
            template = get_object_or_404(
                DesignTemplate, id=template_id, product_type=product_type, active=True
            )
            initial_json = template.canvas_json
        
        if variant_id:
            variant = get_object_or_404(
                ProductVariant, id=variant_id, product_type=product_type, active=True
            )
        else:
            # Get default variant if available
            try:
                variant = ProductVariant.objects.filter(
                    product_type=product_type, is_default=True, active=True
                ).first()
            except ProductVariant.DoesNotExist:
                variant = None
    
    # Get design assets
    clipart = DesignAsset.objects.filter(category='clipart', active=True)
    shapes = DesignAsset.objects.filter(category='shape', active=True)
    backgrounds = DesignAsset.objects.filter(category='background', active=True)
    fonts = Font.objects.filter(active=True)
    color_palettes = ColorPalette.objects.all()
    
    # If no variant is selected, get all available variants
    all_variants = []
    if product_type:
        all_variants = ProductVariant.objects.filter(product_type=product_type, active=True)
    
    context = {
        'product_type': product_type,
        'variant': variant,
        'all_variants': all_variants,
        'template': template,
        'user_design': user_design,
        'initial_json': json.dumps(initial_json) if initial_json else None,
        'design_id': design_id,
        'clipart': clipart,
        'shapes': shapes,
        'backgrounds': backgrounds,
        'fonts': fonts,
        'color_palettes': color_palettes,
    }
    return render(request, 'custom_design/editor.html', context)


@login_required
@require_POST
def save_design(request):
    """API endpoint to save a design"""
    try:
        data = json.loads(request.body)
        
        canvas_json = data.get('canvas_json')
        name = escape(data.get('name', 'Untitled Design'))
        product_type_id = data.get('product_type_id')
        variant_id = data.get('variant_id')
        template_id = data.get('template_id')
        design_id = data.get('design_id')
        preview_image_data = data.get('preview_image')
        is_draft = data.get('is_draft', True)
        design_side = data.get('design_side', 'front')
        
        # Validate required data
        if not canvas_json or not product_type_id:
            return JsonResponse({
                'success': False, 
                'error': 'Missing required data (canvas_json or product_type_id)'
            }, status=400)
        
        # Get related objects
        product_type = get_object_or_404(ProductType, id=product_type_id)
        
        variant = None
        if variant_id:
            variant = get_object_or_404(ProductVariant, id=variant_id)
        
        template = None
        if template_id:
            template = get_object_or_404(DesignTemplate, id=template_id)
        
        # Process preview image if provided
        preview_image = None
        if preview_image_data and preview_image_data.startswith('data:image'):
            # Extract the base64 data
            format, imgstr = preview_image_data.split(';base64,')
            ext = format.split('/')[-1]
            
            # Convert to PIL Image
            img_data = base64.b64decode(imgstr)
            img = Image.open(io.BytesIO(img_data))
            
            # Create a buffer to save the image
            buffer = io.BytesIO()
            if ext.lower() == 'png':
                img.save(buffer, format='PNG')
            else:
                img.save(buffer, format='JPEG', quality=85)
            
            # Create a Django ContentFile
            from django.core.files.base import ContentFile
            preview_image = ContentFile(buffer.getvalue(), name=f"{name}.{ext}")
        
        # Update existing design or create new one
        if design_id:
            user_design = get_object_or_404(UserDesign, id=design_id, user=request.user)
            user_design.name = name
            user_design.canvas_json = canvas_json
            user_design.is_draft = is_draft
            user_design.design_side = design_side
            
            if variant:
                user_design.product_variant = variant
                
            if preview_image:
                if user_design.preview_image:
                    # Delete old preview if it exists
                    user_design.preview_image.delete(save=False)
                user_design.preview_image = preview_image
                
            user_design.save()
            
        else:
            # Create new design
            user_design = UserDesign.objects.create(
                user=request.user,
                name=name,
                product_type=product_type,
                product_variant=variant,
                template=template,
                canvas_json=canvas_json,
                is_draft=is_draft,
                design_side=design_side
            )
            
            if preview_image:
                user_design.preview_image = preview_image
                user_design.save()
        
        return JsonResponse({
            'success': True,
            'design_id': user_design.id,
            'message': 'Design saved successfully'
        })
        
    except Exception as e:
        logger.error(f"Error saving design: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
def load_design(request, design_id):
    """API endpoint to load a saved design"""
    try:
        design = get_object_or_404(UserDesign, id=design_id, user=request.user)
        
        response_data = {
            'success': True,
            'design': {
                'id': design.id,
                'name': design.name,
                'canvas_json': design.canvas_json,
                'product_type_id': design.product_type.id,
                'design_side': design.design_side,
                'is_draft': design.is_draft
            }
        }
        
        if design.product_variant:
            response_data['design']['variant_id'] = design.product_variant.id
            
        if design.template:
            response_data['design']['template_id'] = design.template.id
            
        return JsonResponse(response_data)
        
    except Exception as e:
        logger.error(f"Error loading design: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


def get_assets(request):
    """API endpoint to get design assets"""
    asset_type = request.GET.get('type', 'clipart')
    search = request.GET.get('search', '')
    
    assets = DesignAsset.objects.filter(category=asset_type, active=True)
    
    if search:
        assets = assets.filter(name__icontains=search) | assets.filter(tags__icontains=search)
    
    assets_data = [{
        'id': asset.id,
        'name': asset.name,
        'image_url': asset.image.url,
        'svg_data': asset.svg_data if asset.svg_data else None,
        'is_premium': asset.is_premium
    } for asset in assets]
    
    return JsonResponse({
        'success': True,
        'assets': assets_data
    })


@login_required
def my_designs(request):
    """View for user's saved designs"""
    designs = UserDesign.objects.filter(user=request.user).order_by('-updated_at')
    
    context = {
        'designs': designs
    }
    return render(request, 'custom_design/my_designs.html', context)


@login_required
def design_detail(request, design_id):
    """View details of a specific saved design"""
    design = get_object_or_404(UserDesign, id=design_id, user=request.user)
    
    context = {
        'design': design
    }
    return render(request, 'custom_design/design_detail.html', context)


@login_required
@require_POST
def delete_design(request, design_id):
    """Delete a saved design"""
    design = get_object_or_404(UserDesign, id=design_id, user=request.user)
    
    try:
        design.delete()
        return JsonResponse({
            'success': True,
            'message': 'Design deleted successfully'
        })
    except Exception as e:
        logger.error(f"Error deleting design: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)