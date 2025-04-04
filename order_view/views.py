from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, F, Q
from django.utils import timezone
from django.contrib import messages
from datetime import timedelta
from django.core.files.base import ContentFile
from store.models import *

@login_required
def admin_dashboard(request):
    """Main admin dashboard with overview statistics"""
    
    # Get only orders with transaction IDs and amounts
    orders = Order.objects.filter(
        transaction_id__isnull=False,  # Only orders with transaction IDs
        total_price__gt=0,             # Only orders with prices
        complete=True                  # Only completed orders
    ).prefetch_related('myorder')
    
    pending_orders = PendingOrder.objects.all()
    
    # Calculate total revenue from verified orders
    total_revenue = orders.aggregate(total=Sum('total_price'))['total'] or 0
    
    # Calculate statistics
    today = timezone.now().date()
    today_orders = orders.filter(date_ordered__date=today)
    today_revenue = today_orders.aggregate(total=Sum('total_price'))['total'] or 0
    
    # Calculate completed vs processing orders
    completed_orders = orders.filter(complete=True)
    processing_orders = orders.filter(complete=False)
    
    # Get top products
    top_products = Product.objects.annotate(
        order_count=Count('order', filter=Q(order__transaction_id__isnull=False))
    ).order_by('-order_count')[:5]
    
    # Get recent orders
    recent_orders = orders.order_by('-date_ordered')[:5]
    recent_pending = pending_orders.order_by('-date_ordered')[:5]
    
    # Add payment data to orders and ensure customer data is populated
    orders_with_complete_data = []
    for order in recent_orders:
        payment = order.myorder.first()  # Get the first related payment
        
        # Copy customer details from payment to order if missing
        if payment:
            if not order.first_name and not order.last_name and hasattr(payment, 'first_name') and hasattr(payment, 'last_name'):
                order.customer_name = f"{payment.first_name} {payment.last_name}"
            if not order.email and hasattr(payment, 'email'):
                order.customer_email = payment.email
                
            # Ensure transaction data is copied if missing
            if not order.transaction_id and hasattr(payment, 'transaction_id'):
                order.transaction_id = payment.transaction_id
                order.save()
        
        orders_with_complete_data.append(order)
    
    context = {
        'recent_orders': orders_with_complete_data,
        'verified_count': orders.count(),
        'unverified_count': pending_orders.count(),
        'total_revenue': total_revenue,
        'today_orders': today_orders.count(),
        'today_revenue': today_revenue,
        'completed_count': completed_orders.count(),
        'processing_count': processing_orders.count(),
        'top_products': top_products,
        'recent_pending': recent_pending,
    }
    
    return render(request, 'admin_dashboard/dashboard.html', context)


@login_required
def order_list(request):
    """View all orders - both verified and unverified (pending)"""
    
    # Get filter parameters
    status = request.GET.get('status', 'all')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    show_only_with_transaction = request.GET.get('with_transaction', 'yes') == 'yes'
    
    # Base queryset with proper joins to payment data
    base_orders = Order.objects.all().prefetch_related('myorder').order_by('-date_ordered')
    
    # Filter out orders without transaction IDs if requested
    if show_only_with_transaction:
        base_orders = base_orders.filter(transaction_id__isnull=False, total_price__gt=0)
    
    # Apply other filters
    if status == 'completed':
        orders = base_orders.filter(complete=True)
        pending_orders = PendingOrder.objects.none()
    elif status == 'processing':
        orders = base_orders.filter(complete=False)
        pending_orders = PendingOrder.objects.none()
    elif status == 'unverified':
        orders = Order.objects.none()
        pending_orders = PendingOrder.objects.all().order_by('-date_ordered')
    else:  # 'all'
        orders = base_orders
        pending_orders = PendingOrder.objects.all().order_by('-date_ordered')
    
    # Initialize this variable before any conditions
    orders_with_complete_data = []
    
    # Enrich orders with customer data from related payment records
    for order in orders:
        payment = order.myorder.first()
        
        # Copy customer details from payment if exists
        if payment:
            # Add customer name from payment's firstname and lastname
            if hasattr(payment, 'firstname') and hasattr(payment, 'lastname'):
                order.customer_firstname = payment.firstname
                order.customer_lastname = payment.lastname
                order.customer_name = f"{payment.firstname or ''} {payment.lastname or ''}".strip()
            
            # Add email from payment if it exists
            if hasattr(payment, 'email'):
                order.customer_email = payment.email
        
        orders_with_complete_data.append(order)
    
    # Calculate total revenue from verified orders
    total_revenue = orders.aggregate(total=Sum('total_price'))['total'] or 0
    
    context = {
        'orders': orders_with_complete_data,
        'pending_orders': pending_orders,
        'total_revenue': total_revenue,
        'status': status,
        'date_from': date_from,
        'date_to': date_to,
        'with_transaction': show_only_with_transaction,
    }
    
    return render(request, 'order_view/order_list.html', context)







@login_required
def order_detail(request, order_id):
    """View detailed information about a specific verified order"""
    
    order = get_object_or_404(Order, id=order_id)
    
    context = {
        'order': order,
        'specifications': order.specifications.all(),
    }
    
    return render(request, 'order_view/order_detail.html', context)

