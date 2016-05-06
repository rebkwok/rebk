from django.db import models


class Product(models.Model):
    """
    e.g.
    Product 'T-Shirt'
    ProductAttribute: Size
        ProductAttributeOption: Small
        ProductAttributeOption: Med
        ProductAttributeOption: Large
    ProductAttribute: Colous
        ProductAttributeOption: Black
        ProductAttributeOption: Red
        ProductAttributeOption: Blue
    """
    name = models.CharField(max_length=255)


class ProductAttribute(models.Model):
    name = models.CharField(max_length=255)
    product = models.ForeignKey(Product, related_name='attribues')


class ProductAttributeOption(models.Model):
    name = models.CharField(max_length=255)
    attribute = models.ForeignKey(ProductAttribute, related_name='options')