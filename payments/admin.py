from django.contrib import admin
from django.contrib.auth.models import User
from payments.models import PaypalOrderTransaction
from paypal.standard.ipn.models import PayPalIPN
from paypal.standard.ipn.admin import PayPalIPNAdmin


class PaypalUserFilter(admin.SimpleListFilter):

    title = 'User'
    parameter_name = 'user'

    def lookups(self, request, model_admin):
        qs = User.objects.all().order_by('first_name')
        return [
            (
                user.id,
                "{} {} ({})".format(
                    user.first_name, user.last_name, user.username
                )
             ) for user in qs
            ]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(order__user__id=self.value())
        return queryset


class PaypalOrderTransactionAdmin(admin.ModelAdmin):

    list_display = ('id', 'get_user', 'invoice_id', 'transaction_id')
    readonly_fields = ('id', 'order', 'get_user', 'invoice_id',
                       'get_order_id', 'cost', 'voucher_code')
    list_filter = (PaypalUserFilter,)

    def get_order_id(self, obj):
        return obj.order.id
    get_order_id.short_description = "Order id"

    def get_user(self, obj):
        return "{} {}".format(
            obj.booking.user.first_name, obj.order.user.last_name
        )
    get_user.short_description = "User"

    def cost(self, obj):
        return u"\u00A3{:.2f}".format(obj.order.event.cost)


class PayPalAdmin(PayPalIPNAdmin):

    search_fields = [
        "txn_id", "recurring_payment_id", 'custom', 'invoice',
        'first_name', 'last_name'
    ]
    list_display = [
        "txn_id", "flag", "flag_info", "invoice", "custom",
        "payment_status", "buyer", "created_at"
    ]

    def buyer(self, obj):
        return "{} {}".format(obj.first_name, obj.last_name)
    buyer.admin_order_field = 'first_name'


admin.site.register(PaypalOrderTransaction, PaypalOrderTransactionAdmin)
admin.site.register(
admin.site.unregister(PayPalIPN)
admin.site.register(PayPalIPN, PayPalAdmin)
