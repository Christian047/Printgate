from django.shortcuts import render,get_object_or_404
from store.models import *

# Create your views here.
def order_list(request):
    # Get all confirmed orders
    orders = Order.objects.all().order_by('-date_ordered')
    
    # Get all pending orders
    pending_orders = PendingOrder.objects.all()
    
    context = {
        'orders': orders,
        'pending_orders': pending_orders,
    }
    
    return render(request, 'order_view/order_list.html', context)


def confirm_order(request, pending_id):
    if request.method == 'POST':
        pending_order = get_object_or_404(PendingOrder, id=pending_id)
        
        # Convert pending order to confirmed order
        new_order = pending_order.convert_to_order()
        
        # Copy specifications from pending order to confirmed order
        for pending_spec in pending_order.specifications.all():
            # Create new OrderSpecification for the confirmed order
            order_spec = OrderSpecification(
                order=new_order,
                field_name=pending_spec.field_name,
                field_value=pending_spec.field_value
            )
            
            # Copy file if exists
            if pending_spec.field_file:
                from django.core.files.base import ContentFile
                order_spec.field_file.save(
                    pending_spec.field_file.name,
                    ContentFile(pending_spec.field_file.read()),
                    save=True
                )
            
            order_spec.save()