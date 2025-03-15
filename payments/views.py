# Import necessary Django modules and functions
from django.shortcuts import render, redirect  # For rendering templates and redirecting users
from .models import Payment, UserWallet  # Import custom Payment and UserWallet models
from django.conf import settings  # To access Django settings (like PAYSTACK_PUBLIC_KEY)
from django.contrib import messages  # For displaying flash messages to users
import json  # For handling JSON data
from store.utils import *
from base.models import *  # Import all models from base app




def initiate_payment(request):

    data = cartData(request)
	
    cartItems = data['cartItems']
    order = data['order']
    items = data['items']
    if len(items) == 0:
        messages.error(request, "Your cart is empty")
        return redirect('cart')

    if request.method == "POST":
        if isinstance(order, dict):
            amount = order['get_cart_total']  # Dictionary access
        else:
            amount = order.get_cart_total  # Object property access
            
        email = request.POST['email']  # Get email from POST data

        try:
            # Create new payment record in database
            payment = Payment.objects.create(
                   amount=amount,
                   email=email,
                   payment_order=order, 
                   session_id=request.session.session_key 
                #    or uuid.uuid4().hex       
           )
            
            context = {
                'payment': payment,
                'paystack_pub_key': settings.PAYSTACK_PUBLIC_KEY,
                'amount_value': payment.amount_value(),
                'order': order,
                'items': items,  # Add items to context
                'cartItems':cartItems
            }
            response = render(request, 'make_payment.html', context)
            response.set_cookie('payment_ref', payment.ref, httponly=True)
            return response

        except Exception as e:
            # Handle any errors during payment creation
            messages.error(request, f"An error occurred: {str(e)}")
            return redirect('cart')

    # If not POST, render initial payment form
    return render(request, 'payment.html', {'order': order, 'items': items})





