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
        # Extract these variables at the beginning to ensure they're always defined
        email = request.POST.get('email', '')
        firstname = request.POST.get('firstname', '')
        lastname = request.POST.get('lastname', '')

        try:
            if isinstance(order, dict):
                # For anonymous users, create an actual Order object first
                customer, real_order = guestOrder(request, {
                    'form': {
                        'name': f"{firstname} {lastname}".strip() or 'Guest User',
                        'email': email,
                        'firstname': firstname,
                        'lastname': lastname
                    }
                })
                
                # Now use the real Order object
                amount = real_order.get_cart_total
                order_to_use = real_order
                
                # Store order ID in session for verification process
                request.session['pending_order_id'] = real_order.id
                request.session.modified = True
                print(f"Stored order ID {real_order.id} in session")
            else:
                # For logged-in users, use the existing Order object
                amount = order.get_cart_total
                order_to_use = order

            # Create new payment record in database with the proper Order object
            payment = Payment.objects.create(
                amount=amount,
                email=email,
                firstname=firstname,
                lastname=lastname,
                payment_order=order_to_use,
                session_id=request.session.session_key 
            )
            
            print(f"Payment created: {payment}, Linked Order: {payment.payment_order}")
            
            context = {
                'payment': payment,
                'paystack_pub_key': settings.PAYSTACK_PUBLIC_KEY,
                'amount_value': payment.amount_value(),
                'order': order_to_use,
                'items': items,
                'cartItems': cartItems
            }
            response = render(request, 'make_payment.html', context)
            response.set_cookie('payment_ref', payment.ref, httponly=True)
            
            # For anonymous users, also store order ID in cookie as backup
            if isinstance(order, dict):
                response.set_cookie('pending_order_id', str(order_to_use.id), max_age=86400)
            
            return response

        except Exception as e:
            # Handle any errors during payment creation
            messages.error(request, f"An error occurred: {str(e)}")
            return redirect('cart')

    # If not POST, render initial payment form
    return render(request, 'payment.html', {'order': order, 'items': items})




# def verify_payment(request, ref):
#     print("\n========== PAYMENT VERIFICATION DEBUG ==========")
#     print(f"REQUEST PATH: {request.path}")
#     print(f"PAYMENT REF: {ref}")
#     print(f"USER: {request.user.username if request.user.is_authenticated else 'Anonymous'}")
    
#     # Debug all cookies
#     print("\nALL COOKIES:")
#     for key, value in request.COOKIES.items():
#         print(f"  {key}: {value[:50]}{'...' if len(value) > 50 else ''}")
    
#     # Debug all session data
#     print("\nALL SESSION DATA:")
#     for key, value in request.session.items():
#         value_str = str(value)
#         print(f"  {key}: {value_str[:50]}{'...' if len(value_str) > 50 else ''}")
    
#     # Get payment reference from cookie
#     payment_ref = request.COOKIES.get('payment_ref')
#     print(f"\nRetrieved payment_ref from cookie: {payment_ref}")

#     # Validate payment reference
#     if not payment_ref or payment_ref != ref:
#         print("ERROR: Invalid payment reference!")
#         print(f"Cookie payment_ref: {payment_ref}")
#         print(f"URL ref parameter: {ref}")
#         messages.error(request, "Invalid payment reference")
#         return redirect('cart')

#     try:
#         # Get payment object and verify it
#         print(f"\nFetching payment object for ref: {ref}")
#         payment = Payment.objects.get(ref=ref)
#         print(f"Payment object details:")
#         print(f"  ID: {payment.id}")
#         print(f"  Amount: {payment.amount}")
#         print(f"  Email: {payment.email}")
#         print(f"  Verified: {payment.verified}")
#         print(f"  Date Created: {payment.date_created}")

#         # Get the pending order ID from cookie or session
#         pending_order_id = request.COOKIES.get('pending_order_id')
#         session_pending_order_id = request.session.get('pending_order_id')
        
#         print(f"\nPending order ID from cookie: {pending_order_id}")
#         print(f"Pending order ID from session: {session_pending_order_id}")
        
