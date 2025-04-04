from django.contrib import admin
from .models import Payment, UserWallet

# class PaymentAdmin(admin.ModelAdmin):
# 	list_display = ['user',"id", "ref", 'amount', "verified", "date_created"]


# admin.site.register(Payment, PaymentAdmin)
# admin.site.register(UserWallet)

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    def short_ref(self, obj):
        return (obj.ref[:4] + '...') if len(obj.ref) > 4 else obj.ref
    
    short_ref.short_description = 'Ref'  # Set column header for reference
    
    def short_session_id(self, obj):
        return (obj.session_id[:4] + '...') if len(obj.session_id) > 4 else obj.session_id
    
    short_session_id.short_description = 'Session ID'  # Set column header for session ID
    
    list_display = ("user", "verified", "email","firstname","lastname", "amount", "payment_order", "short_session_id", "date_created", "short_ref")
