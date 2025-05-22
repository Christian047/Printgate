from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
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
from .forms import DesignTemplateForm, ProductTypeForm
        
        
        
def is_admin(user):
    return user.is_staff or user.is_superuser



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
@login_required
@user_passes_test(is_admin)
def design_editor(request, template_id=None):
    """
    Main design editor using Fabric.js
    Handles both the admin path (/design-editor/<id>/) and regular editor via query params
    """
    # Initialize variables with default values
    template = None
    product_type = None
    variant = None
    user_design = None
    initial_json = None
    pending_order = None
    is_admin_editor = False
    design_id = None
    
    # Check if we're accessing via admin template editor path
    if template_id is not None:
        # This is the admin template editor (design-editor/<id>/)
        template = get_object_or_404(DesignTemplate, id=template_id)
        product_type = template.product_type
        initial_json = template.canvas_json
        is_admin_editor = True
    else:
        # This is the regular editor (editor/?product_type=X&template=Y)
        product_type_id = request.GET.get('product_type')
        template_id_param = request.GET.get('template')
        variant_id = request.GET.get('variant')
        design_id = request.GET.get('design_id')
        pending_order_id = request.GET.get('pending_order_id')
        
        # Template from query parameter
        if template_id_param:
            template = get_object_or_404(DesignTemplate, id=template_id_param)
            
            # Premium template check for regular users (not needed for admin editor)
            if template.is_premium:
                from custom_design.templatetags.design_tags import has_purchased
                if not has_purchased(request.user, template.id):
                    messages.error(request, "You need to purchase this template before using it.")
                    return redirect('designs:product_templates', product_slug=product_type.slug)
        
        # Validate required parameters for regular editor
        if not product_type_id and not design_id:
            return HttpResponseBadRequest("Product type or design ID is required")
        
        # Check if this is part of an order flow
        if pending_order_id:
            try:
                pending_order = PendingOrder.objects.get(id=pending_order_id)
                # Get product type from order if available
                if hasattr(pending_order.product, 'product_type'):
                    product_type_id = pending_order.product.product_type.id
                
                # Get variant from order if available
                if pending_order.variant and hasattr(pending_order.variant, 'product_variant'):
                    variant_id = pending_order.variant.product_variant.id
            except PendingOrder.DoesNotExist:
                messages.warning(request, "The order information could not be found. Starting a new design.")
        
        # Load existing design or create a new one
        if design_id and request.user.is_authenticated:
            # Load existing design
            user_design = get_object_or_404(UserDesign, id=design_id, user=request.user)
            product_type = user_design.product_type
            variant = user_design.product_variant
            template = user_design.template
            initial_json = user_design.canvas_json
        else:
            # New design
            product_type = get_object_or_404(ProductType, id=product_type_id, active=True)
            
            if template_id_param:
                template = get_object_or_404(DesignTemplate, id=template_id_param, product_type=product_type, active=True)
                initial_json = template.canvas_json
            
            if variant_id:
                variant = get_object_or_404(ProductVariant, id=variant_id, product_type=product_type, active=True)
            else:
                # Get default variant if available
                try:
                    variant = ProductVariant.objects.filter(product_type=product_type, is_default=True, active=True).first()
                except ProductVariant.DoesNotExist:
                    variant = None
                    
        # Process design save if this is a POST request (regular editor only)
        if not is_admin_editor and request.method == 'POST' and request.user.is_authenticated:
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
    
    # Shared code for both editor modes
    
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
    
    # Check if anonymous user with pending order (regular editor only)
    if not is_admin_editor and not request.user.is_authenticated and pending_order:
        messages.info(request, "Please log in or sign up to save your design and complete your order.")
    
    # Prepare context
    context = {
        'product_type': product_type,
        'variant': variant,
        'template': template,
        'user_design': user_design,
        'initial_json': serialized_initial_json,
        'design_id': design_id,
        'pending_order': pending_order,
        'is_order_flow': pending_order is not None if not is_admin_editor else False,
        'is_admin_editor': is_admin_editor,
    }
    
    # Make sure to return an HttpResponse
    return render(request, 'custom_design/editor.html', context)




