# views.py
from django.shortcuts import render,redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from .models import *
from store.models import *
# from .forms import PrintJobModelForm
from django.http import JsonResponse
from django.db.models import Q  
from .forms import *
from django.http import JsonResponse
import io
from PIL import Image
from store.utils import cookieCart, cartData, guestOrder
import json


def Home(request,pk=None):
    
 
    cart = request.COOKIES.get('cart',{})
    print(f'cart: {cart}')

    cats = Categories.objects.all()
    products = Product.objects.all()
    
    data = cartData(request)
    cartItems = data['cartItems']
    return render(request, 'base/Home1.html', {
        # 'forms': form,
        'cats': cats,
        'products':products,
        'cartItems':cartItems
    })



def product_detail(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    
    context = {
        'product': product
    }
    
    return render(request, 'base/product_detail.html', context)


def design_options(request,pk):
    product = get_object_or_404(Product, pk=pk)
    context = {'product': product}
    return render(request, 'base/design_options.html', context)



def list_Prints(request):
    jobs = PrintJob.objects.all()
    context = {'jobs': jobs}
    return render(request, 'uploadfiles.html', context)


def cat(request):
    return render(request, 'cat.html')



def autocomplete(request):
    if 'term' in request.GET:
        qs = Product.objects.filter(title__icontains=request.GET.get('term'))
        titles = list()
        for product in qs:
            titles.append(product.title)

        return JsonResponse(titles, safe=False)
    return render(request, 'base/Home2.html')





def design_options_page(request):
    return render(request, 'base/upload.html')


def create_print_order(request, pk):
    """Display the form to order a specific product"""
    product = get_object_or_404(Product, pk=pk)
    
    if request.method == 'POST':
        form = BaseOrderForm(product, request.POST, request.FILES)
        if form.is_valid():
            customer = None
            if request.user.is_authenticated:
                customer, created = Customer.objects.get_or_create(
                    user=request.user,
                    defaults={'name': request.user.get_full_name() or request.user.username,
                             'email': request.user.email}
                )
            
            # Save the pending order
            pending_order = form.save(customer=customer)
            
            # Store pending order ID in session for anonymous users
            if not request.user.is_authenticated:
                if 'pending_orders' not in request.session:
                    request.session['pending_orders'] = []
                request.session['pending_orders'].append(pending_order.id)
                request.session.modified = True
            
            # Redirect to order review page
            return redirect('order_confirmation', order_id=pending_order.id)
    else:
        form = BaseOrderForm(product)
    
    return render(request, 'base/create_order2.html', {
        'product': product,
        'form': form
    })



import logging

from django.db import IntegrityError, DatabaseError
from django.core.exceptions import ObjectDoesNotExist

# Initialize Logger
logger = logging.getLogger(__name__)

def hire_designer(request, pk):
    """Display the form to hire a designer for a specific product"""
    try:
        # Ensure the product exists
        product = get_object_or_404(Product, pk=pk)

        if request.method == 'POST':
            print('post')
            form = DesignerOrderForm(product, request.POST, request.FILES)
            
            if form.is_valid():
                print('form valid')
                customer = None
                try:
                    if request.user.is_authenticated:
                        # Get or create the customer record
                        customer, created = Customer.objects.get_or_create(
                            user=request.user,
                            defaults={'name': request.user.get_full_name() or request.user.username,
                                     'email': request.user.email}
                        )
                    
                    # Save the pending order
                    pending_order = form.save(customer=customer)

                    # Handle guest users by storing order in session
                    if not request.user.is_authenticated:
                        request.session.setdefault('pending_orders', []).append(pending_order.id)
                        request.session.modified = True

                    messages.success(request, "Your designer request has been submitted successfully!")
                    return redirect('order_confirmation', order_id=pending_order.id)

                except (IntegrityError, DatabaseError) as db_err:
                    logger.error(f"Database error while saving designer order: {db_err}")
                    messages.error(request, "An unexpected error occurred while processing your request. Please try again.")
                
                except ObjectDoesNotExist as obj_err:
                    logger.error(f"Missing related object: {obj_err}")
                    messages.error(request, "An error occurred. Some required data might be missing.")

                except Exception as e:
                    logger.exception(f"Unexpected error: {e}")
                    messages.error(request, "Something went wrong. Please try again or contact support.")
        
        else:
            print('not valid')
            form = DesignerOrderForm(product)

        return render(request, 'base/hire_designer.html', {
            'product': product,
            'form': form
        })

    except Exception as e:
        logger.exception(f"Unexpected error in hire_designer view: {e}")
        messages.error(request, "An error occurred while loading the page. Please try again.")
        return redirect('home')  # Redirect to a safe page (adjust as needed)



def hire_designer(request, pk):

    try:
  
        product = get_object_or_404(Product, pk=pk)

        if request.method == 'POST':
            print('post')
            form = DesignerOrderForm(product, request.POST, request.FILES)
            
            if form.is_valid():
                print('form valid')
                customer = None
                try:
                    if request.user.is_authenticated:
                        # Get or create the customer record
                        customer, created = Customer.objects.get_or_create(
                            user=request.user,
                            defaults={'name': request.user.get_full_name() or request.user.username,
                                    'email': request.user.email}
                        )
                    
                    # Save the pending order
                    pending_order = form.save(customer=customer)

                    # Handle guest users by storing order in session
                    if not request.user.is_authenticated:
                        request.session.setdefault('pending_orders', []).append(pending_order.id)
                        request.session.modified = True

                    messages.success(request, "Your designer request has been submitted successfully!")
                    return redirect('order_confirmation', order_id=pending_order.id)

                except (IntegrityError, DatabaseError) as db_err:
                    logger.error(f"Database error while saving designer order: {db_err}")
                    messages.error(request, "An unexpected error occurred while processing your request. Please try again.")
                
                except ObjectDoesNotExist as obj_err:
                    logger.error(f"Missing related object: {obj_err}")
                    messages.error(request, "An error occurred. Some required data might be missing.")

                except Exception as e:
                    logger.exception(f"Unexpected error: {e}")
                    messages.error(request, "Something went wrong. Please try again or contact support.")
                        
            else:
                print('form invalid')
          
                logger.warning(f"Form validation failed: {form.errors}")
       
        else:
            # Initialize empty form for GET requests
            form = DesignerOrderForm(product)

        return render(request, 'base/hire_designer.html', {
            'product': product,
            'form': form
        })

    except Exception as e:
        logger.exception(f"Unexpected error in hire_designer view: {e}")
        messages.error(request, "An error occurred while loading the page. Please try again.")
        return redirect('home')




def cart(request):
    return render(request,'base/shopping_cart.html')




def order_confirmation(request, order_id):
    order = get_object_or_404(PendingOrder, id=order_id)
    product = order.product 
    specifications = order.specifications.all()  # Get all specifications
    variant = order.variant
    
    data = cartData(request)
    cartItems = data['cartItems']
    
    file_size_formatted = None
    file_dimensions = None
    
    # Check if the order has a design file directly attached
    if order.design_file:
        try:
            # Get file size
            image_file = order.design_file
            file_size_bytes = image_file.size
            
            # Convert to more readable format
            if file_size_bytes < 1024:
                file_size_formatted = f"{file_size_bytes} bytes"
            elif file_size_bytes < 1024 * 1024:
                file_size_formatted = f"{file_size_bytes / 1024:.2f} KB"
            else:
                file_size_formatted = f"{file_size_bytes / (1024 * 1024):.2f} MB"
                
            # Try to get image dimensions if it's an actual image
            from PIL import Image
            from django.core.files.storage import default_storage
            
            with image_file.open() as img_file:
                with Image.open(img_file) as img:
                    file_dimensions = f"{img.width} x {img.height} pixels"
                    
        except Exception as e:
            # Just log the error but continue processing
            print(f"Error processing design file: {str(e)}")
    
    # Also look for design files in specifications
    file_specs = []
    for spec in specifications:
        if spec.field_file:
            try:
                file_size_bytes = spec.field_file.size
                
                if file_size_bytes < 1024:
                    spec_file_size = f"{file_size_bytes} bytes"
                elif file_size_bytes < 1024 * 1024:
                    spec_file_size = f"{file_size_bytes / 1024:.2f} KB"
                else:
                    spec_file_size = f"{file_size_bytes / (1024 * 1024):.2f} MB"
                
                file_specs.append({
                    'name': spec.field_name,
                    'file_name': spec.field_file.name.split('/')[-1],
                    'file_size': spec_file_size,
                    'file_url': spec.field_file.url
                })
            except Exception as e:
                print(f"Error processing spec file {spec.field_name}: {str(e)}")
    
    # Group specifications by type for display
    text_specs = [spec for spec in specifications if not spec.field_file]
    
    context = {
        'order': order,
        'variant': variant,
        'file_size': file_size_formatted,
        'file_dimensions': file_dimensions,
        'cartItems': cartItems,
        'product': product,
        'text_specs': text_specs,  # Text-based specifications
        'file_specs': file_specs,  # File-based specifications
    }
    
    return render(request, 'base/confirmation.html', context)