def verify_payment(request, ref):
    print("\n========== PAYMENT VERIFICATION DEBUG ==========")
    print(f"REQUEST PATH: {request.path}")
    print(f"PAYMENT REF: {ref}")
    print(f"USER: {request.user.username if request.user.is_authenticated else 'Anonymous'}")
    
    # Debug all cookies
    print("\nALL COOKIES:")
    for key, value in request.COOKIES.items():
        print(f"  {key}: {value[:50]}{'...' if len(value) > 50 else ''}")
    
    # Debug all session data
    print("\nALL SESSION DATA:")
    for key, value in request.session.items():
        value_str = str(value)
        print(f"  {key}: {value_str[:50]}{'...' if len(value_str) > 50 else ''}")
    
    # Get payment reference from cookie
    payment_ref = request.COOKIES.get('payment_ref')
    print(f"\nRetrieved payment_ref from cookie: {payment_ref}")

    # Validate payment reference
    if not payment_ref or payment_ref != ref:
        print("ERROR: Invalid payment reference!")
        print(f"Cookie payment_ref: {payment_ref}")
        print(f"URL ref parameter: {ref}")
        messages.error(request, "Invalid payment reference")
        return redirect('cart')

    try:
        # Get payment object and verify it
        print(f"\nFetching payment object for ref: {ref}")
        payment = Payment.objects.get(ref=ref)
        print(f"Payment object details:")
        print(f"  ID: {payment.id}")
        print(f"  Amount: {payment.amount}")
        print(f"  Email: {payment.email}")
        print(f"  Verified: {payment.verified}")
        print(f"  Date Created: {payment.date_created}")

        # Get the pending order ID from cookie or session
        pending_order_id = request.COOKIES.get('pending_order_id')
        session_pending_order_id = request.session.get('pending_order_id')
        
        print(f"\nPending order ID from cookie: {pending_order_id}")
        print(f"Pending order ID from session: {session_pending_order_id}")
        
        # Use whichever is available
        pending_order_id = pending_order_id or session_pending_order_id
        print(f"Final pending order ID being used: {pending_order_id}")
        
        if not pending_order_id:
            print("ERROR: No pending order ID found in cookies or session.")
            
            # Check if there are any recent pending orders for this user
            if request.user.is_authenticated:
                try:
                    recent_pending_orders = PendingOrder.objects.filter(
                        customer=request.user.customer,
                        complete=False
                    ).order_by('-date_ordered')[:5]
                    
                    print(f"\nFound {recent_pending_orders.count()} recent pending orders for user:")
                    for order in recent_pending_orders:
                        print(f"  ID: {order.id}, Date: {order.date_ordered}, Product: {order.product.title if order.product else 'None'}")
                    
                    if recent_pending_orders.exists():
                        print("RECOVERY ATTEMPT: Using most recent pending order")
                        pending_order_id = recent_pending_orders.first().id
                        print(f"Recovery pending order ID: {pending_order_id}")
                except Exception as e:
                    print(f"Error checking recent orders: {str(e)}")
            
            # If still no pending order ID
            if not pending_order_id:
                print("ABORT: Final attempt to find pending order failed")
                messages.error(request, "No pending order found")
                return redirect('cart')

        # Check if pending order exists before verifying payment
        try:
            pending_order = PendingOrder.objects.get(id=pending_order_id)
            print(f"\nPre-verification check: Found pending order {pending_order_id}")
            print(f"  Customer: {pending_order.customer.name if pending_order.customer else 'None'}")
            print(f"  Product: {pending_order.product.title if pending_order.product else 'None'}")
            print(f"  Complete: {pending_order.complete}")
            print(f"  Total Price: {pending_order.total_price}")
        except PendingOrder.DoesNotExist:
            print(f"ERROR: Pending order with ID {pending_order_id} does not exist in database!")
            messages.error(request, f"Pending order #{pending_order_id} not found")
            return redirect('cart')

        verified = payment.verify_payment()
        print(f"\nPayment verification result: {verified}")

        if verified:
            try:
                # Get the pending order again (to be sure)
                print(f"\nFetching pending order with ID: {pending_order_id}")
                pending_order = PendingOrder.objects.get(id=pending_order_id)
                print(f"Pending order retrieved successfully:")
                print(f"  ID: {pending_order.id}")
                print(f"  Date Ordered: {pending_order.date_ordered}")
                print(f"  Complete Flag: {pending_order.complete}")
                
                # Check specifications
                specs = pending_order.specifications.all()
                print(f"  Specifications count: {specs.count()}")
                for i, spec in enumerate(specs):
                    print(f"    Spec {i+1}: {spec.field_name} = {spec.field_value[:30] if spec.field_value else 'None'}")
                
                # Set transaction ID on pending order
                pending_order.transaction_id = payment.ref
                pending_order.save()
                print(f"Updated pending order with transaction ID: {payment.ref}")
                
                # Convert pending order to confirmed order
                print("\nCONVERTING: Pending order to confirmed order...")
                order = pending_order.convert_to_order()
                print(f"Confirmed order created with ID: {order.id}")
                
                # Set order as complete and save transaction ID
                order.complete = True
                order.transaction_id = payment.ref
                order.save()
                print("Confirmed order marked as complete and saved with transaction ID")
                
                # Copy specifications from pending order to confirmed order
                print("\nCopying specifications from pending order...")
                specs_copied = 0
                for pending_spec in pending_order.specifications.all():
                    # Create new OrderSpecification for the confirmed order
                    order_spec = OrderSpecification(
                        order=order,
                        field_name=pending_spec.field_name,
                        field_value=pending_spec.field_value
                    )
                    
                    # Copy file if exists
                    if pending_spec.field_file:
                        print(f"  Copying file for spec '{pending_spec.field_name}'")
                        from django.core.files.base import ContentFile
                        order_spec.field_file.save(
                            pending_spec.field_file.name,
                            ContentFile(pending_spec.field_file.read()),
                            save=True
                        )
                    
                    order_spec.save()
                    specs_copied += 1
                
                print(f"Successfully copied {specs_copied} specifications to confirmed order")
                
                # Mark pending order as complete
                pending_order.complete = True
                pending_order.save()
                print("Pending order marked as complete")
                
                # Clear cookies and show success page
                print("\nRendering success page...")
                response = render(request, "success.html", {
                    'message': "Payment verified successfully!",
                    'order': order
                })
                
                # Clear cookies
                cookies_to_delete = ['cart', 'payment_ref', 'pending_order_id', 'shipping_info']
                for cookie in cookies_to_delete:
                    if cookie in request.COOKIES:
                        response.delete_cookie(cookie)
                        print(f"Deleted cookie: {cookie}")
                
                # Clear session data if used
                session_keys_to_delete = ['pending_order_id', 'cart']
                for key in session_keys_to_delete:
                    if key in request.session:
                        del request.session[key]
                        print(f"Deleted session key: {key}")
                
                request.session.modified = True
                print("Session marked as modified")
                
                print("DEBUG COMPLETE: Returning success response.")
                print("==========================================\n")
                return response
                
            except PendingOrder.DoesNotExist:
                print(f"ERROR: Pending order with ID {pending_order_id} suddenly not found!")
                print("This suggests the order was deleted or modified during processing")
                messages.error(request, "Pending order not found")
                return redirect('cart')

        else:
            print("\nERROR: Payment verification failed.")
            messages.error(request, "Payment verification failed")
            return render(request, "failure.html")

    except Payment.DoesNotExist:
        print(f"\nERROR: Payment record with ref {ref} not found.")
        messages.error(request, "Payment not found")
        return redirect('cart')

    except Exception as e:
        print(f"\nCRITICAL ERROR: An unexpected exception occurred")
        print(f"Exception type: {type(e).__name__}")
        print(f"Exception message: {str(e)}")
        print(f"Exception traceback:")
        import traceback
        traceback.print_exc()
        messages.error(request, f"An error occurred: {str(e)}")
        return redirect('cart')








