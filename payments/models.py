# -*- coding: utf-8 -*-

import logging

from django.db import models
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone
from django.template.loader import get_template

from paypal.standard.models import ST_PP_COMPLETED, ST_PP_REFUNDED, \
    ST_PP_PENDING
from paypal.standard.ipn.signals import valid_ipn_received, invalid_ipn_received

from orders.models import Order

from activitylog.models import ActivityLog


logger = logging.getLogger(__name__)


class PayPalTransactionError(Exception):
    pass


class PaypalOrderTransaction(models.Model):
    invoice_id = models.CharField(max_length=255, null=True, blank=True, unique=True)
    booking = models.ForeignKey(Order, null=True)
    transaction_id = models.CharField(max_length=255, null=True, blank=True, unique=True)
    voucher_code = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return self.invoice_id


def send_processed_payment_emails(obj_id, paypal_trans, user, obj):
    ctx = {
        'user': " ".join([user.first_name, user.last_name]),
        'obj': obj,
        'invoice_id': paypal_trans.invoice_id,
        'paypal_transaction_id': paypal_trans.transaction_id,
        'paypal_email': obj.paypal_email
    }

    # send email to studio
    if settings.SEND_ALL_STUDIO_EMAILS:
        send_mail(
            '{} Payment processed for order id {}'.format(
                settings.ACCOUNT_EMAIL_SUBJECT_PREFIX, obj_id),
            get_template(
                'payments/email/payment_processed_to_studio.txt').render(ctx),
            settings.DEFAULT_FROM_EMAIL,
            [settings.DEFAULT_STUDIO_EMAIL],
            html_message=get_template(
                'payments/email/payment_processed_to_studio.html').render(ctx),
            fail_silently=False)

    # send email to user
    send_mail(
        '{} Payment processed for order id {}'.format(
            settings.ACCOUNT_EMAIL_SUBJECT_PREFIX, obj_id),
        get_template(
            'payments/email/payment_processed_to_user.txt').render(ctx),
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        html_message=get_template(
            'payments/email/payment_processed_to_user.html').render(ctx),
        fail_silently=False)


def send_processed_refund_emails(obj_id, paypal_trans, user, obj):
    ctx = {
        'user': " ".join([user.first_name, user.last_name]),
        'obj': obj,
        'invoice_id': paypal_trans.invoice_id,
        'paypal_transaction_id': paypal_trans.transaction_id,
        'paypal_email': obj.paypal_email
    }
    # send email to studio only and to support for checking;
    # user will have received automated paypal payment
    send_mail(
        '{} Payment refund processed for order id {}'.format(
            settings.ACCOUNT_EMAIL_SUBJECT_PREFIX, obj_id),
        get_template(
            'payments/email/payment_refund_processed_to_studio.txt'
        ).render(ctx),
        settings.DEFAULT_FROM_EMAIL,
        [settings.DEFAULT_STUDIO_EMAIL, settings.SUPPORT_EMAIL],
        html_message=get_template(
            'payments/email/payment_refund_processed_to_studio.html'
        ).render(ctx),
        fail_silently=False)


def get_obj(ipn_obj):
    from payments import helpers
    try:
        custom = ipn_obj.custom.split()
        obj_id = int(custom[0])
        voucher_code = custom[1] if len(custom) == 2 else None
    except IndexError:  # in case custom not included in paypal response
        raise PayPalTransactionError('Unknown object for payment')

    try:
        obj = Order.objects.get(id=obj_id)
    except Order.DoesNotExist:
        raise PayPalTransactionError(
            'Order with id {} does not exist'.format(obj_id)
        )

    paypal_trans = PaypalOrderTransaction.objects.filter(order=obj)
    if not paypal_trans:
        paypal_trans = helpers.create_paypal_transaction(
            user=obj.user, order=obj
        )
    elif paypal_trans.count() > 1:
        # we may have two ppb transactions created if user changed their
        # username between ordering and paying (invoice_id is created and
        # retrieved using username)
        if ipn_obj.invoice:
            paypal_trans = PaypalOrderTransaction.objects.get(
                order=obj, invoice_id=ipn_obj.invoice
            )
        else:
            paypal_trans = paypal_trans.latest('id')
    else:  # we got one paypaltrans, as we should have
        paypal_trans = paypal_trans[0]

    return {
        'obj': obj,
        'paypal_trans': paypal_trans,
        'voucher_code': voucher_code,
    }


