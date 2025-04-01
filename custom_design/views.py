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
from django.contrib import messages
        
        

from .models import *
from store.models import PendingOrder

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
    return render(request, 'custom_design/myhome.html',context)


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








# ----------------------------------------------------------------------------------------------------

# def design_editor(request):
#     """Main design editor using Fabric.js"""
#     product_type_id = request.GET.get('product_type')
#     template_id = request.GET.get('template')
#     variant_id = request.GET.get('variant')
#     design_id = request.GET.get('design_id')  # For editing existing designs
    
       
#     template = None  # Ensure template is defined
    
#     if template_id:
#         template = get_object_or_404(DesignTemplate, id=template_id)
    
#      # Check if this is a premium template that requires purchase
#     if template and template.is_premium:
#         from custom_design.templatetags.design_tags import has_purchased
#         if not has_purchased(request.user, template.id):
#             messages.error(request, "You need to purchase this template before using it.")
#             return redirect('designs:product_templates', product_slug=product_type.slug)
    
    
#     # Validate required parameters
#     if not product_type_id and not design_id:
#         return HttpResponseBadRequest("Product type or design ID is required")
    
#     # Initialize with defaults
#     product_type = None
#     template = None
#     variant = None
#     user_design = None
#     initial_json = None
    
#     if design_id and request.user.is_authenticated:
#         # Load existing design
#         user_design = get_object_or_404(
#             UserDesign, id=design_id, user=request.user
#         )
#         product_type = user_design.product_type
#         variant = user_design.product_variant
#         template = user_design.template
#         initial_json = user_design.canvas_json
#     else:
#         # New design
#         product_type = get_object_or_404(ProductType, id=product_type_id, active=True)
        
#         if template_id:
#             template = get_object_or_404(
#                 DesignTemplate, id=template_id, product_type=product_type, active=True
#             )
#             initial_json = template.canvas_json
        
#         if variant_id:
#             variant = get_object_or_404(
#                 ProductVariant, id=variant_id, product_type=product_type, active=True
#             )
#         else:
#             # Get default variant if available
#             try:
#                 variant = ProductVariant.objects.filter(
#                     product_type=product_type, is_default=True, active=True
#                 ).first()
#             except ProductVariant.DoesNotExist:
#                 variant = None
    
#     # DEBUG: Print initial JSON details
#     print("DEBUG: initial_json type:", type(initial_json))
#     print("DEBUG: initial_json content:", initial_json)
    
#     # Ensure initial_json is always a dictionary
#     if initial_json is None:
#         initial_json = {"version": "5.3.1", "objects": [], "background": "#ffffff"}
    
#     # Ensure initial_json is JSON serializable
#     try:
#         # Use mark_safe to prevent double-escaping when rendered in template
#         from django.utils.safestring import mark_safe
#         serialized_initial_json = mark_safe(json.dumps(initial_json))
#     except TypeError as e:
#         print(f"DEBUG: JSON serialization error - {e}")
#         # Fallback to default empty canvas
#         serialized_initial_json = mark_safe(json.dumps({"version": "5.3.1", "objects": [], "background": "#ffffff"}))
    
#     # Rest of the view remains the same...
#     context = {
#         'product_type': product_type,
#         'variant': variant,
#         # 'all_variants': all_variants,
#         'template': template,
#         'user_design': user_design,
#         'initial_json': serialized_initial_json,  # Use the serialized version
#         'design_id': design_id,
#         # ... other context variables
#     }
#     return render(request, 'custom_design/editor.html', context)

