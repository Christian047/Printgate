from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from store.models import Product, Categories
from base.forms import ProductForm

@login_required
def product_list(request):
    """View to list all products with edit/delete options"""
    products = Product.objects.prefetch_related('category').all()
    context = {
        'products': products,
        'title': 'Manage Products'
    }
    return render(request, 'product_update/product_list.html', context)

@login_required
def add_product(request):
    """View to add a new product"""
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save()
            messages.success(request, f'Product "{product.title}" has been added successfully!')
            return redirect('product_list')
    else:
        form = ProductForm()
    
    context = {
        'form': form,
        'title': 'Add New Product',
        'submit_text': 'Add Product'
    }
    return render(request, 'product_update/product_form.html', context)

@login_required
def edit_product(request, pk):
    """View to edit an existing product"""
    product = get_object_or_404(Product, pk=pk)
    
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            product = form.save()
            messages.success(request, f'Product "{product.title}" has been updated successfully!')
            return redirect('product_list')
    else:
        form = ProductForm(instance=product)
    
    context = {
        'form': form,
        'product': product,
        'title': f'Edit Product: {product.title}',
        'submit_text': 'Update Product'
    }
    return render(request, 'product_update/product_form.html', context)

@login_required
def delete_product(request, pk):
    """View to delete a product"""
    product = get_object_or_404(Product, pk=pk)
    
    if request.method == 'POST':
        product_title = product.title
        product.delete()
        messages.success(request, f'Product "{product_title}" has been deleted successfully!')
        return redirect('product_list')
    
    context = {
        'product': product,
        'title': f'Delete Product: {product.title}'
    }
    return render(request, 'product_update/product_confirm_delete.html', context)