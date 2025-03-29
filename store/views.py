from django.shortcuts import render
from django.http import JsonResponse
import json
import datetime
from .models import * 
from .utils import cookieCart, cartData, guestOrder
import json
import traceback

def store(request):
	data = cartData(request)

	cartItems = data['cartItems']

	order = data['order']
	items = data['items']

	products = Product.objects.all()
	context = {'products':products, 'cartItems':cartItems}
	return render(request, 'store/store.html', context)


def cart(request):
    data = cartData(request)

    cartItems = data['cartItems']
    order = data['order']
    items = data['items']
        

    context = {'items':items, 'order':order, 'cartItems':cartItems}
    return render(request, 'store/cart.html', context)

def checkout(request):
	data = cartData(request)
	
	cartItems = data['cartItems']
	order = data['order']
	items = data['items']

	context = {'items':items, 'order':order, 'cartItems':cartItems}
	return render(request, 'store/checkout.html', context)



def updateItem(request):
    try:
        print("Request received")  # Debug print
        print("Request body:", request.body)  # Debug print
        
        data = json.loads(request.body)
        print("Parsed data:", data)  # Debug print
        
        productId = data['productId']
        action = data['action']
        variantId = data.get('variantId')  # Get variant ID if available
        designer_service = data.get('designer_service', False)  # Get designer service flag
        
        # Normalize variant ID - treat None, "null", "undefined" as None
        if variantId in [None, "null", "undefined", ""]:
            variantId = None
        
        print('Action:', action)
        print('Product:', productId)
        print('Variant:', variantId)
        print('Designer Service:', designer_service)
        
        # Get product information
        product = Product.objects.get(id=productId)
        variant = None
        if variantId:
            try:
                variant = ProductVariant.objects.get(id=variantId)
            except ProductVariant.DoesNotExist:
                print(f"❌ Variant with ID {variantId} not found")
                variant = None
        
        # Check if user is authenticated
        if request.user.is_authenticated:
            # Use the existing logic for authenticated users
            customer = request.user.customer
            order, created = Order.objects.get_or_create(customer=customer, complete=False)
            
            # Check if an order item with this product and variant already exists
            orderItem = OrderItem.objects.filter(
                order=order, 
                product=product,
                variant=variant
            ).first()
            
            if not orderItem:
                orderItem = OrderItem.objects.create(
                    order=order, 
                    product=product,
                    variant=variant,
                    quantity=0,
                    designer_service=designer_service
                )

            if action == 'add':
                orderItem.quantity = (orderItem.quantity + 1)
            elif action == 'remove':
                orderItem.quantity = (orderItem.quantity - 1)
            
            # Make sure we preserve the designer service flag when updating
            if designer_service:
                orderItem.designer_service = True
            
            orderItem.save()

            if orderItem.quantity <= 0:
                orderItem.delete()
                
            return JsonResponse({'status': 'success', 'message': 'Item was updated'})
        else:
            # Handle anonymous users with cookie cart
            print("🔎 Anonymous user, using cookie cart")
            
            # Get or create cart cookie
            cart = {}
            try:
                cart_cookie = request.COOKIES.get('cart')
                if cart_cookie:
                    cart = json.loads(cart_cookie)
            except json.JSONDecodeError:
                print("❌ Invalid cart cookie, creating new one")
                cart = {}
            
            # Create a unique key for this product+variant combination
            item_key = f"{productId}_{variantId}" if variantId else f"{productId}_null"
            
            # Update the cart based on the action
            if action == 'add':
                if item_key in cart:
                    cart[item_key]['quantity'] += 1
                else:
                    cart[item_key] = {
                        'quantity': 1,
                        'productId': productId,
                        'variantId': variantId,
                        'designer_service': designer_service
                    }
            elif action == 'remove':
                if item_key in cart:
                    cart[item_key]['quantity'] -= 1
                    if cart[item_key]['quantity'] <= 0:
                        del cart[item_key]
            
            print(f"🔎 Cart cookie being set: {cart}")
            
            # Return the response with the updated cookie
            response = JsonResponse({'status': 'success', 'message': 'Item was updated'})
            response.set_cookie('cart', json.dumps(cart), max_age=86400*7)  # Cookie expires in 7 days
            return response

    except Exception as e:
        print("Error:", str(e))  # Debug print
        print("Traceback:", traceback.format_exc())  # Full traceback
        return JsonResponse({
            'error': str(e),
            'traceback': traceback.format_exc()
        }, status=500)
        
        


