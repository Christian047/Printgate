# forms.py
from django import forms
from .models import PrintJob
from store.models import *




class BaseOrderForm(forms.Form):
    def __init__(self, product, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.product = product
        self.spec_fields = product.spec_fields.all().order_by('order')
        
        # Dynamically add fields based on the product specification
        for field in self.spec_fields:
            field_name = f"spec_{field.id}"
            
            if field.field_type == 'text':
                self.fields[field_name] = forms.CharField(
                    label=field.name,
                    required=field.required,
                    help_text=field.help_text,
                    widget=forms.TextInput(attrs={
                        'class': 'form-control',
                        'placeholder': f'Enter {field.name}',
                        'autofocus': True if field.order == 1 else False
                    })
                )
            
            elif field.field_type == 'number':
                self.fields[field_name] = forms.FloatField(
                    label=field.name,
                    required=field.required,
                    help_text=field.help_text,
                    widget=forms.NumberInput(attrs={
                        'class': 'form-control',
                        'placeholder': f'Enter {field.name}',
                        'min': 0
                    })
                )
            
            elif field.field_type == 'select':
                choices = [(option.strip(), option.strip()) for option in field.options.split(',')]
                self.fields[field_name] = forms.ChoiceField(
                    label=field.name,
                    required=field.required,
                    choices=choices,
                    help_text=field.help_text,
                    widget=forms.Select(attrs={'class': 'form-select spec-field' })
                )
            
            elif field.field_type == 'file':
                self.fields[field_name] = forms.FileField(
                    label=field.name,
                    required=field.required,
                    help_text=field.help_text,
                    widget=forms.ClearableFileInput(attrs={'class': 'form-control-file'})
                )
            
            elif field.field_type == 'color':
                self.fields[field_name] = forms.CharField(
                    label=field.name,
                    required=field.required,
                    help_text=field.help_text,
                    widget=forms.TextInput(attrs={
                        'type': 'color',
                        'class': 'form-control form-control-color',
                        'value': '#000000'  # Default black
                    })
                )
            
            elif field.field_type == 'textarea':
                self.fields[field_name] = forms.CharField(
                    label=field.name,
                    required=field.required,
                    help_text=field.help_text,
                    widget=forms.Textarea(attrs={
                        'class': 'form-control',
                        'rows': 4,
                        'placeholder': f'Enter {field.name}...'
                    })
                )
        
        # Add product variant selection if there are variants
        variants = product.variants.all()
        if variants.exists():
            variant_choices = [
                (variant.id, f"{variant.name} ({'+$' if variant.price_adjustment > 0 else '-$' if variant.price_adjustment < 0 else ''}${abs(variant.price_adjustment)})") 
                for variant in variants
            ]
            self.fields['variant'] = forms.ChoiceField(
                label="Select Option",
                choices=variant_choices,
                required=True,
                widget=forms.Select(attrs={'class': 'form-select'})
            )
        
        # Move special_instructions to the end
        self.fields['special_instructions'] = forms.CharField(
            widget=forms.Textarea(attrs={
                'rows': 3,
                'class': 'form-control',
                'placeholder': 'Enter any special instructions...'
            }),
            required=False,
            label="Special Instructions"
        )

    def save(self, customer=None):
        # Calculate total price based on product, variant, and any other factors
        product = self.product
        base_price = product.base_price
        
        # Add variant price adjustment if selected
        total_price = base_price
        variant_id = self.cleaned_data.get('variant')
        variant = None
        
        design_file = None
        for field in self.spec_fields:
            if field.name == "Design file":  # Or whatever identifier you use
                field_name = f"spec_{field.id}"
                design_file = self.cleaned_data.get(field_name)
                break
        
        if variant_id:
            try:
                variant = product.variants.get(id=variant_id)
                total_price += variant.price_adjustment
            except:
                pass
    
        # Create pending order
        pending_order = PendingOrder.objects.create(
            customer=customer,
            product=product,
            variant=variant,
            special_instructions=self.cleaned_data.get('special_instructions', ''),
            total_price=total_price,
            design_file=design_file
        )
        
        # Save specifications
        for field in self.spec_fields:
            field_name = f"spec_{field.id}"
            value = self.cleaned_data.get(field_name)
            
            if field.field_type == 'file' and value:
                # For file fields, save the file separately
                PendingOrderSpecification.objects.create(
                    pending_order=pending_order,
                    spec_field=field,
                    field_name=field.name,
                    field_value=value.name,  # Store filename in value
                    field_file=value  # Store actual file
                )
            else:
                # For non-file fields, just save the value
                PendingOrderSpecification.objects.create(
                    pending_order=pending_order,
                    field_name=field.name,
                    field_value=str(value) if value is not None else ''
                )
        
        return pending_order
    
class DesignerOrderForm(BaseOrderForm):

        def __init__(self, product, *args, **kwargs):
            super().__init__(product, *args, **kwargs)
            
          
            if 'special_instructions' in self.fields:
                del self.fields['special_instructions']
            
            self.fields['designer_instructions'] = forms.CharField(
                widget=forms.Textarea(attrs={
                    'rows': 5,
                    'class': 'form-control',
      
                }),
                required=True,
                label="Design Instructions",
     
            )
            
            # Add field for reference images
            self.fields['reference_images'] = forms.FileField(
                widget=forms.ClearableFileInput(attrs={
                    'class': 'form-control',
                    'accept': '.jpg,.jpeg,.png,.pdf'
                }),
                required=False,
                label="Reference Images",
        
            )
            
            

            # Add special instructions back at the end
            self.fields['special_instructions'] = forms.CharField(
                widget=forms.Textarea(attrs={
                    'rows': 3,
                    'class': 'form-control',
              
                }),
                required=False,
                label="Additional Notes"
            )
        
        def save(self, customer=None):
            # Get the pending order created by the parent method
            pending_order = super().save(customer=customer)
            
            # Add designer fee to the total price
            pending_order.total_price += 5000
            pending_order.designer_fee = 5000
            pending_order.order_type = 'designer'
            
            pending_order.designer_instructions = self.cleaned_data.get('designer_instructions', '')
            pending_order.save()
            
            # Handle multiple reference images
            if 'reference_images' in self.cleaned_data and self.cleaned_data['reference_images']:
                reference_images = self.files.getlist('reference_images')
                
                for image in reference_images:
                    ReferenceImage.objects.create(
                        pending_order=pending_order,
                        image=image
                    )
                    
            return pending_order