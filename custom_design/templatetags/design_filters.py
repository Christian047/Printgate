# custom_design/templatetags/design_filters.py
from django import template
from custom_design.models import TemplateTransaction

register = template.Library()

@register.filter
def has_purchased(user, template_id):
    """Check if user has purchased a template"""
    if not user.is_authenticated:
        return False
        
    return TemplateTransaction.objects.filter(
        user=user,
        template_id=template_id,
        is_verified=True
    ).exists()