# -------


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
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    # Add these imports at the top if not already present
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from .models import DesignTemplate, ProductType, DesignCategory, UserDesign
from .forms import DesignTemplateForm
import json

def is_admin(user):
    return user.is_staff or user.is_superuser

@login_required
@user_passes_test(is_admin)
def design_template_create(request):
    # Get common data needed for all form types
    product_types = ProductType.objects.filter(active=True)
    design_categories = DesignCategory.objects.filter(active=True)
    # user_designs = UserDesign.objects.filter(is_draft=True).select_related('product_type').order_by('-updated_at')
    user_designs = UserDesign.objects.all()
    
    if request.method == 'POST':
        form_type = request.POST.get('form_type', 'manual')
        
        # Manual form submission
        if form_type == 'manual':
            form = DesignTemplateForm(request.POST, request.FILES)
            if form.is_valid():
                template = form.save()
                messages.success(request, f"Design template '{template.name}' created successfully.")
                return redirect('design_template_list')
        
        # Import from user design
        elif form_type == 'import':
            # Get details from form
            name = request.POST.get('template_name')
            product_type_id = request.POST.get('product_type')
            category_id = request.POST.get('category')
            description = request.POST.get('description', '')
            is_featured = request.POST.get('is_featured') == 'on'
            is_premium = request.POST.get('is_premium') == 'on'
            user_design_id = request.POST.get('user_design_id')
            
            try:
                # Fetch the user design
                user_design = UserDesign.objects.get(id=user_design_id)
                product_type = ProductType.objects.get(id=product_type_id)
                category = DesignCategory.objects.get(id=category_id)
                
                # Create the template using user design data
                template = DesignTemplate.objects.create(
                    name=name,
                    product_type=product_type,
                    category=category,
                    description=description,
                    preview_image=user_design.preview_image,
                    canvas_json=user_design.canvas_json,
                    is_featured=is_featured,
                    is_premium=is_premium,
                    active=True
                )
                
                messages.success(request, f"Design template '{template.name}' imported successfully.")
                return redirect('design_template_list')
            except (UserDesign.DoesNotExist, ProductType.DoesNotExist, DesignCategory.DoesNotExist) as e:
                messages.error(request, f"Error importing design: {str(e)}")
        
        # Use design editor
        elif form_type == 'editor':
            # Get basic information and redirect to editor
            name = request.POST.get('editor_name')
            product_type_id = request.POST.get('editor_product_type')
            category_id = request.POST.get('editor_category')
            description = request.POST.get('editor_description', '')
            
            try:
                product_type = ProductType.objects.get(id=product_type_id)
                category = DesignCategory.objects.get(id=category_id)
                
                # Create a temporary template
                temp_template = DesignTemplate.objects.create(
                    name=name,
                    product_type=product_type,
                    category=category,
                    description=description,
                    canvas_json=json.loads('{"version": "5.3.1", "objects": [], "background": "#FFFFFF"}'),
                    active=False  # Mark as inactive until completed
                )
                
                # Redirect to the design editor with the template ID
                return redirect('design_editor', template_id=temp_template.id)
            except (ProductType.DoesNotExist, DesignCategory.DoesNotExist) as e:
                messages.error(request, f"Error creating design template: {str(e)}")
    else:
        form = DesignTemplateForm()
    
    # Render the form
    return render(request, 'custom_design/design_template_form.html', {
        'form': form,
        'title': 'Add New Design Template',
        'submit_text': 'Create Template',
        'product_types': product_types,
        'design_categories': design_categories,
        'user_designs': user_designs,
    })



