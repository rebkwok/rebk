# -*- coding: utf-8 -*-

from model_mommy import mommy
from mock import Mock, patch

from django.conf import settings
from django.contrib.auth.models import User
from django.core import mail
from django.core.urlresolvers import reverse
from django.test import TestCase, Client, override_settings

from orders.models import Order, Voucher

from payments import helpers
from payments.models import PaypalOrderTransaction
from payments.models import logger as payment_models_logger

from paypal.standard.ipn.models import PayPalIPN

from six import b, text_type
from six.moves.urllib.parse import urlencode


# Parameters are all bytestrings, so we can construct a bytestring
# request the same way that Paypal does.
CHARSET = "windows-1252"
TEST_RECEIVER_EMAIL = 'dummy-email@hotmail.com'
IPN_POST_PARAMS = {
    "mc_gross": b"7.00",
    "invoice": b"order-inv001",
    "protection_eligibility": b"Ineligible",
    "txn_id": b"51403485VH153354B",
    "last_name": b"User",
    "receiver_email": b(TEST_RECEIVER_EMAIL),
    "payer_id": b"BN5JZ2V7MLEV4",
    "tax": b"0.00",
    "payment_date": b"23:04:06 Feb 02, 2009 PST",
    "first_name": b"Test",
    "mc_fee": b"0.44",
    "notify_version": b"3.8",
    "custom": b"1",
    "payer_status": b"verified",
    "payment_status": b"Completed",
    "business": b"rebkdesign%40gmail.com",
    "quantity": b"1",
    "verify_sign": b"An5ns1Kso7MWUdW4ErQKJJJ4qi4-AqdZy6dD.sGO3sDhTf1wAbuO2IZ7",
    "payer_email": b"test_user@gmail.com",
    "payment_type": b"instant",
    "payment_fee": b"",
    "receiver_id": b"258DLEHY2BDK6",
    "txn_type": b"web_accept",
    "item_name": "order",
    "mc_currency": b"GBP",
    "item_number": b"",
    "residence_country": "GB",
    "handling_amount": b"0.00",
    "charset": b(CHARSET),
    "payment_gross": b"",
    "transaction_subject": b"",
    "ipn_track_id": b"1bd9fe52f058e",
    "shipping": b"0.00",
}