def design_editor(request):
    """Main design editor using Fabric.js"""
    product_type_id = request.GET.get('product_type')
    template_id = request.GET.get('template')
    variant_id = request.GET.get('variant')
    design_id = request.GET.get('design_id')  # For editing existing designs
    pending_order_id = request.GET.get('pending_order_id')  # For designs created during order flow
    
    template = None  # Ensure template is defined
    
    if template_id:
        template = get_object_or_404(DesignTemplate, id=template_id)
    
    # Check if this is a premium template that requires purchase
    if template and template.is_premium:
        from custom_design.templatetags.design_tags import has_purchased
        if not has_purchased(request.user, template.id):
            messages.error(request, "You need to purchase this template before using it.")
            return redirect('designs:product_templates', product_slug=product_type.slug)
    
    # Validate required parameters
    if not product_type_id and not design_id:
        return HttpResponseBadRequest("Product type or design ID is required")
    
    # Initialize with defaults
    product_type = None
    variant = None
    user_design = None
    initial_json = None
    pending_order = None
    
    # Check if this is part of an order flow
    if pending_order_id:
        try:
            pending_order = PendingOrder.objects.get(id=pending_order_id)
            # If product is associated with a specific product type, get it
            if hasattr(pending_order.product, 'product_type'):
                product_type_id = pending_order.product.product_type.id
            
            # If variant is specified in the order, use it
            if pending_order.variant and hasattr(pending_order.variant, 'product_variant'):
                variant_id = pending_order.variant.product_variant.id
        except PendingOrder.DoesNotExist:
            messages.warning(request, "The order information could not be found. Starting a new design.")
    
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
    
    # DEBUG: Print initial JSON details
    print("DEBUG: initial_json type:", type(initial_json))
    print("DEBUG: initial_json content:", initial_json)
    
    # Ensure initial_json is always a dictionary
    if initial_json is None:
        initial_json = {"version": "5.3.1", "objects": [], "background": "#ffffff"}
    
    # Ensure initial_json is JSON serializable
    try:
        # Use mark_safe to prevent double-escaping when rendered in template
        from django.utils.safestring import mark_safe
        serialized_initial_json = mark_safe(json.dumps(initial_json))
    except TypeError as e:
        print(f"DEBUG: JSON serialization error - {e}")
        # Fallback to default empty canvas
        serialized_initial_json = mark_safe(json.dumps({"version": "5.3.1", "objects": [], "background": "#ffffff"}))
    
    # Process design save if this is a POST request
    if request.method == 'POST' and request.user.is_authenticated:
        design_name = request.POST.get('design_name', f'Design for {product_type.name}')
        canvas_json = request.POST.get('canvas_json')
        preview_image = request.FILES.get('preview_image')
        
        try:
            # Parse the canvas JSON
            canvas_data = json.loads(canvas_json)
            
            # Create or update the design
            if user_design:
                # Update existing design
                user_design.name = design_name
                user_design.canvas_json = canvas_data
                if preview_image:
                    user_design.preview_image = preview_image
                user_design.is_draft = False
                user_design.save()
                messages.success(request, "Your design has been updated.")
            else:
                # Create new design
                user_design = UserDesign.objects.create(
                    user=request.user,
                    name=design_name,
                    product_type=product_type,
                    product_variant=variant,
                    template=template,
                    canvas_json=canvas_data,
                    preview_image=preview_image,
                    is_draft=False
                )
                messages.success(request, "Your design has been saved.")
            
            # If this is part of an order flow, link the design to the pending order
            if pending_order:
                pending_order.user_design = user_design
                pending_order.order_type = 'design'
                pending_order.save()
                
                # Redirect to order confirmation
                return redirect('order_confirmation', order_id=pending_order.id)
            
            # Otherwise, redirect to the designs page
            return redirect('user_designs')
            
        except json.JSONDecodeError:
            messages.error(request, "There was an error processing your design data. Please try again.")
        except Exception as e:
            messages.error(request, f"An error occurred: {str(e)}")
    
    # Check if anonymous user with pending order
    if not request.user.is_authenticated and pending_order:
        messages.info(request, "Please log in or sign up to save your design and complete your order.")
    
    context = {
        'product_type': product_type,
        'variant': variant,
        'template': template,
        'user_design': user_design,
        'initial_json': serialized_initial_json,  # Use the serialized version
        'design_id': design_id,
        'pending_order': pending_order,  # Pass the pending order to the template
        'is_order_flow': pending_order is not None,  # Flag to indicate this is part of an order
    }
    return render(request, 'custom_design/editor.html', context)




# ---------------------------------------------------------------------------

# @login_required
# @require_POST
# def save_design(request):
#     """API endpoint to save a design"""
#     try:
#         data = json.loads(request.body)
        
#         canvas_json = data.get('canvas_json')
#         name = escape(data.get('name', 'Untitled Design'))
#         product_type_id = data.get('product_type_id')
#         variant_id = data.get('variant_id')
#         template_id = data.get('template_id')
#         design_id = data.get('design_id')
#         preview_image_data = data.get('preview_image')
#         is_draft = data.get('is_draft', True)
#         design_side = data.get('design_side', 'front')
        
