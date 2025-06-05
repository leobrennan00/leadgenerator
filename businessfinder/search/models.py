from django.db import models

class BusinessType(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

class EmailAddress(models.Model):
    email = models.EmailField(unique=True)
    business_type = models.ForeignKey(BusinessType, on_delete=models.CASCADE, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.email