@override_settings(DEFAULT_PAYPAL_EMAIL=TEST_RECEIVER_EMAIL)
class PaypalSignalsTests(TestCase):

    def paypal_post(self, params):
        """
        Does an HTTP POST the way that PayPal does, using the params given.
        Taken from django-paypal
        """
        # We build params into a bytestring ourselves, to avoid some encoding
        # processing that is done by the test client.
        cond_encode = lambda v: v.encode(CHARSET) if isinstance(v, text_type) else v
        byte_params = {
            cond_encode(k): cond_encode(v) for k, v in params.items()
            }
        post_data = urlencode(byte_params)
        return self.client.post(
            reverse('paypal-ipn'),
            post_data, content_type='application/x-www-form-urlencoded'
        )

    def test_paypal_notify_url_with_no_data(self):
        self.assertFalse(PayPalIPN.objects.exists())
        resp = self.paypal_post(
            {'charset': b(CHARSET), 'txn_id': 'test'}
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(PayPalIPN.objects.count(), 1)

        ppipn = PayPalIPN.objects.first()
        self.assertTrue(ppipn.flag)

        # one warning email sent
        self.assertEqual(len(mail.outbox), 1)

        self.assertEqual(
            mail.outbox[0].subject,
            'WARNING! Error processing Invalid Payment Notification from PayPal'
        )
        self.assertEqual(
            mail.outbox[0].body,
            'PayPal sent an invalid transaction notification while '
            'attempting to process payment;.\n\nThe flag '
            'info was "{}"\n\nAn additional error was raised: {}'.format(
                ppipn.flag_info, 'Unknown object for payment'
            )
        )

    def test_paypal_notify_url_with_no_matching_order(self):
        self.assertFalse(PayPalIPN.objects.exists())

        resp = self.paypal_post(
            {'custom': b'1', 'charset': b(CHARSET), 'txn_id': 'test'}
        )

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(PayPalIPN.objects.count(), 1)
        ppipn = PayPalIPN.objects.first()

        # one warning email sent
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(
            mail.outbox[0].subject,
            'WARNING! Error processing Invalid Payment Notification from PayPal'
        )
        self.assertEqual(
            mail.outbox[0].body,
            'PayPal sent an invalid transaction notification while '
            'attempting to process payment;.\n\nThe flag '
            'info was "{}"\n\nAn additional error was raised: {}'.format(
                ppipn.flag_info, 'Order with id 1 does not exist'
            )
        )

    @patch('paypal.standard.ipn.models.PayPalIPN._postback')
    def test_paypal_notify_url_with_complete_status(self, mock_postback):
        mock_postback.return_value = b"VERIFIED"
        user = mommy.make(User)
        order = mommy.make(Order, user=user)
        pptrans = helpers.create_paypal_transaction(order.user, order)

        self.assertFalse(PayPalIPN.objects.exists())
        params = dict(IPN_POST_PARAMS)
        params.update(
            {
                'custom': b('{}'.format(order.id)),
                'invoice': b(pptrans.invoice_id),
                'txn_id': b'test_txn_id'
            }
        )
        self.assertIsNone(pptrans.transaction_id)
        resp = self.paypal_post(params)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(PayPalIPN.objects.count(), 1)
        ppipn = PayPalIPN.objects.first()
        self.assertFalse(ppipn.flag)
        self.assertEqual(ppipn.flag_info, '')

        # check paypal trans obj is updated
        pptrans.refresh_from_db()
        self.assertEqual(pptrans.transaction_id, 'test_txn_id')

        # 2 emails sent, to user and studio
        self.assertEqual(len(mail.outbox), 2)

    @patch('paypal.standard.ipn.models.PayPalIPN._postback')
    def test_paypal_notify_url_with_complete_status_unmatching_order(self, mock_postback):
        mock_postback.return_value = b"VERIFIED"

        self.assertFalse(PayPalIPN.objects.exists())
        self.assertFalse(Order.objects.exists())
        params = dict(IPN_POST_PARAMS)
        params.update(
            {
                'custom': b'1',
            }
        )
        resp = self.paypal_post(params)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(PayPalIPN.objects.count(), 1)
        ppipn = PayPalIPN.objects.first()

        # paypal ipn is not flagged
        self.assertFalse(ppipn.flag)
        self.assertEqual(ppipn.flag_info, '')

        # we can't match up the payment to order, so raise error and send
        # emails
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(
            mail.outbox[0].subject,
            'WARNING! Error processing PayPal IPN'
        )
        self.assertEqual(
            mail.outbox[0].body,
            'Valid Payment Notification received from PayPal but an error '
            'occurred during processing.\n\nTransaction id {}\n\nThe flag info '
            'was "{}"\n\nError raised: Order with id 1 does not exist'.format(
                ppipn.txn_id, ppipn.flag_info,
            )
        )

    @patch('paypal.standard.ipn.models.PayPalIPN._postback')
    def test_successful_paypal_payment_sends_emails(self, mock_postback):
        mock_postback.return_value = b"VERIFIED"
        order = mommy.make(Order)
        invoice_id = helpers.create_paypal_transaction(
            order.user, order
        ).invoice_id

        self.assertFalse(PayPalIPN.objects.exists())
        params = dict(IPN_POST_PARAMS)
        params.update(
            {
                'custom': b('{}'.format(order.id)),
                'invoice': b(invoice_id)
            }
        )
        resp = self.paypal_post(params)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(PayPalIPN.objects.count(), 1)

        # 2 emails sent, to user and studio
        self.assertEqual(
            len(mail.outbox), 2,
            "NOTE: Fails if SEND_ALL_STUDIO_EMAILS!=True in env/test settings"
        )
        self.assertEqual(mail.outbox[0].to, [settings.DEFAULT_STUDIO_EMAIL])
        self.assertEqual(mail.outbox[1].to, [order.user.email])

    @patch('paypal.standard.ipn.models.PayPalIPN._postback')
    def test_successful_paypal_payment_updates_order(self, mock_postback):
        mock_postback.return_value = b"VERIFIED"
        order = mommy.make(Order)
        invoice_id = helpers.create_paypal_transaction(
            order.user, order
        ).invoice_id

        self.assertFalse(PayPalIPN.objects.exists())
        params = dict(IPN_POST_PARAMS)
        params.update(
            {
                'custom': b('{}'.format(order.id)),
                'invoice': b(invoice_id)
            }
        )
        self.paypal_post(params)
        order.refresh_from_db()
        self.assertTrue(order.paid)

    @patch('paypal.standard.ipn.models.PayPalIPN._postback')
    def test_paypal_notify_url_with_complete_status_no_invoice_number(self, mock_postback):
        mock_postback.return_value = b"VERIFIED"
        order = mommy.make(Order)
        invoice_id = helpers.create_paypal_transaction(
            order.user, order
        ).invoice_id

        self.assertFalse(PayPalIPN.objects.exists())
        params = dict(IPN_POST_PARAMS)
        params.update(
            {
                'custom': b('order {}'.format(order.id)),
                'invoice': b''
            }
        )
        self.paypal_post(params)
        order.refresh_from_db()
        self.assertTrue(order.paid)

        # 3 emails sent - studio, user, support to notify about missing inv
        self.assertEqual(len(mail.outbox), 3)
        self.assertEqual(
            mail.outbox[2].subject,
            '{} No invoice number on paypal ipn for order id {}'.format(
                settings.ACCOUNT_EMAIL_SUBJECT_PREFIX, order.id
            )
        )

    @patch('paypal.standard.ipn.models.PayPalIPN._postback')
    def test_paypal_notify_only_updates_relevant_order(self, mock_postback):
        mock_postback.return_value = b"VERIFIED"
        user = mommy.make(User)
        order = mommy.make(Order, user=user)
        invoice_id = helpers.create_paypal_transaction(
            order.user, order
        ).invoice_id
        mommy.make(Order, _quantity=5)

        self.assertFalse(PayPalIPN.objects.exists())
        params = dict(IPN_POST_PARAMS)
        params.update(
            {
                'custom': b('{}'.format(order.id)),
                'invoice': b(invoice_id)
            }
        )
        resp = self.paypal_post(params)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(PayPalIPN.objects.count(), 1)
        ppipn = PayPalIPN.objects.first()
        self.assertFalse(ppipn.flag)
        self.assertEqual(ppipn.flag_info, '')

        order.refresh_from_db()
        self.assertTrue(order.paid)
        # 2 emails sent, to user and studio
        self.assertEqual(len(mail.outbox), 2)

        for order in Order.objects.all():
            if order.id == order.id:
                self.assertTrue(order.paid)
            else:
                self.assertFalse(order.paid)

    @patch('paypal.standard.ipn.models.PayPalIPN._postback')
    def test_paypal_notify_url_without_order_trans_object(self, mock_postback):
        """
        A PayPalOrderTransaction object should be created
        when the paypal form button is created (to generate and store the inv
        number and transaction id against each order.  In case it isn't,
        we create one when processing the payment
        """
        mock_postback.return_value = b"VERIFIED"
        order = mommy.make(Order)

        self.assertFalse(PayPalIPN.objects.exists())
        self.assertFalse(PaypalOrderTransaction.objects.exists())

        params = dict(IPN_POST_PARAMS)
        params.update(
            {
                'custom': b('{}'.format(order.id)),
                'invoice': b''
            }
        )
        resp = self.paypal_post(params)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(PayPalIPN.objects.count(), 1)
        ppipn = PayPalIPN.objects.first()
        self.assertFalse(ppipn.flag)
        self.assertEqual(ppipn.flag_info, '')

        self.assertEqual(PaypalOrderTransaction.objects.count(), 1)
        order.refresh_from_db()
        self.assertTrue(order.paid)
        # 3 emails sent, to user and studio and support because there is no inv
        self.assertEqual(len(mail.outbox), 3)

    @patch('paypal.standard.ipn.models.PayPalIPN._postback')
    def test_paypal_notify_url_with_refunded_status(self, mock_postback):
        """
        when a paypal payment is refunded, it looks like it posts back to the
        notify url again (since the PayPalIPN is updated).  Test that we can
        identify and process refunded payments.
        """
        mock_postback.return_value = b"VERIFIED"
        order = mommy.make(Order)
        pptrans = helpers.create_paypal_transaction(order.user, order)
        pptrans.transaction_id = "test_trans_id"
        pptrans.save()

        self.assertFalse(PayPalIPN.objects.exists())
        params = dict(IPN_POST_PARAMS)
        params.update(
            {
                'custom': b('{}'.format(order.id)),
                'invoice': b(pptrans.invoice_id),
                'payment_status': b'Refunded'
            }
        )
        self.paypal_post(params)
        order.refresh_from_db()
        self.assertFalse(order.paid)

        self.assertEqual(len(mail.outbox), 1)

        # emails sent to studio and support
        self.assertEqual(
            mail.outbox[0].to,
            [settings.DEFAULT_STUDIO_EMAIL, settings.SUPPORT_EMAIL],
        )

    @patch('paypal.standard.ipn.models.PayPalIPN._postback')
    def test_paypal_date_format_with_extra_spaces(self, mock_postback):
        mock_postback.return_value = b"VERIFIED"
        order = mommy.make(Order)
        pptrans = helpers.create_paypal_transaction(
            order.user, order
        )
        pptrans.transaction_id = "test_trans_id"
        pptrans.save()

        params = dict(IPN_POST_PARAMS)
        params.update(
            {
                "payment_date": b"01:21:32  Jan   25  2015 PDT",
                'invoice': b(pptrans.invoice_id),
                'custom': b('{}'.format(order.id))
            }
        )

        # Check extra spaces
        self.paypal_post(params)
        ppipn = PayPalIPN.objects.latest('id')
        self.assertFalse(ppipn.flag)

    def test_paypal_notify_url_with_invalid_date(self):
        """
        There has been one instance of a returned payment which has no info
        except a flag invalid date in the paypal form.  Check that this will
        send a support email
        """
        self.assertFalse(PayPalIPN.objects.exists())
        self.paypal_post(
            {
                "payment_date": b"2015-10-25 01:21:32",
                'charset': b(CHARSET),
                'txn_id': 'test',
            }
        )
        ppipn = PayPalIPN.objects.first()
        self.assertTrue(ppipn.flag)
        self.assertEqual(
            ppipn.flag_info,
            'Invalid form. (payment_date: Invalid date format '
            '2015-10-25 01:21:32: need more than 2 values to unpack)'
        )

        self.assertEqual(mail.outbox[0].to, [settings.SUPPORT_EMAIL])
        self.assertEqual(
            mail.outbox[0].subject,
            'WARNING! Error processing Invalid Payment Notification from PayPal'
        )
        self.assertEqual(
            mail.outbox[0].body,
            'PayPal sent an invalid transaction notification while attempting '
            'to process payment;.\n\nThe flag info was "Invalid form. '
            '(payment_date: Invalid date format '
            '2015-10-25 01:21:32: need more than 2 values to unpack)"'
            '\n\nAn additional error was raised: Unknown object for '
            'payment'
        )

    def test_paypal_notify_url_with_invalid_date_formats(self):
        """
        Check other invalid date formats
        %H:%M:%S %b. %d, %Y PDT is the expected format

        """
        # Fails because 25th cannot be convered to int
        self.paypal_post(
            {
                "payment_date": b"01:21:32 Jan 25th 2015 PDT",
                'charset': b(CHARSET),
                'txn_id': 'test'
            }
        )
        ppipn = PayPalIPN.objects.latest('id')
        self.assertTrue(ppipn.flag)
        self.assertEqual(
            ppipn.flag_info,
            "Invalid form. (payment_date: Invalid date format "
            "01:21:32 Jan 25th 2015 PDT: invalid literal for int() with "
            "base 10: '25th')"
        )

        # Fails because month is not in Mmm format
        self.paypal_post(
            {
                "payment_date": b"01:21:32 01 25 2015 PDT",
                'charset': b(CHARSET),
                'txn_id': 'test'
            }
        )
        ppipn = PayPalIPN.objects.latest('id')
        self.assertTrue(ppipn.flag)
        self.assertEqual(
            ppipn.flag_info,
            "Invalid form. (payment_date: Invalid date format "
            "01:21:32 01 25 2015 PDT: '01' is not in list)"
        )

        # Fails because month is not in Mmm format
        self.paypal_post(
            {
                "payment_date": b"01:21:32 January 25 2015 PDT",
                'charset': b(CHARSET),
                'txn_id': 'test'
            }
        )
        ppipn = PayPalIPN.objects.latest('id')
        self.assertTrue(ppipn.flag)
        self.assertEqual(
            ppipn.flag_info,
            "Invalid form. (payment_date: Invalid date format "
            "01:21:32 January 25 2015 PDT: 'January' is not in list)"
        )

        # Fails because year part cannot be convered to int
        self.paypal_post(
            {
                "payment_date": b"01:21:32 Jan 25 2015a PDT",
                'charset': b(CHARSET),
                'txn_id': 'test'
            }
        )
        ppipn = PayPalIPN.objects.latest('id')
        self.assertTrue(ppipn.flag)
        self.assertEqual(
            ppipn.flag_info,
            "Invalid form. (payment_date: Invalid date format "
            "01:21:32 Jan 25 2015a PDT: invalid literal for int() with "
            "base 10: '2015a')"
        )

        # No seconds part; fails on splitting the time
        self.paypal_post(
            {
                "payment_date": b"01:28 Jan 25 2015 PDT",
                'charset': b(CHARSET),
                'txn_id': 'test'
            }
        )
        ppipn = PayPalIPN.objects.latest('id')
        self.assertTrue(ppipn.flag)
        self.assertEqual(
            ppipn.flag_info,
            "Invalid form. (payment_date: Invalid date format "
            "01:28 Jan 25 2015 PDT: need more than 2 values to unpack)"
        )

        # Can be split and day/month/year parts converted but invalid date so
        #  conversion to datetime sails
        self.paypal_post(
            {
                "payment_date": b"01:21:32 Jan 49 2015 PDT",
                'charset': b(CHARSET),
                'txn_id': 'test'
            }
        )
        ppipn = PayPalIPN.objects.latest('id')
        self.assertTrue(ppipn.flag)
        self.assertEqual(
            ppipn.flag_info,
            "Invalid form. (payment_date: Invalid date format "
            "01:21:32 Jan 49 2015 PDT: day is out of range for month)"
        )

    @patch('paypal.standard.ipn.models.PayPalIPN._postback')
    def test_payment_received_with_duplicate_txn_flag(self, mock_postback):
        """
        If we get a flagged completed payment, send a warning email.  Most
        likely to happen with a duplicate transaction id
        """
        mock_postback.return_value = b"VERIFIED"
        order = mommy.make(Order)
        pptrans = helpers.create_paypal_transaction(order.user, order)
        # make an existing completed paypal ipn
        mommy.make(PayPalIPN, txn_id='test_txn_id', payment_status='Completed')
        self.assertEqual(PayPalIPN.objects.count(), 1)

        params = dict(IPN_POST_PARAMS)
        params.update(
            {
                'custom': b('{}'.format(order.id)),
                'invoice': b(pptrans.invoice_id),
                'txn_id': 'test_txn_id'
            }
        )
        self.paypal_post(params)
        order.refresh_from_db()
        ppipn = PayPalIPN.objects.all()[0]
        ppipn1 = PayPalIPN.objects.all()[1]

        self.assertFalse(ppipn.flag)
        self.assertTrue(ppipn1.flag)
        self.assertEqual(ppipn1.flag_info, 'Duplicate txn_id. (test_txn_id)')

        # even if the postback is verified, it is flagged and processed as
        # invalid
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(
            mail.outbox[0].subject,
            'WARNING! Invalid Payment Notification received from PayPal'
        )

    @patch('paypal.standard.ipn.models.PayPalIPN._postback')
    @patch('payments.models.send_processed_payment_emails')
    def test_error_sending_emails_payment_received(
            self, mock_send_emails, mock_postback
    ):
        """
        We send a warning email with the exception if anything else goes wrong
        during the payment processing; most likely to be something wrong with
        sending the emails
        """
        mock_send_emails.side_effect = Exception('Error sending mail')
        mock_postback.return_value = b"VERIFIED"

        order = mommy.make(Order)
        pptrans = helpers.create_paypal_transaction(order.user, order)

        params = dict(IPN_POST_PARAMS)
        params.update(
            {
                'custom': b('{}'.format(order.id)),
                'invoice': b(pptrans.invoice_id),
                'txn_id': 'test_txn_id'
            }
        )
        self.paypal_post(params)
        order.refresh_from_db()

        ppipn = PayPalIPN.objects.first()
        self.assertFalse(ppipn.flag)

        # even if the postback is verified, it is flagged and processed as
        # invalid
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(
            mail.outbox[0].subject,
            '{} There was some problem processing payment for order id {}'.format(
                settings.ACCOUNT_EMAIL_SUBJECT_PREFIX, order.id
            ),
        )

        self.assertEqual(
            mail.outbox[0].body,
            'Please check your order and paypal records for invoice # {}, '
            'paypal transaction id test_txn_id.\n\nThe exception '
            'raised was "Error sending mail"'.format(pptrans.invoice_id)
        )

    @patch('payments.models.send_mail')
    def test_error_sending_emails_payment_not_received(self, mock_send_emails):
        """
        We send a warning email with the exception if anything else goes wrong
        during the payment processing; most likely to be something wrong with
        sending the emails, so we need to check the logs
        """
        mock_send_emails.side_effect = Exception('Error sending mail')
        payment_models_logger.warning = Mock()

        user = mommy.make(User)
        order = mommy.make(Order, user=user)
        pptrans = helpers.create_paypal_transaction(order.user, order)

        params = dict(IPN_POST_PARAMS)
        params.update(
            {
                'custom': b('{}'.format(order.id)),
                'invoice': b(pptrans.invoice_id),
                'txn_id': 'test_txn_id'
            }
        )

        with self.assertRaises(Exception):
            self.paypal_post(params)
            payment_models_logger.warning.assert_called_with(
                'Problem processing payment_not_received for order {}; '
                'invoice_id {}, transaction id: test_txn_id. Exception: '
                'Error sending mail'.format(order.id, pptrans.invoice)
            )

        order.refresh_from_db()
        ppipn = PayPalIPN.objects.first()

        self.assertTrue(ppipn.flag)
        self.assertEqual(ppipn.flag_info, 'Invalid postback. (INVALID)')

    # @patch('paypal.standard.ipn.models.PayPalIPN._postback')
    # def test_paypal_notify_with_voucher_code(self, mock_postback):
    #     mock_postback.return_value = b"VERIFIED"
    #     product = mommy.make(Product)
    #     voucher = mommy.make(Voucher, code='test', discount=10)
    #     voucher.products.add(product)
    #     user = mommy.make(User)
    #     order = mommy.make(Order, user=user)
    #     pptrans = helpers.create_paypal_transaction(order.user, order)
    #
    #     self.assertFalse(PayPalIPN.objects.exists())
    #     params = dict(IPN_POST_PARAMS)
    #     params.update(
    #         {
    #             'custom': b('{} {}'.format(order.id, voucher.code)),
    #             'invoice': b(pptrans.invoice_id),
    #             'txn_id': b'test_txn_id',
    #         }
    #     )
    #     self.assertIsNone(pptrans.transaction_id)
    #     self.paypal_post(params)
    #     self.assertEqual(PayPalIPN.objects.count(), 1)
    #     ppipn = PayPalIPN.objects.first()
    #     self.assertFalse(ppipn.flag)
    #     self.assertEqual(ppipn.flag_info, '')
    #
    #     order.refresh_from_db()
    #     self.assertTrue(ordder.paid)
    #
    #     pptrans.refresh_from_db()
    #     self.assertEqual(pptrans.voucher_code, voucher.code)
    #     self.assertEqual(voucher.users.count(), 1)
    #     self.assertEqual(voucher.users.first(), user)
    #
    # @patch('paypal.standard.ipn.models.PayPalIPN._postback')
    # def test_paypal_notify_with_invalid_voucher_code(self, mock_postback):
    #     """
    #     Test that paypal is processed properly and marked as paid if an
    #     invalid voucher code is included. Warning mail sent to support.
    #     """
    #     mock_postback.return_value = b"VERIFIED"
    #
    #     user = mommy.make(User)
    #     order = mommy.make(Order, user=user)
    #     pptrans = helpers.create_paypal_transaction(order.user, order)
    #
    #     self.assertFalse(PayPalIPN.objects.exists())
    #     params = dict(IPN_POST_PARAMS)
    #     params.update(
    #         {
    #             'custom': b('{} invalid_code'.format(order.id)),
    #             'invoice': b(pptrans.invoice_id),
    #             'txn_id': b'test_txn_id',
    #         }
    #     )
    #     self.assertIsNone(pptrans.transaction_id)
    #     self.paypal_post(params)
    #     self.assertEqual(PayPalIPN.objects.count(), 1)
    #     ppipn = PayPalIPN.objects.first()
    #     self.assertFalse(ppipn.flag)
    #     self.assertEqual(ppipn.flag_info, '')
    #
    #     order.refresh_from_db()
    #     self.assertTrue(order.paid)
    #
    #     # email to user, studio, and support email
    #     self.assertEqual(len(mail.outbox), 3)
    #     support_email = mail.outbox[2]
    #     self.assertEqual(support_email.to, [settings.SUPPORT_EMAIL])
    #     self.assertEqual(
    #         support_email.subject,
    #         '{} There was some problem processing payment for order '
    #         'id {}'.format(settings.ACCOUNT_EMAIL_SUBJECT_PREFIX, order.id)
    #     )
    #     self.assertIn(
    #         'The exception raised was "Voucher matching query does not exist.',
    #         support_email.body
    #     )

    @patch('paypal.standard.ipn.models.PayPalIPN._postback')
    def test_paypal_notify_with_mismatched_receiver_email(self, mock_postback):
        """
        Test that error is raised if receiver email doesn't match object's
        paypal_email. Warning mail sent to support.
        """
        mock_postback.return_value = b"VERIFIED"

        user = mommy.make(User)
        order = mommy.make(Order, user=user, paypal_email='test@test.com')
        pptrans = helpers.create_paypal_transaction(order.user, order)

        self.assertFalse(PayPalIPN.objects.exists())
        params = dict(IPN_POST_PARAMS)
        params.update(
            {
                'custom': b(' {}'.format(order.id)),
                'invoice': b(pptrans.invoice_id),
                'txn_id': b'test_txn_id',
            }
        )
        self.assertIsNone(pptrans.transaction_id)
        self.paypal_post(params)
        self.assertEqual(PayPalIPN.objects.count(), 1)
        ppipn = PayPalIPN.objects.first()
        self.assertTrue(ppipn.flag)
        self.assertEqual(
            ppipn.flag_info,
            'Invalid receiver_email ({})'.format(TEST_RECEIVER_EMAIL)
        )

        order.refresh_from_db()
        self.assertFalse(order.paid)

        # email to user, studio, and support email
        self.assertEqual(len(mail.outbox), 1)
        support_email = mail.outbox[0]
        self.assertEqual(support_email.to, [settings.SUPPORT_EMAIL])
        self.assertEqual(
            support_email.subject,
            '{} There was some problem processing payment for order '
            'id {}'.format(settings.ACCOUNT_EMAIL_SUBJECT_PREFIX, order.id)
        )
        self.assertIn(
            'The exception raised was '
            '"Invalid receiver_email ({})'.format(TEST_RECEIVER_EMAIL),
            support_email.body
        )

    @patch('paypal.standard.ipn.models.PayPalIPN._postback')
    def test_paypal_notify_with_pending_payment_status(self, mock_postback):
        """
        Test that error is raised and warning mail sent to support for a
        payment status that is not Completed or Refunded.
        """
        mock_postback.return_value = b"VERIFIED"

        user = mommy.make(User)
        order = mommy.make(Order, user=user)
        pptrans = helpers.create_paypal_transaction(order.user, order)

        self.assertFalse(PayPalIPN.objects.exists())
        params = dict(IPN_POST_PARAMS)
        params.update(
            {
                'custom': b('{}'.format(order.id)),
                'invoice': b(pptrans.invoice_id),
                'txn_id': b'test_txn_id',
                'payment_status': 'Pending'
            }
        )
        self.assertIsNone(pptrans.transaction_id)
        self.paypal_post(params)
        self.assertEqual(PayPalIPN.objects.count(), 1)
        ppipn = PayPalIPN.objects.first()

        order.refresh_from_db()
        self.assertFalse(order.paid)

        # email to support email
        self.assertEqual(len(mail.outbox), 1)
        support_email = mail.outbox[0]
        self.assertEqual(support_email.to, [settings.SUPPORT_EMAIL])
        self.assertEqual(
            support_email.subject,
            '{} There was some problem processing payment for order '
            'id {}'.format(settings.ACCOUNT_EMAIL_SUBJECT_PREFIX, order.id)
        )
        self.assertIn(
            'The exception raised was "PayPal payment returned with '
            'status PENDING for order {}; '
            'ipn obj id {} (txn id {}).  This is usually due to an '
            'unrecognised or unverified paypal email address.'.format(
                order.id, ppipn.id, ppipn.txn_id
            ),
            support_email.body
        )

    @patch('paypal.standard.ipn.models.PayPalIPN._postback')
    def test_paypal_notify_with_unexpected_payment_status(self, mock_postback):
        """
        Test that error is raised and warning mail sent to support for a
        payment status that is not Completed or Refunded.
        """
        mock_postback.return_value = b"VERIFIED"

        user = mommy.make(User)
        order = mommy.make(Order, user=user)
        pptrans = helpers.create_paypal_transaction(order.user, order)

        self.assertFalse(PayPalIPN.objects.exists())
        params = dict(IPN_POST_PARAMS)
        params.update(
            {
                'custom': b('{}'.format(order.id)),
                'invoice': b(pptrans.invoice_id),
                'txn_id': b'test_txn_id',
                'payment_status': 'Voided'
            }
        )
        self.assertIsNone(pptrans.transaction_id)
        self.paypal_post(params)
        self.assertEqual(PayPalIPN.objects.count(), 1)
        ppipn = PayPalIPN.objects.first()

        order.refresh_from_db()
        self.assertFalse(order.paid)

        # email to support email
        self.assertEqual(len(mail.outbox), 1)
        support_email = mail.outbox[0]
        self.assertEqual(support_email.to, [settings.SUPPORT_EMAIL])
        self.assertEqual(
            support_email.subject,
            '{} There was some problem processing payment for order '
            'id {}'.format(settings.ACCOUNT_EMAIL_SUBJECT_PREFIX, order.id)
        )
        self.assertIn(
            'The exception raised was "Unexpected payment status VOIDED for '
            'order {}; ipn obj id {} (txn id {})'.format(
                order.id, ppipn.id, ppipn.txn_id
            ),
            support_email.body
        )