#         # Validate required data
#         if not canvas_json or not product_type_id:
#             return JsonResponse({
#                 'success': False, 
#                 'error': 'Missing required data (canvas_json or product_type_id)'
#             }, status=400)
        
#         # Get related objects
#         product_type = get_object_or_404(ProductType, id=product_type_id)
        
#         variant = None
#         if variant_id:
#             variant = get_object_or_404(ProductVariant, id=variant_id)
        
#         template = None
#         if template_id:
#             template = get_object_or_404(DesignTemplate, id=template_id)
        
#         # Process preview image if provided
#         preview_image = None
#         if preview_image_data and preview_image_data.startswith('data:image'):
#             # Extract the base64 data
#             format, imgstr = preview_image_data.split(';base64,')
#             ext = format.split('/')[-1]
            
#             # Convert to PIL Image
#             img_data = base64.b64decode(imgstr)
#             img = Image.open(io.BytesIO(img_data))
            
#             # Create a buffer to save the image
#             buffer = io.BytesIO()
#             if ext.lower() == 'png':
#                 img.save(buffer, format='PNG')
#             else:
#                 img.save(buffer, format='JPEG', quality=85)
            
#             # Create a Django ContentFile
#             from django.core.files.base import ContentFile
#             preview_image = ContentFile(buffer.getvalue(), name=f"{name}.{ext}")
        
#         # Update existing design or create new one
#         if design_id:
#             user_design = get_object_or_404(UserDesign, id=design_id, user=request.user)
#             user_design.name = name
#             user_design.canvas_json = canvas_json
#             user_design.is_draft = is_draft
#             user_design.design_side = design_side
            
#             if variant:
#                 user_design.product_variant = variant
                
#             if preview_image:
#                 if user_design.preview_image:
#                     # Delete old preview if it exists
#                     user_design.preview_image.delete(save=False)
#                 user_design.preview_image = preview_image
                
#             user_design.save()
            
#         else:
#             # Create new design
#             user_design = UserDesign.objects.create(
#                 user=request.user,
#                 name=name,
#                 product_type=product_type,
#                 product_variant=variant,
#                 template=template,
#                 canvas_json=canvas_json,
#                 is_draft=is_draft,
#                 design_side=design_side
#             )
            
#             if preview_image:
#                 user_design.preview_image = preview_image
#                 user_design.save()
        
#         return JsonResponse({
#             'success': True,
#             'design_id': user_design.id,
#             'message': 'Design saved successfully'
#         })
        
#     except Exception as e:
#         logger.error(f"Error saving design: {str(e)}")
#         return JsonResponse({
#             'success': False,
#             'error': str(e)
#         }, status=500)





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
        
        # Check if this is part of an order flow
        pending_order_id = request.session.get('pending_order_id')
        redirect_url = None
        
        if pending_order_id:
            try:
                # Link the design to the pending order
                pending_order = PendingOrder.objects.get(id=pending_order_id)
                pending_order.user_design = user_design
                pending_order.order_type = 'design'
                pending_order.save()
                
                # Clear the session variable
                del request.session['pending_order_id']
                request.session.modified = True
                
                # Set redirect URL to order confirmation
                redirect_url = reverse('order_confirmation', kwargs={'order_id': pending_order_id})
                
                logger.info(f"Design {user_design.id} linked to pending order {pending_order_id}")
            except PendingOrder.DoesNotExist:
                logger.warning(f"Pending order {pending_order_id} not found when saving design {user_design.id}")
        
        response_data = {
            'success': True,
            'design_id': user_design.id,
            'message': 'Design saved successfully'
        }
        
        # Add redirect URL if needed
        if redirect_url:
            response_data['redirect_url'] = redirect_url
        
        return JsonResponse(response_data)
        
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
        
        
        
        
        
        
        
        
        
        
        
 


def has_purchased_template(user, template_id):
    """Utility function to check if user has purchased a template"""
    if not user.is_authenticated:
        return False
        
    return TemplateTransaction.objects.filter(
        user=user,
        template_id=template_id,
        is_verified=True
    ).exists()
    
    
    
    
    
