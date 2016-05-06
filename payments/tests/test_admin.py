# -*- coding: utf-8 -*-

from model_mommy import mommy

from django.contrib.auth.models import User
from django.contrib.admin.sites import AdminSite
from django.test import TestCase

from paypal.standard.ipn.models import PayPalIPN

from orders.models import Order

from payments import helpers
from payments import admin

from payments.models import PaypalOrderTransaction


class PaymentsAdminTests(TestCase):

    def test_paypal_order_admin_display(self):
        user = mommy.make(User, first_name='Test', last_name='User')
        order = mommy.make(Order, user=user)
        pptrans = helpers.create_paypal_transaction(order.user, order)

        ppadmin = admin.PaypalOrderTransactionAdmin(
            PaypalOrderTransaction, AdminSite()
        )
        ppadmin_query = ppadmin.get_queryset(None)[0]

        self.assertEqual(
            ppadmin.get_user(ppadmin_query), 'Test User'
        )
        self.assertEqual(
            ppadmin.cost(ppadmin_query),
            u"\u00A3{}.00".format(order.event.cost)
        )

    def test_paypaladmin_display(self):
        mommy.make(PayPalIPN, first_name='Mickey', last_name='Mouse')
        paypal_admin = admin.PayPalAdmin(PayPalIPN, AdminSite())
        query = paypal_admin.get_queryset(None)[0]
        self.assertEqual(paypal_admin.buyer(query), 'Mickey Mouse')


class PaymentsAdminFiltersTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = mommy.make(
            User, first_name="Foo", last_name="Bar", username="foob"
        )
        cls.user1 = mommy.make(
            User, first_name="Donald", last_name="Duck", username="dd"
        )
        for user in User.objects.all():
            mommy.make(PaypalOrderTransaction, booking__user=user,
                       _quantity=5
                       )

    def test_payments_user_filter_choices(self):
        # test that user filter shows formatted choices ordered by first name

        userfilter = admin.PaypalUserFilter(
            None, {}, PaypalOrderTransaction,
            admin.PaypalOrderTransactionAdmin
        )

        self.assertEqual(
            userfilter.lookup_choices,
            [
                (self.user1.id, 'Donald Duck (dd)'),
                (self.user.id, 'Foo Bar (foob)')
            ]
        )
