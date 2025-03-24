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

                # Extract product ID and variant ID from the cart
                product_id = cart[key].get('productId')
                variant_id = cart[key].get('variantId')
                
                # Normalize variant ID - treat None, "null", "undefined" as None
                if variant_id in [None, "null", "undefined", ""]:
                    variant_id = None
                
                # Fallback to key parsing only if necessary
                if not product_id:
                    parts = key.split('_')
                    product_id = parts[0]
                    if len(parts) > 1 and parts[1] not in ["null", "undefined", ""]:
                        variant_id = parts[1]
                    else:
                        variant_id = None
                
                # Make sure product_id is valid
                if not str(product_id).isdigit():
                    print(f"⚠️ Invalid product ID in cart: {product_id}")
                    continue

                print(f"🔹 Processing product {product_id} with variant {variant_id}, key {key}")

                product = Product.objects.get(id=product_id)

                # Handle variant
                variant = None
                variant_adjustment = 0
                
                if variant_id:
                    try:
                        variant = ProductVariant.objects.get(id=variant_id)
                        variant_adjustment = variant.price_adjustment
                        print(f"✅ Found variant: {variant.name} with adjustment {variant_adjustment}")
                    except ProductVariant.DoesNotExist:
                        print(f"❌ Variant with ID {variant_id} not found")
                        variant_id = None  # Reset to avoid incorrect association

                # Calculate the correct price including variant adjustment
                unit_price = product.base_price + variant_adjustment
                total = unit_price * cart[key]['quantity']

                order['get_cart_total'] += total
                order['get_cart_items'] += cart[key]['quantity']

                item = {
                    'id': product.id,
                    'product': {
                        'id': product.id,
                        'name': product.title, 
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
        
        # Get variant if available - make sure to use the correct variant_id
        if item.get('variant_id'):
            try:
                variant = ProductVariant.objects.get(id=item['variant_id'])
                print(f"✅ Adding variant {variant.name} to order for product {product.title}")
            except ProductVariant.DoesNotExist:
                print(f"❌ Variant with ID {item['variant_id']} not found during checkout")
        
        orderItem = OrderItem.objects.create(
            product=product,
            order=order,
            variant=variant,  # Associate variant with order item
            quantity=item['quantity'],
        )
    
    return customer, order
