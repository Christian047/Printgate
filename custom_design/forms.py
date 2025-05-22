# forms.py
from django import forms
from .models import *
import json




class ProductTypeForm(forms.ModelForm):
    class Meta:
        model = ProductType
        fields = ['name', 'description', 'icon', 'order', 'default_width', 'default_height', 'has_print_area', 'active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'icon': forms.TextInput(attrs={'class': 'form-control'}),
            'order': forms.NumberInput(attrs={'class': 'form-control'}),
            'default_width': forms.NumberInput(attrs={'class': 'form-control'}),
            'default_height': forms.NumberInput(attrs={'class': 'form-control'}),
            'has_print_area': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        
        


class DesignTemplateForm(forms.ModelForm):
    class Meta:
        model = DesignTemplate
        fields = ['name', 'product_type', 'category', 'description', 'preview_image', 
                 'canvas_json', 'is_featured', 'is_premium', 'active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'product_type': forms.Select(attrs={'class': 'form-select'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'preview_image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'canvas_json': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 10, 
                'spellcheck': 'false',
                'style': 'font-family: monospace;'
            }),
            'is_featured': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_premium': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def clean_canvas_json(self):
        # Validate the JSON data
        canvas_json = self.cleaned_data.get('canvas_json')
        try:
            # Try to parse the JSON to ensure it's valid
            if isinstance(canvas_json, str):
                json_data = json.loads(canvas_json)
                # Return the parsed JSON object to ensure it's saved as a proper JSON object
                return json_data
            return canvas_json
        except json.JSONDecodeError as e:
            raise forms.ValidationError(f"Invalid JSON format: {str(e)}")