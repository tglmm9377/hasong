from django.contrib import admin
from user import models
# Register your models here.
admin.site.register(models.User)
admin.site.register(models.Address)