from django.conf import settings
from django.contrib.auth.models import User
from django.db import models


class Order(models.Model):

    paypal_email = models.EmailField(
        default=settings.DEFAULT_PAYPAL_EMAIL,
        help_text='Email for the paypal account to be used for payment.  '
                  'Check this carefully!'
    )
    user = models.ForeignKey(User)
    paid = models.BooleanField(default=False)


class Voucher(models.Model):

    pass


#  TODO Products -- Orders M2M?