@login_required
def pending_order_detail(request, pending_id):
    """View detailed information about a specific unverified (pending) order"""
    
    pending_order = get_object_or_404(PendingOrder, id=pending_id)
    
    context = {
        'pending_order': pending_order,
        'specifications': pending_order.specifications.all(),
        'reference_images': pending_order.reference_images.all(),
    }
    
    return render(request, 'order_view/pending_order_detail.html', context)




@login_required
def verify_order(request, pending_id):
    """Convert an unverified (pending) order to a verified order"""
    
    if request.method == 'POST':
        try:
            pending_order = get_object_or_404(PendingOrder, id=pending_id)
            
            # First, check if there are already open orders for this customer
            # If there are, close them to avoid MultipleObjectsReturned error
            if pending_order.customer:
                existing_open_orders = Order.objects.filter(
                    customer=pending_order.customer, 
                    complete=False
                )
                # Mark all as complete except the one we're about to create
                for order in existing_open_orders:
                    order.complete = True
                    order.save()
                    messages.info(request, f'Existing open order #{order.id} was automatically completed.')
            
            # Create new verified order from the pending order
            order = Order(
                pending_order=pending_order,
                customer=pending_order.customer,
                product=pending_order.product,
                width=pending_order.width,
                height=pending_order.height,
                dimension_unit=pending_order.dimension_unit,
                special_instructions=pending_order.special_instructions,
                total_price=pending_order.total_price,
                transaction_id=pending_order.transaction_id or f"manual-verify-{pending_id}",
            )
            
            # Save the order first to generate ID
            order.save()
            
            # Copy design file if it exists
            if pending_order.design_file:
                try:
                    # Read the design file content
                    file_content = pending_order.design_file.read()
                    order.design_file.save(
                        pending_order.design_file.name,
                        ContentFile(file_content),
                        save=True
                    )
                except Exception as e:
                    messages.warning(request, f"Could not copy design file: {str(e)}")
            
            # Copy specifications from pending order to verified order
            for pending_spec in pending_order.specifications.all():
                # Create new OrderSpecification for the verified order
                order_spec = OrderSpecification(
                    order=order,
                    field_name=pending_spec.field_name,
                    field_value=pending_spec.field_value
                )
                
                # Copy file if exists
                if pending_spec.field_file:
                    try:
                        file_content = pending_spec.field_file.read()
                        order_spec.field_file.save(
                            pending_spec.field_file.name,
                            ContentFile(file_content),
                            save=True
                        )
                    except Exception as e:
                        messages.warning(request, f"Could not copy specification file: {str(e)}")
                
                order_spec.save()
            
            # Link the pending order to the verified order
            pending_order.confirmed_order = order
            pending_order.save()
            
            messages.success(request, f'Order #{pending_id} has been verified successfully.')
            
        except Exception as e:
            messages.error(request, f"Error verifying order: {str(e)}")
            
    return redirect('order_list')







@login_required
def mark_order_complete(request, order_id):
    """Mark a verified order as complete"""
    
    if request.method == 'POST':
        order = get_object_or_404(Order, id=order_id)
        order.complete = True
        order.save()
        
        messages.success(request, f'Order #{order_id} has been marked as complete.')
        return redirect('order_list')
    
    return redirect('order_list')

@login_required
def sales_report(request):
    """Generate sales reports and statistics"""
    
    # Get time period from request
    period = request.GET.get('period', 'all')
    
    # Base queryset
    orders = Order.objects.all()
    
    # Apply time period filter
    today = timezone.now().date()
    
    if period == 'today':
        orders = orders.filter(date_ordered__date=today)
        title = "Today's Sales"
    elif period == 'week':
        week_start = today - timedelta(days=today.weekday())
        orders = orders.filter(date_ordered__date__gte=week_start)
        title = "This Week's Sales"
    elif period == 'month':
        month_start = today.replace(day=1)
        orders = orders.filter(date_ordered__date__gte=month_start)
        title = "This Month's Sales"
    else:
        title = "All Sales"
    
    # Calculate totals
    total_revenue = orders.aggregate(total=Sum('total_price'))['total'] or 0
    total_orders = orders.count()
    
    # Calculate average order value
    avg_order_value = total_revenue / total_orders if total_orders > 0 else 0
    
    # Get top products by order count
    top_products = Product.objects.filter(order__in=orders).annotate(
        order_count=Count('order'),
        revenue=Sum('order__total_price')
    ).order_by('-order_count')[:10]
    
    # Recent orders
    recent_orders = orders.order_by('-date_ordered')[:20]
    
    context = {
        'period': period,
        'title': title,
        'total_revenue': total_revenue,
        'total_orders': total_orders,
        'avg_order_value': avg_order_value,
        'top_products': top_products,
        'recent_orders': recent_orders
    }
    
    return render(request, 'order_view/sales_report.html', context) 



@login_required
def order_full_details(request, order_id):
    """
    View full details of a specific order
    """
    try:
        # Use select_related and prefetch_related for optimized querying
        order = Order.objects.select_related('product', 'customer', 'pending_order')\
            .prefetch_related(
                'orderitem_set__product', 
                'orderitem_set__variant',
                'pending_order__specifications'
            ).get(id=order_id)
        
        return render(request, 'order_view/order_full_details.html', {'order': order})
    
    except Order.DoesNotExist:
        messages.error(request, "Order not found.")
        return redirect('orders')  # Adjust this to your actual dashboard URL name