#         # Use whichever is available
#         pending_order_id = pending_order_id or session_pending_order_id
#         print(f"Final pending order ID being used: {pending_order_id}")
        
#         if not pending_order_id:
#             print("ERROR: No pending order ID found in cookies or session.")
            
#             # Check if there are any recent pending orders for this user
#             if request.user.is_authenticated:
#                 try:
#                     recent_pending_orders = PendingOrder.objects.filter(
#                         customer=request.user.customer,
#                         complete=False
#                     ).order_by('-date_ordered')[:5]
                    
#                     print(f"\nFound {recent_pending_orders.count()} recent pending orders for user:")
#                     for order in recent_pending_orders:
#                         print(f"  ID: {order.id}, Date: {order.date_ordered}, Product: {order.product.title if order.product else 'None'}")
                    
#                     if recent_pending_orders.exists():
#                         print("RECOVERY ATTEMPT: Using most recent pending order")
#                         pending_order_id = recent_pending_orders.first().id
#                         print(f"Recovery pending order ID: {pending_order_id}")
#                 except Exception as e:
#                     print(f"Error checking recent orders: {str(e)}")
            
#             # If still no pending order ID
#             if not pending_order_id:
#                 print("ABORT: Final attempt to find pending order failed")
#                 messages.error(request, "No pending order found")
#                 return redirect('cart')

#         # Check if pending order exists before verifying payment
#                 # In verify_payment function, replace this part:

#         # With this code:
#         try:
#             pending_order = PendingOrder.objects.get(id=pending_order_id)
#             print(f"\nPre-verification check: Found pending order {pending_order_id}")
#             # ... continue with your existing pending order code ...
#         except PendingOrder.DoesNotExist:
#             print(f"Pending order with ID {pending_order_id} not found, checking Order table...")
#             try:
#                 # Check if it exists in the Order table instead
#                 order = Order.objects.get(id=pending_order_id)
#                 print(f"\nFound order in Order table: {order.id}")
#                 print(f"  Customer: {order.customer.name if order.customer else 'None'}")
#                 print(f"  Complete: {order.complete}")
                
#                 # Verify the payment
#                 verified = payment.verify_payment()
#                 print(f"\nPayment verification result: {verified}")
                
#                 if verified:
#                     # Update the order
#                     order.transaction_id = payment.ref
#                     order.complete = True
#                     order.save()
#                     print(f"Updated order with transaction ID: {payment.ref}")
                    
#                     # For logged-in users, mark all their incomplete orders as complete
#                     if request.user.is_authenticated:
#                         updated_count = Order.objects.filter(
#                             customer=request.user.customer, 
#                             complete=False
#                         ).update(complete=True)
#                         print(f"Marked {updated_count} additional incomplete orders as complete")
                    
#                     # Clear cookies and show success page
#                     print("\nRendering success page...")
#                     response = render(request, "success.html", {
#                         'message': "Payment verified successfully!",
#                         'order': order
#                     })
                    
#                     # Clear cookies
#                     cookies_to_delete = ['cart', 'payment_ref', 'pending_order_id', 'shipping_info']
#                     for cookie in cookies_to_delete:
#                         if cookie in request.COOKIES:
#                             response.delete_cookie(cookie)
#                             print(f"Deleted cookie: {cookie}")
                    
#                     # Clear session data
#                     session_keys_to_delete = ['pending_order_id', 'cart']
#                     for key in session_keys_to_delete:
#                         if key in request.session:
#                             del request.session[key]
#                             print(f"Deleted session key: {key}")
                    
#                     request.session.modified = True
#                     print("Session marked as modified")
                    
#                     print("DEBUG COMPLETE: Returning success response.")
#                     print("==========================================\n")
#                     return response
                    
#                 else:
#                     print("\nERROR: Payment verification failed.")
#                     messages.error(request, "Payment verification failed")
#                     return render(request, "failure.html")
                    
#             except Order.DoesNotExist:
#                 print(f"ERROR: Order with ID {pending_order_id} does not exist in either table!")
#                 messages.error(request, f"Order #{pending_order_id} not found")
#                 return redirect('cart')

#         verified = payment.verify_payment()
#         print(f"\nPayment verification result: {verified}")