# def verify_payment(request, ref):


#     # Get payment reference from cookie
#     payment_ref = request.COOKIES.get('payment_ref')
#     print(f"Retrieved payment_ref: {payment_ref}")

#     # Validate payment reference
#     if not payment_ref or payment_ref != ref:
#         print("Invalid payment reference!")
#         messages.error(request, "Invalid payment reference")
#         return redirect('cart')

#     try:
#         # Get payment object and verify it
#         print(f"Fetching payment object for ref: {ref}")
#         payment = Payment.objects.get(ref=ref)
#         print("Payment object retrieved successfully.")

#         # Get the pending order ID from cookie or session
#         pending_order_id = request.COOKIES.get('pending_order_id') or request.session.get('pending_order_id')
#         print(f"Pending order ID: {pending_order_id}")
        
#         if not pending_order_id:
#             print("No pending order ID found.")
#             messages.error(request, "No pending order found")
#             return redirect('cart')

#         verified = payment.verify_payment()
#         print(f"Payment verification result: {verified}")

#         if verified:
#             try:
#                 # Get the pending order
#                 print(f"Fetching pending order with ID: {pending_order_id}")
#                 pending_order = PendingOrder.objects.get(id=pending_order_id)
#                 print("Pending order retrieved successfully.")
                
#                 # Set transaction ID on pending order
#                 pending_order.transaction_id = payment.ref
#                 pending_order.save()
                
#                 # Convert pending order to confirmed order
#                 print("Converting pending order to confirmed order...")
#                 order = pending_order.convert_to_order()
#                 print(f"Order created with ID: {order.id}")
                
#                 # Set order as complete and save transaction ID
#                 order.complete = True
#                 order.transaction_id = payment.ref
#                 order.save()
#                 print("Order marked as complete and saved.")
                
#                 # Copy specifications from pending order to confirmed order
#                 print("Copying specifications from pending order...")
#                 for pending_spec in pending_order.specifications.all():
#                     # Create new OrderSpecification for the confirmed order
#                     order_spec = OrderSpecification(
#                         order=order,
#                         field_name=pending_spec.field_name,
#                         field_value=pending_spec.field_value
#                     )
                    
#                     # Copy file if exists
#                     if pending_spec.field_file:
#                         from django.core.files.base import ContentFile
#                         order_spec.field_file.save(
#                             pending_spec.field_file.name,
#                             ContentFile(pending_spec.field_file.read()),
#                             save=True
#                         )
                    
#                     order_spec.save()
#                     print(f"Specification '{pending_spec.field_name}' copied successfully.")
                
#                 # Mark pending order as complete
#                 pending_order.complete = True
#                 pending_order.save()
#                 print("Pending order marked as complete.")
                
#                 # Clear cookies and show success page
#                 print("Rendering success page...")
#                 response = render(request, "success.html", {
#                     'message': "Payment verified successfully!",
#                     'order': order
#                 })
                
#                 # Clear cookies
#                 response.delete_cookie('cart')
#                 response.delete_cookie('payment_ref')
#                 response.delete_cookie('pending_order_id')
#                 if request.COOKIES.get('shipping_info'):
#                     response.delete_cookie('shipping_info')
                
