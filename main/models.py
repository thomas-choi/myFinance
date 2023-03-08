from django.db import models

# Create your models here.

class Router(models.Model):
    specifications = models.FileField(upload_to='US_Stock_Performance')

# So this file gets uploaded to root > media > US_Stock_Performance 