#         if verified:
#             try:
#                 # Get the pending order again (to be sure)
#                 print(f"\nFetching pending order with ID: {pending_order_id}")
#                 pending_order = PendingOrder.objects.get(id=pending_order_id)
#                 print(f"Pending order retrieved successfully:")
#                 print(f"  ID: {pending_order.id}")
#                 print(f"  Date Ordered: {pending_order.date_ordered}")
#                 print(f"  Complete Flag: {pending_order.complete}")
                
#                 # Check specifications
#                 specs = pending_order.specifications.all()
#                 print(f"  Specifications count: {specs.count()}")
#                 for i, spec in enumerate(specs):
#                     print(f"    Spec {i+1}: {spec.field_name} = {spec.field_value[:30] if spec.field_value else 'None'}")
                
#                 # Set transaction ID on pending order
#                 pending_order.transaction_id = payment.ref
#                 pending_order.save()
#                 print(f"Updated pending order with transaction ID: {payment.ref}")
                
#                 # Convert pending order to confirmed order
#                 print("\nCONVERTING: Pending order to confirmed order...")
#                 order = pending_order.convert_to_order()
                
#                 # NEW CODE: Link the order back to the pending order
#                 order.pending_order = pending_order
#                 order.save()
#                 print(f"Set foreign key link: Order {order.id} -> PendingOrder {pending_order.id}")
                
#                 print(f"Confirmed order created with ID: {order.id}")
                
#                 # Set order as complete and save transaction ID
#                 order.complete = True
#                 order.transaction_id = payment.ref
#                 order.save()
#                 print("Confirmed order marked as complete and saved with transaction ID")
                
                
#                 # Copy specifications from pending order to confirmed order
#                 print("\nCopying specifications from pending order...")
#                 specs_copied = 0
#                 for pending_spec in pending_order.specifications.all():
#                     # Create new OrderSpecification for the confirmed order
#                     order_spec = OrderSpecification(
#                         order=order,
#                         field_name=pending_spec.field_name,
#                         field_value=pending_spec.field_value
#                     )
                    
#                     # Copy file if exists
#                     if pending_spec.field_file:
#                         print(f"  Copying file for spec '{pending_spec.field_name}'")
#                         from django.core.files.base import ContentFile
#                         order_spec.field_file.save(
#                             pending_spec.field_file.name,
#                             ContentFile(pending_spec.field_file.read()),
#                             save=True
#                         )
                    
#                     order_spec.save()
#                     specs_copied += 1
                
#                 print(f"Successfully copied {specs_copied} specifications to confirmed order")
                
#                 # Mark pending order as complete
#                 pending_order.complete = True
#                 pending_order.save()
#                 print("Pending order marked as complete")
                
#                 # For logged-in users, mark all their incomplete orders as complete
#                 if request.user.is_authenticated:
#                     # Find any other incomplete orders for this customer and mark them complete
#                     updated_count = Order.objects.filter(
#                         customer=request.user.customer, 
#                         complete=False
#                     ).update(complete=True)
#                     print(f"Marked {updated_count} additional incomplete orders as complete for user {request.user.username}")
                
#                 # Clear cookies and show success page
#                 print("\nRendering success page...")
#                 response = render(request, "success.html", {
#                     'message': "Payment verified successfully!",
#                     'order': order
#                 })
                
#                 # Clear cookies
#                 cookies_to_delete = ['cart', 'payment_ref', 'pending_order_id', 'shipping_info']
#                 for cookie in cookies_to_delete:
#                     if cookie in request.COOKIES:
#                         response.delete_cookie(cookie)
#                         print(f"Deleted cookie: {cookie}")
                
#                 # Clear session data if used
#                 session_keys_to_delete = ['pending_order_id', 'cart']
#                 for key in session_keys_to_delete:
#                     if key in request.session:
#                         del request.session[key]
#                         print(f"Deleted session key: {key}")
                
#                 request.session.modified = True
#                 print("Session marked as modified")
                
#                 print("DEBUG COMPLETE: Returning success response.")
#                 print("==========================================\n")
#                 return response
                