def design_templates_view(request):
    # Handle filters
    product_type_id = request.GET.get('product_type', '')
    status = request.GET.get('status', '')
    search = request.GET.get('search', '')
    
    # Query templates with filters
    templates = DesignTemplate.objects.all()
    if product_type_id:
        templates = templates.filter(product_type_id=product_type_id)
    if status == 'active':
        templates = templates.filter(is_active=True)
    elif status == 'draft':
        templates = templates.filter(is_active=False)
    if search:
        templates = templates.filter(name__icontains=search)
    
    # Get all product types for filter dropdown
    all_product_types = ProductType.objects.all()
    
    # Organize templates by product type
    templates_by_type = {}
    if product_type_id:
        # If filtered by type, only include that type
        product_type = ProductType.objects.get(id=product_type_id)
        templates_by_type[product_type] = templates
    else:
        # Otherwise group by all types
        for product_type in all_product_types:
            type_templates = templates.filter(product_type=product_type)
            if type_templates.exists():
                templates_by_type[product_type] = type_templates
    
    return render(request, 'design_templates.html', {
        'templates_by_type': templates_by_type,
        'all_product_types': all_product_types,
        'selected_type': product_type_id,
        'status': status,
        'search': search,
    })



@login_required
@user_passes_test(is_admin)
def design_template_edit(request, pk):
    design_template = get_object_or_404(DesignTemplate, pk=pk)
    product_types = ProductType.objects.filter(active=True)
    design_categories = DesignCategory.objects.filter(active=True)
    user_designs = UserDesign.objects.filter(is_draft=False).select_related('product_type').order_by('-updated_at')
    
    if request.method == 'POST':
        form_type = request.POST.get('form_type', 'manual')
        
        # Manual form submission
        if form_type == 'manual':
            form = DesignTemplateForm(request.POST, request.FILES, instance=design_template)
            if form.is_valid():
                template = form.save()
                messages.success(request, f"Design template '{template.name}' updated successfully.")
                return redirect('design_template_list')
        
        # Import from user design
        elif form_type == 'import':
            user_design_id = request.POST.get('user_design_id')
            
            try:
                user_design = UserDesign.objects.get(id=user_design_id)
                
                # Update fields from the form
                design_template.name = request.POST.get('template_name', design_template.name)
                design_template.description = request.POST.get('description', design_template.description)
                design_template.is_featured = request.POST.get('is_featured') == 'on'
                design_template.is_premium = request.POST.get('is_premium') == 'on'
                
                # Update canvas data and preview
                design_template.canvas_json = user_design.canvas_json
                if user_design.preview_image:
                    design_template.preview_image = user_design.preview_image
                
                # Update product_type and category if provided
                product_type_id = request.POST.get('product_type')
                category_id = request.POST.get('category')
                if product_type_id:
                    design_template.product_type = ProductType.objects.get(id=product_type_id)
                if category_id:
                    design_template.category = DesignCategory.objects.get(id=category_id)
                
                design_template.save()
                
                messages.success(request, f"Design template '{design_template.name}' updated with imported design.")
                return redirect('design_template_list')
            except UserDesign.DoesNotExist:
                messages.error(request, "Selected user design does not exist.")
        
        # Use design editor
        elif form_type == 'editor':
            # Redirect to the editor with the existing template ID
            return redirect('design_editor', template_id=design_template.id)
    else:
        form = DesignTemplateForm(instance=design_template)
    
    # Render the form
    return render(request, 'custom_design/design_template_form.html', {
        'form': form,
        'design_template': design_template,
        'title': f'Edit Design Template: {design_template.name}',
        'submit_text': 'Update Template',
        'product_types': product_types,
        'design_categories': design_categories,
        'user_designs': user_designs,
    })

