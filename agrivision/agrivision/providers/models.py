from django.conf import settings
from django.db import models

class ProviderProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='provider_profile')
    phone_number = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    company_name = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return f"{self.user.email}'s Provider Profile"

class ProviderRequest(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Accepted', 'Accepted'),
        ('Rejected', 'Rejected'),
    ]

    provider = models.ForeignKey(ProviderProfile, on_delete=models.CASCADE, related_name='requests')
    item_name = models.CharField(max_length=100)
    quantity = models.PositiveIntegerField()
    expected_price = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.item_name} by {self.provider.user.email} - {self.status}"