# def updateItem(request):
#     try:
#         print("Request received")  # Debug print
#         print("Request body:", request.body)  # Debug print
        
#         data = json.loads(request.body)
#         print("Parsed data:", data)  # Debug print
        
#         productId = data['productId']
#         action = data['action']
#         variantId = data.get('variantId')  # Get variant ID if available
#         designer_service = data.get('designer_service', False)  # Get designer service flag
        
#         # Normalize variant ID - treat None, "null", "undefined" as None
#         if variantId in [None, "null", "undefined", ""]:
#             variantId = None
        
#         print('Action:', action)
#         print('Product:', productId)
#         print('Variant:', variantId)
#         print('Designer Service:', designer_service)
        
#         customer = request.user.customer
#         product = Product.objects.get(id=productId)
#         order, created = Order.objects.get_or_create(customer=customer, complete=False)
        
#         # Get or create order item with the correct variant
#         variant = None
#         if variantId:
#             try:
#                 variant = ProductVariant.objects.get(id=variantId)
#             except ProductVariant.DoesNotExist:
#                 print(f"❌ Variant with ID {variantId} not found")
#                 variant = None
        
#         # Check if an order item with this product and variant already exists
#         orderItem = OrderItem.objects.filter(
#             order=order, 
#             product=product,
#             variant=variant
#         ).first()
        
#         if not orderItem:
#             orderItem = OrderItem.objects.create(
#                 order=order, 
#                 product=product,
#                 variant=variant,
#                 quantity=0,
#                 designer_service=designer_service  # Set designer service when creating
#             )

#         if action == 'add':
#             orderItem.quantity = (orderItem.quantity + 1)
#         elif action == 'remove':
#             orderItem.quantity = (orderItem.quantity - 1)
        
#         # Make sure we preserve the designer service flag when updating
#         if designer_service:
#             orderItem.designer_service = True
        
#         orderItem.save()

#         if orderItem.quantity <= 0:
#             orderItem.delete()

#         return JsonResponse({'status': 'success', 'message': 'Item was updated'})
    
#     except Exception as e:
#         print("Error:", str(e))  # Debug print
#         print("Traceback:", traceback.format_exc())  # Full traceback
#         return JsonResponse({
#             'error': str(e),
#             'traceback': traceback.format_exc()
#         }, status=500)
        
        
        
def processOrder(request):
	transaction_id = datetime.datetime.now().timestamp()
	data = json.loads(request.body)

	if request.user.is_authenticated:
		customer = request.user.customer
		order, created = Order.objects.get_or_create(customer=customer, complete=False)
	else:
		customer, order = guestOrder(request, data)

	total = float(data['form']['total'])
	order.transaction_id = transaction_id

	if total == order.get_cart_total:
		order.complete = True
	order.save()

	if order.shipping == True:
		ShippingAddress.objects.create(
		customer=customer,
		order=order,
		address=data['shipping']['address'],
		city=data['shipping']['city'],
		state=data['shipping']['state'],
		zipcode=data['shipping']['zipcode'],
		)

	return JsonResponse('Payment submitted..', safe=False)




def clearCart(request):
    try:
        if request.method == 'POST':
            if request.user.is_authenticated:
                # Handle logged-in user
                customer = request.user.customer
                order, created = Order.objects.get_or_create(customer=customer, complete=False)
            else:
                # Handle guest user
                device_id = request.COOKIES.get('device')
                order, created = Order.objects.get_or_create(device=device_id, complete=False)
            
            # Delete all items in the cart
            order.orderitem_set.all().delete()
            
            return JsonResponse({'status': 'success', 'message': 'Cart cleared'})
        else:
            return JsonResponse({'status': 'error', 'message': 'Invalid request method'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})