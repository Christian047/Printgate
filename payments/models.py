from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import secrets
from .paystack import Paystack
from store.models import Order

# Create your models here.
class UserWallet(models.Model):
	user = models.OneToOneField(User, null=True, on_delete=models.CASCADE)
	currency = models.CharField(max_length=50, default='NGN')
	balance = models.PositiveIntegerField(default=0)
	created_at = models.DateTimeField(default=timezone.now, null=True)

	def __str__(self):
		return self.user.__str__()


class Payment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True)
    amount = models.PositiveIntegerField()
    ref = models.CharField(max_length=200)
    email = models.EmailField()
    firstname = models.CharField(null=True, blank=True,max_length= 50)
    lastname = models.CharField(null=True, blank=True,max_length= 50)
    verified = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)
    session_id = models.CharField(max_length=255)  # Ensure this field exists
    payment_order = models.ForeignKey(Order, on_delete=models.CASCADE, default= None, related_name= 'myorder')

    class Meta:
        ordering = ('-date_created',)

    def __str__(self):
        return f"Payment: {self.amount}"

    def save(self, *args, **kwargs):
        while not self.ref:
            ref = secrets.token_urlsafe(50)
            object_with_similar_ref = Payment.objects.filter(ref=ref)
            if not object_with_similar_ref:
                self.ref = ref

        super().save(*args, **kwargs)

    def amount_value(self):
        return int(self.amount) * 100
    

    def verify_payment(self):
        try:
            paystack = Paystack()
            status, result = paystack.verify_payment(self.ref, self.amount)
            
            if status:
                # Store transaction data regardless of amount match
                self.transaction_id = result.get('transaction_id')  # Store the transaction ID
                self.actual_amount = result.get('amount', 0) / 100  # Store the actual amount
                
                # Verify amount matches expected amount
                if result.get('amount', 0) / 100 == self.amount:
                    self.verified = True
                    
                    # If we have an order linked to this payment, update it
                    if hasattr(self, 'payment_order') and self.payment_order:
                        self.payment_order.transaction_id = self.ref
                        self.payment_order.total_price = self.amount
                        self.payment_order.complete = True
                        self.payment_order.save()
                else:
                    self.verified = False
                    # Optionally log the amount mismatch
                    print(f"Amount mismatch: expected {self.amount}, got {result.get('amount', 0) / 100}")
            else:
                # Handle failed verification
                self.verified = False
                
            # Save all the new data
            self.save()
            
            return self.verified
        except Exception as e:
            # Log the error
            print(f"Payment verification error: {str(e)}")
            return False