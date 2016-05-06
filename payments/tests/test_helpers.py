from datetime import datetime
from model_mommy import mommy

from django.contrib.auth.models import User
from django.test import TestCase, Client
from django.utils import timezone

from orders.models import Order

from payments import helpers
from payments.models import PaypalOrderTransaction


class TestHelpers(TestCase):

    def test_create_order_transaction(self):
        user = mommy.make(User, username="testuser")
        order = mommy.make(Order, user=user)
        order_txn = helpers.create_paypal_transaction(user, order)
        self.assertEqual(order_txn.order, order)
        self.assertEqual(
            order_txn.invoice_id, 'order-inv#001'
        )
        # str returns invoice id
        self.assertEqual(str(order_txn), order_txn.invoice_id)

    def test_create_existing_order_transaction(self):
        user = mommy.make(User, username="testuser")
        order = mommy.make(Order, user=user)
        order_txn = helpers.create_paypal_transaction(user, order)

        self.assertEqual(order_txn.order, order)
        self.assertEqual(
            order_txn.invoice_id, 'order-inv#001'
        )
        self.assertEqual(PaypalOrderTransaction.objects.count(), 1)

        dp_booking_txn = helpers.create_paypal_transaction(user, order)
        self.assertEqual(PaypalOrderTransaction.objects.count(), 1)
        self.assertEqual(order_txn, dp_booking_txn)

    def test_create_existing_order_txn_with_txn_id(self):
        """
        if the existing transaction is already associated with a paypal
        transaction_id, we do need to create a new transaction, with new
        invoice number with incremented counter
        """
        user = mommy.make(User, username="testuser")
        order = mommy.make(Order, user=user)
        order_txn = helpers.create_paypal_transaction(user, order)

        self.assertEqual(order_txn.order, order)
        self.assertEqual(
            order_txn.invoice_id, 'order-inv#001'
        )
        self.assertEqual(PaypalOrderTransaction.objects.count(), 1)

        order_txn.transaction_id = "123"
        order_txn.save()
        new_order_txn = helpers.create_paypal_transaction(user, order)
        self.assertEqual(PaypalOrderTransaction.objects.count(), 2)
        self.assertEqual(
            new_order_txn.invoice_id,
            'order-inv#002'
        )

    def test_create_booking_with_duplicate_invoice_number(self):
        user = mommy.make(User, username="testuser")
        order = mommy.make(Order, user=user)
        order1 = mommy.make(Order, user=user)
        order_txn = helpers.create_paypal_transaction(user, order)
        self.assertEqual(order_txn.order, order)
        self.assertEqual(
            order_txn.invoice_id, 'order-inv#001'
        )

        order_txn = helpers.create_paypal_transaction(user, order1)
        self.assertEqual(order_txn.order1, order1)
        self.assertNotEqual(
            order_txn.invoice_id, 'order-inv#001'
        )
        # to avoid duplication, the counter is set to 6 digits, the first 3
        # random between 100 and 999
        self.assertEqual(len(order1_txn.invoice_id.split('#')[-1]), 6)