@login_required
def purchase_template(request, template_id):
    """Handle template purchase with separate payment flow"""
    from django.db import IntegrityError
    import secrets
    
    template = get_object_or_404(DesignTemplate, id=template_id, active=True)
    
    # Check if already purchased
    is_purchased = TemplateTransaction.objects.filter(
        user=request.user, 
        template=template,
        is_verified=True
    ).exists()
    
    if is_purchased:
        # Already purchased, redirect to editor
        messages.info(request, "You've already purchased this template.")
        return redirect(f"{reverse('editor')}?product_type={template.product_type.id}&template={template.id}")
    
    if request.method == "POST":
        # Generate payment reference
        payment_ref = f"template_{secrets.token_urlsafe(16)}"
        
        # Create transaction record (or update existing one)
        try:
            transaction, created = TemplateTransaction.objects.get_or_create(
                user=request.user,
                template=template,
                defaults={
                    'payment_ref': payment_ref,
                    'is_verified': False
                }
            )
            
            if not created:
                # Update the payment reference if this is an existing transaction
                transaction.payment_ref = payment_ref
                transaction.save()
                
        except IntegrityError:
            # If there's a race condition, just get the existing one
            transaction = TemplateTransaction.objects.get(
                user=request.user,
                template=template
            )
            transaction.payment_ref = payment_ref
            transaction.save()
        
        # Store reference in session for verification
        request.session['template_payment_ref'] = payment_ref
        request.session.modified = True
        
        # Initialize Paystack payment
        from django.conf import settings
        
        context = {
            'template': template,
            'payment_ref': payment_ref,
            'amount': 500,  # Template price
            'amount_value': 500 * 100,  # Paystack requires amount in kobo
            'email': request.user.email,
            'paystack_pub_key': settings.PAYSTACK_PUBLIC_KEY,
        }
        
        return render(request, 'custom_design/template_payment.html', context)
    
    # GET request - show confirmation page
    return render(request, 'custom_design/purchase_template.html', {
        'template': template,
        'price': 500
    })
    
    
    
@login_required
def verify_template_payment(request, payment_ref):
    """Verify template payment after Paystack callback"""
    transaction = get_object_or_404(TemplateTransaction, 
                                   payment_ref=payment_ref, 
                                   user=request.user)
    
    # Verify payment with Paystack
    from payments.models import Paystack
    paystack = Paystack()
    status, result = paystack.verify_payment(payment_ref, 500)  # 500 is the amount
    
    if status:
        # Update transaction as verified
        transaction.is_verified = True
        transaction.save()
        
        messages.success(request, "Template purchased successfully!")
        return redirect(f"{reverse('editor')}?product_type={transaction.template.product_type.id}&template={transaction.template.id}")
    else:
        messages.error(request, "Payment verification failed.")
        return redirect('designs:product_templates', product_slug=transaction.template.product_type.slug)
    
    
    
    
    
@login_required
def template_payment(request, template_id):
    """
    Render payment page for a specific template
    """
    import logging
    import secrets
    
    logger = logging.getLogger(__name__)
    
    try:
        # Fetch the template
        template = get_object_or_404(DesignTemplate, id=template_id, active=True)
        
        # Check if already purchased
        is_purchased = TemplateTransaction.objects.filter(
            user=request.user, 
            template=template,
            is_verified=True
        ).exists()
        
        if is_purchased:
            messages.info(request, "You've already purchased this template.")
            return redirect(f"/editor/?product_type={template.product_type.id}&template={template.id}")
        
        # Get the most recent pending transaction for this template and user
        transaction = TemplateTransaction.objects.filter(
            user=request.user,
            template=template,
            is_verified=False
        ).first()
        
        # Generate payment reference if no existing transaction
        if not transaction:
            payment_ref = f"template_{secrets.token_urlsafe(16)}"
            transaction = TemplateTransaction.objects.create(
                user=request.user,
                template=template,
                payment_ref=payment_ref,
                is_verified=False
            )
        
        # Prepare context for payment page
        context = {
            'template': template,
            'payment_ref': transaction.payment_ref,
            'amount': 500,  # Template price
            'amount_value': 500 * 100,  # Paystack requires amount in kobo
            'email': request.user.email,
            'paystack_pub_key': settings.PAYSTACK_PUBLIC_KEY,
        }
        
        logger.info(f"Rendering payment page for template {template_id}")
        return render(request, 'custom_design/template_payment.html', context)
    
    except Exception as e:
        logger.error(f"Error in template payment page: {str(e)}", exc_info=True)
        messages.error(request, "An error occurred while processing your payment.")
        return redirect(f"/customproducts/{template.product_type.slug}/")