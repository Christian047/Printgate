# cart.py (Handles Cart Logic)

import json  # Import JSON module for handling cart data stored as cookies
from .models import *  # Import all models (Product, Order, OrderItem, Customer)

def cookieCart(request):
    try:
        cart = json.loads(request.COOKIES.get('cart', '{}'))
        print("🔎 Cart cookie found:", cart)
    except Exception as e:
        print(f"❌ Cookie parsing error: {e}")
        cart = {}

    items = []
    order = {'get_cart_total': 0, 'get_cart_items': 0, 'shipping': False}
    cartItems = order['get_cart_items']

    for key in cart:
        try:
            if cart[key]['quantity'] > 0:
                cartItems += cart[key]['quantity']

                # ✅ Extract product_id correctly
                product_id = cart[key].get('productId')
                if not product_id:  # If productId isn't explicitly stored, get from key
                    product_id = key.split('_')[0] if '_' in key else key

                if not product_id.isdigit():  # Prevent errors if key is corrupted
                    print(f"⚠️ Invalid product ID in cart: {product_id}")
                    continue

                print(f"🔹 Processing product {product_id} with key {key}")

                product = Product.objects.get(id=product_id)

                # Handle variant
                variant = None
                variant_adjustment = 0
                variant_id = cart[key].get('variantId')

                print(f"➡️ Variant ID: {variant_id}")

                if variant_id:
                    try:
                        variant = ProductVariant.objects.get(id=variant_id)
                        variant_adjustment = variant.price_adjustment
                    except ProductVariant.DoesNotExist:
                        print(f"❌ Variant with ID {variant_id} not found")
                        variant_id = None  # Reset to avoid incorrect association

                unit_price = product.base_price + variant_adjustment
                total = unit_price * cart[key]['quantity']

                order['get_cart_total'] += total
                order['get_cart_items'] += cart[key]['quantity']

                item = {
                    'id': product.id,
                    'product': {
                        'id': product.id,
                        'name': product.name, 
                        'price': product.base_price,
                        'imageURL': product.imageURL
                    },
                    'quantity': cart[key]['quantity'],
                    'digital': product.digital,
                    'get_total': total,
                    'variant_id': variant_id,
                    'variant': variant,
                    'unit_price': unit_price,
                }
                items.append(item)

                if not product.digital:
                    order['shipping'] = True
        except Exception as e:
            print(f"❌ Error processing cart item {key}: {e}")
            import traceback
            print(traceback.format_exc())
    
    return {'cartItems': cartItems, 'order': order, 'items': items}

def cartData(request):
    """
    Retrieves cart data based on whether the user is logged in or a guest.
    Returns order, cart items, and total quantity.
    """

    if request.user.is_authenticated:
        # Get the logged-in customer's cart
        customer = request.user.customer  # Get the customer linked to the user
        order, created = Order.objects.get_or_create(customer=customer, complete=False)  # Get or create an open order
        items = order.orderitem_set.all()  # Retrieve all items in the order
        cartItems = order.get_cart_items  # Get the total number of items in the cart

    else:
        # Retrieve cart from cookies for guests
        cookieData = cookieCart(request)
        cartItems = cookieData['cartItems']
        order = cookieData['order']
        items = cookieData['items']

    return {'cartItems': cartItems, 'order': order, 'items': items}  # Return cart details

def guestOrder(request, data):
    name = data['form']['name']
    email = data['form']['email']
    
    cookieData = cookieCart(request)
    items = cookieData['items']
    
    customer, created = Customer.objects.get_or_create(
        email=email,
    )
    customer.name = name
    customer.save()
    
    order = Order.objects.create(
        customer=customer,
        complete=False,
    )
    
    for item in items:
        product = Product.objects.get(id=item['id'])
        variant = None
        
        # Get variant if available
        if item.get('variant_id'):
            try:
                variant = ProductVariant.objects.get(id=item['variant_id'])
            except ProductVariant.DoesNotExist:
                pass
        
        orderItem = OrderItem.objects.create(
            product=product,
            order=order,
            variant=variant,  # Associate variant with order item
            quantity=(item['quantity'] if item['quantity'] > 0 else -1 * item['quantity']),
        )
    
    return customer, order

# import json
# from .models import *

# def cookieCart(request):

# 	#Create empty cart for now for non-logged in user
# 	try:
# 		cart = json.loads(request.COOKIES['cart'])
# 	except:
# 		cart = {}
# 		print('CART:', cart)

# 	items = []
# 	order = {'get_cart_total':0, 'get_cart_items':0, 'shipping':False}
# 	cartItems = order['get_cart_items']

# 	for i in cart:
# 		#We use try block to prevent items in cart that may have been removed from causing error
# 		try:	
# 			if(cart[i]['quantity']>0): #items with negative quantity = lot of freebies  
# 				cartItems += cart[i]['quantity']

# 				product = Product.objects.get(id=i)
# 				total = (product.price * cart[i]['quantity'])

# 				order['get_cart_total'] += total
# 				order['get_cart_items'] += cart[i]['quantity']

# 				item = {
# 				'id':product.id,
# 				'product':{'id':product.id,'name':product.name, 'price':product.price, 
# 				'imageURL':product.imageURL}, 'quantity':cart[i]['quantity'],
# 				'digital':product.digital,'get_total':total,
# 				}
# 				items.append(item)

# 				if product.digital == False:
# 					order['shipping'] = True
# 		except:
# 			pass
			
# 	return {'cartItems':cartItems ,'order':order, 'items':items}

# def cartData(request):
# 	if request.user.is_authenticated:
# 		customer = request.user.customer
# 		order, created = Order.objects.get_or_create(customer=customer, complete=False)
# 		items = order.orderitem_set.all()
# 		cartItems = order.get_cart_items
# 	else:
# 		cookieData = cookieCart(request)
# 		cartItems = cookieData['cartItems']
# 		order = cookieData['order']
# 		items = cookieData['items']

# 	return {'cartItems':cartItems ,'order':order, 'items':items}

	
# def guestOrder(request, data):
# 	name = data['form']['name']
# 	email = data['form']['email']

# 	cookieData = cookieCart(request)
# 	items = cookieData['items']

# 	customer, created = Customer.objects.get_or_create(
# 			email=email,
# 			)
# 	customer.name = name
# 	customer.save()

# 	order = Order.objects.create(
# 		customer=customer,
# 		complete=False,
# 		)

# 	for item in items:
# 		product = Product.objects.get(id=item['id'])
# 		orderItem = OrderItem.objects.create(
# 			product=product,
# 			order=order,
# 			quantity=(item['quantity'] if item['quantity']>0 else -1*item['quantity']), # negative quantity = freebies
# 		)
# 	return customer, order