def payment_received(sender, **kwargs):
    ipn_obj = sender

    try:
        obj_dict = get_obj(ipn_obj)
    except PayPalTransactionError as e:
        send_mail(
        'WARNING! Error processing PayPal IPN',
        'Valid Payment Notification received from PayPal but an error '
        'occurred during processing.\n\nTransaction id {}\n\nThe flag info '
        'was "{}"\n\nError raised: {}'.format(
            ipn_obj.txn_id, ipn_obj.flag_info, e
        ),
        settings.DEFAULT_FROM_EMAIL, [settings.SUPPORT_EMAIL],
        fail_silently=False)
        logger.error(
            'PaypalTransactionError: unknown object type for payment '
            '(ipn_obj transaction_id: {}, error: {})'.format(
                ipn_obj.txn_id, e
            )
        )
        return

    obj = obj_dict['obj']
    paypal_trans = obj_dict['paypal_trans']
    voucher_code = obj_dict.get('voucher_code')
    additional_data = obj_dict.get('additional_data')

    try:
        if obj.paypal_email != ipn_obj.receiver_email:
            ipn_obj.set_flag(
                "Invalid receiver_email (%s)" % ipn_obj.receiver_email
            )
            ipn_obj.save()
            raise PayPalTransactionError(ipn_obj.flag_info)

        if ipn_obj.payment_status == ST_PP_REFUNDED:
            obj.paid = False
            obj.save()

            ActivityLog.objects.create(
                log='Order id {} for user {} has been refunded from paypal; '
                    'paypal transaction id {}, invoice id {}'.format(
                    obj.id, obj.user.username,
                    ipn_obj.txn_id, paypal_trans.invoice_id
                    )
            )
            send_processed_refund_emails(
                obj.id, paypal_trans, obj.user, obj
            )

        elif ipn_obj.payment_status == ST_PP_PENDING:
            ActivityLog.objects.create(
                log='PayPal payment returned with status PENDING for order {}; '
                    'ipn obj id {} (txn id {})'.format(
                     obj.id, ipn_obj.id, ipn_obj.txn_id
                    )
            )
            raise PayPalTransactionError(
                'PayPal payment returned with status PENDING for order {}; '
                'ipn obj id {} (txn id {}).  This is usually due to an '
                'unrecognised or unverified paypal email address.'.format(
                    obj.id, ipn_obj.id, ipn_obj.txn_id
                )
            )

        elif ipn_obj.payment_status == ST_PP_COMPLETED:
            # we only process if payment status is completed
            # check for django-paypal flags (checks for valid payment status,
            # duplicate trans id, correct receiver email, valid secret (if using
            # encrypted), mc_gross, mc_currency, item_name and item_number are all
            # correct
            obj.paid = True
            obj.save()

            # do this AFTER saving the booking as paid; in the edge case that a
            # user re-requests the page with the paypal button on it in between
            # booking and the paypal transaction being saved, this prevents a
            # second invoice number being generated
            # SCENARIO 1 (how we did it before): paypal trans id saved first;
            # user requests page when booking still marked as unpaid -->
            # renders paypal button and generates new invoice # because
            # retrieved paypal trans already has a txn_id stored against it.
            # Paypal will allow the booking to be paid twice because the
            # invoice number is different
            # SCENARIO: booking saved first; user requests page when paypal
            # trans not updated yet --> booking is marked as paid so doesn't
            # render the paypal button at all
            paypal_trans.transaction_id = ipn_obj.txn_id
            paypal_trans.save()

            ActivityLog.objects.create(
                log='Order id {} for user {} paid by PayPal; paypal '
                    'transaction id {}'.format(
                    obj.id, obj.user.username,  paypal_trans.id,
                    '(paypal email {})'.format((obj.paypal_email)
                    )
                )
            )

            send_processed_payment_emails(obj.id, paypal_trans, obj.user, obj)

            if voucher_code:
                voucher = Voucher.objects.get(code=voucher_code)
                voucher.users.add(obj.user)
                paypal_trans.voucher_code = voucher_code
                paypal_trans.save()

                ActivityLog.objects.create(
                    log='Voucher code {} used for order id {} by user {}'.format(
                        voucher_code, obj.id, obj.user.username
                    )
                )

                if not ipn_obj.invoice:
                    # sometimes paypal doesn't send back the invoice id -
                    # everything should be ok but email to check
                    ipn_obj.invoice = paypal_trans.invoice_id
                    ipn_obj.save()
                    send_mail(
                        '{} No invoice number on paypal ipn for '
                        'order id {}'.format(
                            settings.ACCOUNT_EMAIL_SUBJECT_PREFIX, obj.id
                        ),
                        'Please check booking and paypal records for '
                        'paypal transaction id {}.  No invoice number on paypal'
                        ' IPN.  Invoice number has been set to {}.'.format(
                            ipn_obj.txn_id, paypal_trans.invoice_id
                        ),
                        settings.DEFAULT_FROM_EMAIL,
                        [settings.SUPPORT_EMAIL],
                        fail_silently=False
                    )

        else:  # any other status
            ActivityLog.objects.create(
                log='Unexpected payment status {} for order {}; '
                    'ipn obj id {} (txn id {})'.format(
                     obj.id,
                     ipn_obj.payment_status.upper(), ipn_obj.id, ipn_obj.txn_id
                    )
            )
            raise PayPalTransactionError(
                'Unexpected payment status {} for order {}; ipn obj id {} '
                '(txn id {})'.format(
                    ipn_obj.payment_status.upper(), obj.id,
                    ipn_obj.id, ipn_obj.txn_id
                )
            )

    except Exception as e:
        # if anything else goes wrong, send a warning email
        logger.warning(
            'Problem processing payment for order {}; invoice_id {}, transaction '
            'id: {}.  Exception: {}'.format(
                obj.id, ipn_obj.invoice, ipn_obj.txn_id, e
            )
        )

        send_mail(
            '{} There was some problem processing payment for '
            'order id {}'.format(settings.ACCOUNT_EMAIL_SUBJECT_PREFIX, obj.id),
            'Please check your booking and paypal records for '
            'invoice # {}, paypal transaction id {}.\n\nThe exception '
            'raised was "{}"'.format(
                ipn_obj.invoice, ipn_obj.txn_id, e
            ),
            settings.DEFAULT_FROM_EMAIL,
            [settings.SUPPORT_EMAIL],
            fail_silently=False)