# API endpoint to save canvas data from the editor
@login_required
@user_passes_test(is_admin)
def save_template_canvas(request, template_id):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Method not allowed'}, status=405)
        
    try:
        design_template = DesignTemplate.objects.get(id=template_id)
        data = json.loads(request.body)
        canvas_json = data.get('canvas_json')
        
        if not canvas_json:
            return JsonResponse({'success': False, 'message': 'No canvas data provided'}, status=400)
            
        # Update the canvas JSON data
        design_template.canvas_json = canvas_json
        
        # Handle preview image if provided
        preview_image_data = data.get('preview_image')
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
            
            # Delete old preview if it exists
            if design_template.preview_image:
                design_template.preview_image.delete(save=False)
                
            # Create a Django ContentFile and save it
            from django.core.files.base import ContentFile
            design_template.preview_image = ContentFile(buffer.getvalue(), name=f"{design_template.name}.{ext}")
        
        # Mark as active now that it has content
        design_template.active = True
        design_template.save()
        
        # Check if this is part of an order flow
        pending_order_id = request.session.get('pending_order_id')
        redirect_url = None
        
        if pending_order_id:
            try:
                # Create a UserDesign from this template
                if request.user.is_authenticated:
                    user_design = UserDesign.objects.create(
                        user=request.user,
                        name=f"Design based on {design_template.name}",
                        product_type=design_template.product_type,
                        template=design_template,
                        canvas_json=canvas_json,
                        is_draft=False
                    )
                    
                    # Copy preview image if available
                    if design_template.preview_image:
                        user_design.preview_image = design_template.preview_image
                        user_design.save()
                    
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
                    logger.info(f"Template {design_template.id} linked to pending order {pending_order_id} via user design {user_design.id}")
            except PendingOrder.DoesNotExist:
                logger.warning(f"Pending order {pending_order_id} not found when saving template {design_template.id}")
        
        response_data = {
            'success': True,
            'message': 'Template saved successfully',
            'template_id': design_template.id
        }
        
        # Add redirect URL if needed
        if redirect_url:
            response_data['redirect_url'] = redirect_url
            
        return JsonResponse(response_data)
        
    except DesignTemplate.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Template not found'}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'Invalid JSON data'}, status=400)
    except Exception as e:
        logger.error(f"Error saving template canvas: {str(e)}", exc_info=True)
        return JsonResponse({'success': False, 'message': f'An error occurred: {str(e)}'}, status=500)
    
    
    
    
    
@login_required
@user_passes_test(is_admin)
def product_type_list(request):
    product_types = ProductType.objects.all().order_by('order', 'name')
    return render(request, 'custom_design/product_type_list.html', {
        'product_types': product_types,
        'title': 'Product Types'
    })

@login_required
@user_passes_test(is_admin)
def product_type_delete(request, pk):
    product_type = get_object_or_404(ProductType, pk=pk)
    
    if request.method == 'POST':
        product_type_name = product_type.name
        product_type.delete()
        messages.success(request, f"Product type '{product_type_name}' has been deleted.")
        return redirect('product_type_list')
    
    return render(request, 'delete_confirmation.html', {
        'title': 'Delete Product Type',
        'object': product_type,
        'object_name': product_type.name,
        'cancel_url': 'product_type_list'
    })








@login_required
@user_passes_test(is_admin)
def design_template_delete(request, pk):
    template = get_object_or_404(DesignTemplate, pk=pk)
    
    if request.method == 'POST':
        template_name = template.name
        template.delete()
        messages.success(request, f"Design template '{template_name}' has been deleted.")
        return redirect('design_template_list')
    
    return render(request, 'delete_confirmation.html', {
        'title': 'Delete Design Template',
        'object': template,
        'object_name': template.name,
        'cancel_url': 'design_template_list'
    })




