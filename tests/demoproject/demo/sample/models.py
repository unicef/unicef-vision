from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models


class DemoModel(models.Model):
    name = models.CharField(max_length=50)
    boolean_field = models.BooleanField(default=False)


class Image(models.Model):
    name = models.CharField(max_length=150)
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
    )
    object_id = models.IntegerField()
    content_object = GenericForeignKey()
    code = models.CharField(max_length=64)


class Author(models.Model):
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)


class Book(models.Model):
    name = models.CharField(max_length=150)
    author = models.ForeignKey(Author, on_delete=models.CASCADE)