#                 # Clear session data if used
#                 if 'pending_order_id' in request.session:
#                     del request.session['pending_order_id']
#                     request.session.modified = True
                
#                 print("Cookies and session data cleared, returning success response.")
#                 return response
                
#             except PendingOrder.DoesNotExist:
#                 print("Pending order not found.")
#                 messages.error(request, "Pending order not found")
#                 return redirect('cart')

#         else:
#             print("Payment verification failed.")
#             messages.error(request, "Payment verification failed")
#             return render(request, "failure.html")

#     except Payment.DoesNotExist:
#         print("Payment record not found.")
#         messages.error(request, "Payment not found")
#         return redirect('cart')

#     except Exception as e:
#         print(f"An error occurred: {str(e)}")
#         messages.error(request, f"An error occurred: {str(e)}")
#         return redirect('cart')


# def verify_payment(request, ref):
#     print("Starting verify_payment function...")

#     # Get payment reference from cookie
#     payment_ref = request.COOKIES.get('payment_ref')
#     print(f"Retrieved payment_ref: {payment_ref}")

#     # Validate payment reference
#     if not payment_ref or payment_ref != ref:
#         print("Invalid payment reference!")
#         messages.error(request, "Invalid payment reference")
#         return redirect('cart')

#     try:
#         # Get payment object and verify it
#         print(f"Fetching payment object for ref: {ref}")
#         payment = Payment.objects.get(ref=ref)
#         print("Payment object retrieved successfully.")

#         verified = payment.verify_payment()
#         print(f"Payment verification result: {verified}")

#         if verified:
#             # Use the same cartData function you're using elsewhere
#             print("Fetching cart data...")
#             data = cartData(request)
#             items = data['items']
#             print(f"Cart data retrieved. Items count: {len(items)}")

#             if request.user.is_authenticated:
#                 print("User is authenticated, creating order...")
#                 customer = request.user.customer
#                 order = Order.objects.create(
#                     customer=customer,
#                     complete=True,
#                     transaction_id=payment.ref,
#                 )
#                 print(f"Order created with ID: {order.id}")

#                 # Create order items from cart items
#                 for idx, item in enumerate(items):
#                     print(f"Processing item {idx + 1}...")

#                     if isinstance(item, dict):  # Guest user case
#                         product = Product.objects.get(id=item['id'])
#                         quantity = item['quantity']
#                     else:  # Logged-in user case
#                         product = item.product
#                         quantity = item.quantity

#                     OrderItem.objects.create(
#                         product=product,
#                         order=order,
#                         quantity=quantity,
#                     )
#                     print(f"OrderItem created for product ID: {product.id}")
                
#                 # Clear user's cart in database (important addition)
#                 print("Clearing user's cart in database...")
#                 old_cart_items = OrderItem.objects.filter(
#                     order__customer=customer, 
#                     order__complete=False
#                 )
#                 if old_cart_items.exists():
#                     # Get the incomplete order(s) and delete
#                     incomplete_orders = Order.objects.filter(
#                         customer=customer,
#                         complete=False
#                     )
#                     incomplete_orders.delete()
#                     print("Database cart cleared successfully.")

#             else:
#                 print("User is a guest, processing guest order...")
#                 shipping_info = json.loads(request.COOKIES.get('shipping_info', '{}'))
#                 print(f"Shipping info retrieved: {shipping_info}")

#                 # Prepare data in the format expected by guestOrder
#                 form_data = {
#                     'form': {
#                         'name': shipping_info.get('name', 'Guest User'),
#                         'email': payment.email  # Use email from payment
#                     },
#                     'shipping': shipping_info
#                 }

#                 print("Calling guestOrder function...")
#                 customer, order = guestOrder(request, form_data)
#                 print(f"Guest order created. Order ID: {order.id}")

#                 order.complete = True
#                 order.transaction_id = payment.ref
#                 order.save()
#                 print("Guest order marked as complete and saved.")

#             # Clear cookies and show success page
#             print("Rendering success page...")
#             response = render(request, "success.html", {
#                 'message': "Payment verified successfully!",
#                 'order': order
#             })
            