@login_required
@user_passes_test(is_admin)
def design_template_list(request):
    templates = DesignTemplate.objects.all().select_related('product_type', 'category')
    
    # Filter options
    product_type_id = request.GET.get('product_type')
    category_id = request.GET.get('category')
    is_featured = request.GET.get('is_featured')
    is_premium = request.GET.get('is_premium')
    
    if product_type_id:
        templates = templates.filter(product_type_id=product_type_id)
    
    if category_id:
        templates = templates.filter(category_id=category_id)
    
    if is_featured:
        templates = templates.filter(is_featured=(is_featured == '1'))
    
    if is_premium:
        templates = templates.filter(is_premium=(is_premium == '1'))
    
    # Get all product types for filter dropdown
    product_types = ProductType.objects.filter(active=True)
    categories = DesignCategory.objects.filter(active=True)
    
    # Organize templates by product type
    templates_by_type = {}
    
    if product_type_id:
        # If filtered by a specific product type, only show that group
        try:
            product_type = ProductType.objects.get(id=product_type_id)
            templates_by_type[product_type] = templates
        except ProductType.DoesNotExist:
            # Handle case where product type doesn't exist
            pass
    else:
        # Otherwise, group by all product types
        for product_type in product_types:
            type_templates = templates.filter(product_type=product_type)
            if type_templates.exists():
                templates_by_type[product_type] = type_templates
    
    # Check if preview URL exists in the project
    preview_url_exists = False
    try:
        from django.urls import reverse
        reverse('design_template_edit', args=[1])  # Test if edit URL exists
        # You'd test preview URL here, but we know it doesn't exist
    except:
        pass
    
    return render(request, 'custom_design/design_template_list.html', {
        'templates_by_type': templates_by_type,
        'product_types': product_types,
        'categories': categories,
        'selected_product_type': product_type_id,
        'selected_category': category_id,
        'selected_featured': is_featured,
        'selected_premium': is_premium,
        'preview_url_exists': preview_url_exists,
        'title': 'Design Templates'
    })

# @login_required
# @user_passes_test(is_admin)
# def design_editor(request, template_id):
#     template = get_object_or_404(DesignTemplate, pk=template_id)
    
#     # Add any additional context data needed for the editor
#     context = {
#         'template': template,
#         'title': f'Editing: {template.name}',
#         'product_type': template.product_type,
#         # Add other data your editor might need
#     }
    
#     return render(request, 'custom_design/editor.html', context)




@login_required
@user_passes_test(is_admin)
def product_type_create(request):
    if request.method == 'POST':
        form = ProductTypeForm(request.POST)
        if form.is_valid():
            product_type = form.save()
            messages.success(request, f"Product type '{product_type.name}' created successfully.")
            return redirect('product_type_list')
    else:
        form = ProductTypeForm()
    
    return render(request, 'custom_design/product_type_form.html', {
        'form': form,
        'title': 'Add New Product Type',
        'submit_text': 'Create Product Type'
    })
    
    
@login_required
@user_passes_test(is_admin)
def product_type_edit(request, pk):
    product_type = get_object_or_404(ProductType, pk=pk)
    
    if request.method == 'POST':
        form = ProductTypeForm(request.POST, instance=product_type)
        if form.is_valid():
            product_type = form.save()
            messages.success(request, f"Product type '{product_type.name}' updated successfully.")
            return redirect('product_type_list')
    else:
        form = ProductTypeForm(instance=product_type)
    
    return render(request, 'custom_design/product_type_form.html', {
        'form': form,
        'title': f'Edit Product Type: {product_type.name}',
        'submit_text': 'Update Product Type'
    })
    
    
    
    
    
    
    
    
    
    
    
@login_required
@require_POST
def delete_design(request, design_id):
    """Delete a saved design"""
    design = get_object_or_404(UserDesign, id=design_id, user=request.user)
    
    try:
        # Save the design name for the success message
        design_name = design.name
        
        # If the design has a preview image, delete it from storage
        if design.preview_image:
            # Delete the file from storage
            design.preview_image.delete(save=False)
        
        # Delete the design object
        design.delete()
        
        # Add success message
        messages.success(request, f'Design "{design_name}" has been deleted successfully.')
        
        return redirect('my_designs')
    except Exception as e:
        logger.error(f"Error deleting design: {str(e)}")
        messages.error(request, f"An error occurred while deleting the design: {str(e)}")
        return redirect('my_designs')