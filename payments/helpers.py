import random

from payments.models import PaypalOrderTransaction


def create_paypal_transaction(user, order):
    id_string = "order"  # todo create based on order id
    existing = PaypalOrderTransaction.objects.filter(
        invoice_id__contains=id_string, order=order).order_by('-invoice_id')

    if existing:
        # PaypalOrderTransaction is created when the view is called, not when
        # payment is made.  If there is no transaction id stored against it,
        # we shouldn't need to make a new one
        for transaction in existing:
            if not transaction.transaction_id:
                return transaction
        existing_counter = existing[0].invoice_id[-3:]
        counter = str(int(existing_counter) + 1).zfill(len(existing_counter))
    else:
        counter = '001'

    invoice_id = id_string + counter
    existing_inv = PaypalOrderTransaction.objects.filter(
        invoice_id=invoice_id
    )
    if existing_inv:
        # in case we already have the same invoice id for a different
        # booking (the check for existing above checked for this exact
        # combination of invoice id and booking
        random_prefix = random.randrange(100, 999)
        invoice_id = id_string + str(random_prefix) + counter

    pbt = PaypalOrderTransaction.objects.create(
        invoice_id=invoice_id, order=order
    )
    return pbt