#             # Always clear cookies for both user types
#             response.delete_cookie('cart')
#             response.delete_cookie('payment_ref')
#             response.delete_cookie('shipping_info')
#             print("Cookies cleared, returning success response.")
#             return response

#         else:
#             print("Payment verification failed.")
#             messages.error(request, "Payment verification failed")
#             return render(request, "failure.html")

#     except Payment.DoesNotExist:
#         print("Payment record not found.")
#         messages.error(request, "Payment not found")
#         return redirect('cart')

#     except Exception as e:
#         print(f"An error occurred: {str(e)}")
#         messages.error(request, f"An error occurred: {str(e)}")
#         return redirect('cart')








# from django.shortcuts import render, redirect
# from .models import Payment, UserWallet
# from django.conf import settings
# from django.contrib import messages
# from base.models import Registration


# def initiate_payment(request):
#     registration_id = request.session.get('registration_id')
#     if not registration_id:
#         messages.error(request, "Session expired. Please register again.")
#         return redirect('prospectus')

#     registration = Registration.objects.filter(id=registration_id).first()
#     if not registration:
#         messages.error(request, "Registration not found for this session.")
#         return redirect('prospectus')

#     course = registration.course

#     if request.method == "POST":
#         amount = request.POST['amount']
#         email = request.POST['email']

#         pk = settings.PAYSTACK_PUBLIC_KEY
#         session_id = request.session.session_key

#         try:
#             # Create the payment record
#             payment = Payment.objects.create(
#                 amount=amount,
#                 email=email,
#                 session_id=session_id,
#                 registration=registration  # Associate payment with registration
#             )
#             payment.save()
#         except Exception as e:
#             messages.error(request, f"An error occurred while creating the payment: {str(e)}")
#             return redirect('initiate_payment')

#         context = {
#             'payment': payment,
#             'field_values': request.POST,
#             'paystack_pub_key': pk,
#             'amount_value': payment.amount_value(),
#             'course_price': course.price,
#             'course_name': course.name,
          
            
#         }
#         return render(request, 'make_payment.html', context)

#     # Render the payment page for GET requests
#     return render(request, 'payment.html', {'course_price': course.price, 'course_name': course.name})

# def verify_payment(request, ref):
# 	payment = Payment.objects.get(ref=ref)
# 	verified = payment.verify_payment()

# 	if verified:
# 		user_wallet = UserWallet.objects.get(user=request.user)
# 		user_wallet.balance += payment.amount
# 		user_wallet.save()
# 		print(request.user.username, " funded wallet successfully")
# 		return render(request, "success.html")
# 	return render(request, "success.html")



# def verify_payment(request, ref):
#     session_id = request.session.session_key

#     try:
#         payment = Payment.objects.get(ref=ref, session_id=session_id)
#     except Payment.DoesNotExist:
#         messages.error(request, "Payment not found or does not match this session.")
#         return render(request, "payments/failure.html")

#     verified = payment.verify_payment()

#     if verified:
#             # Payment was successful
#             messages.success(request, "Payment successful, registration complete.")
#             return render(request, "success.html", {'message': "Payment verified successfully!"})
    
#     return render(request, "failure.html", {'message': "Payment verification failed."})


# # Geting The session from the main views

# # def prospectus(request):
# #     all_courses = Courses.objects.all()
# #     if request.method == 'POST':
# #         # Create form instance with POST data
# #         form = RegistrationForm(request.POST)
# #         # Check if the form is valid
# #         if form.is_valid():
# #             try:
# #                 # Save the registration without committing to the database
# #                 registration = form.save(commit=False)
                
# #                 # Generate and set the secret code
# #                 registration.secret_code = generate_secret_code()
                
# #                 # Save the registration to the database
# #                 registration.save()
                
# #                 # Store the registration ID in the session
# #                 request.session['registration_id'] = registration.id

# #                 # Redirect to the success page
# #                 return redirect('success')
# #             except Exception as e:

# #                 messages.error(request, f"Registration failed: {str(e)}")
# #         else:
# #             for field, errors in form.errors.items():
# #                 for error in errors:
# #                     messages.error(request, f"{field.capitalize()}: {error}")
# #     else:
# #         form = RegistrationForm()
        
        
    
# #     # Render the prospectus page with the form
# #     return render(request, 'propestus.html', {'form': form, 'all_courses': all_courses})