def payment_not_received(sender, **kwargs):
    ipn_obj = sender

    try:
        obj_dict = get_obj(ipn_obj)
    except PayPalTransactionError as e:
        send_mail(
            'WARNING! Error processing Invalid Payment Notification from PayPal',
            'PayPal sent an invalid transaction notification while '
            'attempting to process payment;.\n\nThe flag '
            'info was "{}"\n\nAn additional error was raised: {}'.format(
                ipn_obj.flag_info, e
            ),
            settings.DEFAULT_FROM_EMAIL, [settings.SUPPORT_EMAIL],
            fail_silently=False)
        logger.error(
            'PaypalTransactionError: unknown object for payment ('
            'transaction_id: {}, error: {})'.format(ipn_obj.txn_id, e)
        )
        return

    try:
        obj = obj_dict.get('obj')

        if obj:
            logger.warning('Invalid Payment Notification received from PayPal '
                           'for order id {}'.format(obj.id)
                )
            send_mail(
                'WARNING! Invalid Payment Notification received from PayPal',
                'PayPal sent an invalid transaction notification while '
                'attempting to process payment for order id {}.\n\nThe flag '
                'info was "{}"'.format(obj.id, ipn_obj.flag_info),
                settings.DEFAULT_FROM_EMAIL, [settings.SUPPORT_EMAIL],
                fail_silently=False)

    except Exception as e:
            # if anything else goes wrong, send a warning email
            logger.warning(
                'Problem processing payment_not_received for order id {}; '
                'invoice_id {}, transaction id: {}. Exception: {}'.format(
                    obj.id, ipn_obj.invoice, ipn_obj.txn_id, e
                )
            )
            send_mail(
                '{} There was some problem processing payment_not_received for '
                'order id {}'.format(
                    settings.ACCOUNT_EMAIL_SUBJECT_PREFIX, obj.id
                ),
                'Please check your order and paypal records for '
                'invoice # {}, paypal transaction id {}.\n\nThe exception '
                'raised was "{}".\n\nNOTE: this error occurred during '
                'processing of the payment_not_received signal'.format(
                    ipn_obj.invoice, ipn_obj.txn_id, e
                ),
                settings.DEFAULT_FROM_EMAIL,
                [settings.SUPPORT_EMAIL],
                fail_silently=False)

valid_ipn_received.connect(payment_received)
invalid_ipn_received.connect(payment_not_received)