#             except PendingOrder.DoesNotExist:
#                 print(f"ERROR: Pending order with ID {pending_order_id} suddenly not found!")
#                 print("This suggests the order was deleted or modified during processing")
#                 messages.error(request, "Pending order not found")
#                 return redirect('cart')

#         else:
#             print("\nERROR: Payment verification failed.")
#             messages.error(request, "Payment verification failed")
#             return render(request, "failure.html")

#     except Payment.DoesNotExist:
#         print(f"\nERROR: Payment record with ref {ref} not found.")
#         messages.error(request, "Payment not found")
#         return redirect('cart')

#     except Exception as e:
#         print(f"\nCRITICAL ERROR: An unexpected exception occurred")
#         print(f"Exception type: {type(e).__name__}")
#         print(f"Exception message: {str(e)}")
#         print(f"Exception traceback:")
#         import traceback
#         traceback.print_exc()
#         messages.error(request, f"An error occurred: {str(e)}")
#         return redirect('cart')




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

        # Verify the payment first - we only want to process verified payments
        verified = payment.verify_payment()
        print(f"\nPayment verification result: {verified}")
        
        if not verified:
            print("\nERROR: Payment verification failed.")
            messages.error(request, "Payment verification failed")
            return render(request, "failure.html")

        # Get the pending order ID from cookie or session
        pending_order_id = request.COOKIES.get('pending_order_id')
        session_pending_order_id = request.session.get('pending_order_id')
        
        print(f"\nPending order ID from cookie: {pending_order_id}")
        print(f"Pending order ID from session: {session_pending_order_id}")
        
        # Use whichever is available
        pending_order_id = pending_order_id or session_pending_order_id
        print(f"Final pending order ID being used: {pending_order_id}")
        
        # First check if this payment has already been processed
        existing_order = Order.objects.filter(transaction_id=payment.ref).first()
        if existing_order:
            print(f"\nFOUND: Payment already processed for Order #{existing_order.id}")
            
            # Clear cookies and show success page
            response = render(request, "success.html", {
                'message': "Payment already verified successfully!",
                'order': existing_order
            })
            
            # Clear cookies
            cookies_to_delete = ['cart', 'payment_ref', 'pending_order_id', 'shipping_info']
            for cookie in cookies_to_delete:
                if cookie in request.COOKIES:
                    response.delete_cookie(cookie)
            
            # Clear session data
            session_keys_to_delete = ['pending_order_id', 'cart']
            for key in session_keys_to_delete:
                if key in request.session:
                    del request.session[key]
            
            request.session.modified = True
            return response
        
        # Check for pending order or confirmed order with this ID
        pending_order = None
        order = None
        
        # Try to find the pending order first
        if pending_order_id:
            try:
                pending_order = PendingOrder.objects.get(id=pending_order_id)
                print(f"\nFound pending order with ID: {pending_order.id}")
            except PendingOrder.DoesNotExist:
                print(f"Pending order with ID {pending_order_id} not found, checking Order table...")
                try:
                    order = Order.objects.get(id=pending_order_id)
                    print(f"Found order in Order table with ID: {order.id}")
                except Order.DoesNotExist:
                    print(f"Order with ID {pending_order_id} not found in either table!")
                    pending_order_id = None
                    
        # If still no pending order ID, try to find a recent pending order for this user or email
        if not pending_order and not order:
            print("\nAttempting to recover order based on user/email...")
            
            # Try to find by user first if authenticated
            if request.user.is_authenticated:
                try:
                    recent_pending_orders = PendingOrder.objects.filter(
                        customer=request.user.customer,
                        complete=False
                    ).order_by('-date_ordered')[:5]
                    
                    print(f"Found {recent_pending_orders.count()} recent pending orders for user.")
                    if recent_pending_orders.exists():
                        pending_order = recent_pending_orders.first()
                        print(f"Recovered pending order with ID: {pending_order.id}")
                except Exception as e:
                    print(f"Error finding orders by user: {str(e)}")
            
            # If not found, try by email
            if not pending_order and payment.email:
                try:
                    # Try to match by email from the payment
                    from django.db.models import Q
                    recent_pending_orders = PendingOrder.objects.filter(
                        Q(customer__email=payment.email) | 
                        Q(customer__user__email=payment.email)
                    ).filter(complete=False).order_by('-date_ordered')[:5]
                    
                    print(f"Found {recent_pending_orders.count()} recent pending orders by email.")
                    if recent_pending_orders.exists():
                        pending_order = recent_pending_orders.first()
                        print(f"Recovered pending order with ID: {pending_order.id}")
                except Exception as e:
                    print(f"Error finding orders by email: {str(e)}")
            
            # If still nothing found, we can't proceed
            if not pending_order and not order:
                print("ABORT: Failed to find any relevant order for this payment")
                messages.error(request, "No order found for this payment")
                return redirect('cart')
        
        # Process the payment based on whether we have a pending order or confirmed order
        if pending_order:
            # Process the pending order
            print("\nProcessing a pending order...")
            
            # Set transaction ID on pending order
            pending_order.transaction_id = payment.ref
            pending_order.save()
            print(f"Updated pending order with transaction ID: {payment.ref}")
            
            # Check if this pending order already has a confirmed order
            if hasattr(pending_order, 'confirmed_order') and pending_order.confirmed_order:
                print(f"This pending order already has a confirmed order with ID: {pending_order.confirmed_order.id}")
                order = pending_order.confirmed_order
                
                # Make sure it's marked as complete
                order.complete = True
                order.transaction_id = payment.ref
                order.save()
                print("Updated existing confirmed order")
            else:
                # Convert pending order to confirmed order
                print("\nCONVERTING: Pending order to confirmed order...")
                
                # Use convert_to_order method if it exists
                if hasattr(pending_order, 'convert_to_order') and callable(getattr(pending_order, 'convert_to_order')):
                    order = pending_order.convert_to_order()
                    print(f"Used convert_to_order() to create Order #{order.id}")
                else:
                    # Create order manually if method doesn't exist
                    order = Order(
                        pending_order=pending_order,
                        customer=pending_order.customer,
                        product=pending_order.product,
                        width=pending_order.width,
                        height=pending_order.height,
                        dimension_unit=pending_order.dimension_unit,
                        design_file=pending_order.design_file,
                        special_instructions=pending_order.special_instructions,
                        total_price=pending_order.total_price,
                        transaction_id=payment.ref,
                        complete=True
                    )
                    order.save()
                    print(f"Manually created Order #{order.id}")
                
                # Set the bidirectional relationship
                order.pending_order = pending_order
                order.complete = True
                order.transaction_id = payment.ref
                order.save()
                print(f"Updated Order #{order.id} with complete=True, transaction_id={payment.ref}")
                
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
                        try:
                            print(f"  Copying file for spec '{pending_spec.field_name}'")
                            from django.core.files.base import ContentFile
                            file_content = pending_spec.field_file.read()
                            pending_spec.field_file.seek(0)  # Reset file pointer
                            order_spec.field_file.save(
                                pending_spec.field_file.name,
                                ContentFile(file_content),
                                save=True
                            )
                        except Exception as e:
                            print(f"Error copying file: {str(e)}")
                    
                    order_spec.save()
                    specs_copied += 1
                
                print(f"Successfully copied {specs_copied} specifications to confirmed order")
                
                # Mark pending order as complete
                pending_order.complete = True
                pending_order.save()
                print("Pending order marked as complete")
        
        elif order:
            # Process the already created order
            print("\nProcessing an existing order...")
            
            # Update the order with payment information
            order.transaction_id = payment.ref
            order.complete = True
            order.save()
            print(f"Updated existing order with transaction ID: {payment.ref}")
            
            # Check if this order has a related pending order
            if order.pending_order:
                # Update pending order too
                order.pending_order.complete = True
                order.pending_order.transaction_id = payment.ref
                order.pending_order.save()
                print(f"Updated related pending order #{order.pending_order.id}")
        
        # For logged-in users, mark all their other incomplete orders as complete
        if request.user.is_authenticated:
            other_orders = Order.objects.filter(
                customer=request.user.customer, 
                complete=False
            ).exclude(id=order.id)
            
            updated_count = other_orders.update(complete=True)
            print(f"Marked {updated_count} additional incomplete orders as complete")
        
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
        
        # Clear session data
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




