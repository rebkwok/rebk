from model_mommy import mommy

from django.core.urlresolvers import reverse
from django.test import TestCase

from orders.models import Order

from paypal.standard.ipn.models import PayPalIPN


class TestViews(TestCase):

    def test_confirm_return(self):

        order = mommy.make(Order)

        url = reverse('payments:paypal_confirm')
        resp = self.client.post(
            url,
            {
                'custom': '{}'.format(order.id),
                'payment_status': 'paid',
                'item_name': 'order'
            }
        )
        self.assertEquals(resp.status_code, 200)
        self.assertEquals(resp.context_data['obj'], order)

    def test_confirm_return_with_unknown_obj(self):
        url = reverse('payments:paypal_confirm')
        resp = self.client.post(
            url,
            {
                'custom': 'other',
                'payment_status': 'paid',
                'item_name': 'order'
            }
        )
        self.assertEquals(resp.status_code, 200)
        self.assertEquals(resp.context_data['obj_unknown'], True)
        self.assertIn(
            'Everything is probably fine...',
            resp.rendered_content
        )


    def test_confirm_return_with_no_custom_field(self):
        url = reverse('payments:paypal_confirm')
        resp = self.client.post(
            url,
            {
                'payment_status': 'paid',
            }
        )
        self.assertEquals(resp.status_code, 200)
        self.assertEquals(resp.context_data['obj_unknown'], True)
        self.assertIn(
            'Everything is probably fine...',
            resp.rendered_content
        )

    def test_cancel_return(self):
        url = reverse('payments:paypal_cancel')
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 200)
