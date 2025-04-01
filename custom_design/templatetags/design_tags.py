# # In your app/templatetags/design_tags.py
# from django import template
# from designs.views import has_purchased_template

# register = template.Library()

# @register.filter
# def has_purchased(user, template_id):
#     """Template tag to check if user has purchased a template"""
#     return has_purchased_template(user, template_id)


# custom_design/templatetags/design_tags.py
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