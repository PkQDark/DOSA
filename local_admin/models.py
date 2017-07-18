from django.db import models
from django.contrib.auth.models import User
from django.template.defaultfilters import slugify


class Company(models.Model):
    name = models.CharField(max_length=100, unique=True)
    comment = models.TextField(null=True, blank=True)
    active = models.BooleanField(default=True)


class CompanyUser(models.Model):
    user = models.OneToOneField(User, unique=True, on_delete=models.CASCADE)
    company = models.ForeignKey(Company)


class Device(models.Model):
    dev_id = models.CharField(max_length=40, unique=True)
    port = models.PositiveIntegerField(max_length=6, default=9090)
    company = models.ForeignKey(Company)
    owned = models.BooleanField(default=False)
