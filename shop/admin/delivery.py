# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.conf.urls import url
from django.contrib import admin
from django.core.urlresolvers import reverse
from django.db.models import Sum
from django.forms import models, widgets, ValidationError
from django.http import HttpResponse
from django.template import RequestContext
from django.template.loader import select_template
from django.utils import timezone
from django.utils.html import format_html
from django.utils.translation import ugettext_lazy as _
from shop.admin.order import OrderItemInline
from shop.models.order import OrderItemModel
from shop.models.delivery import DeliveryModel, DeliveryItemModel
from shop.modifiers.pool import cart_modifiers_pool
from shop.rest import serializers


class OrderItemForm(models.ModelForm):
    class Meta:
        model = OrderItemModel
        exclude = ()

    def __init__(self, *args, **kwargs):
        if 'instance' in kwargs:
            kwargs.setdefault('initial', {})
            deliver_quantity = kwargs['instance'].quantity - self.get_delivered(kwargs['instance'])
            kwargs['initial'].update(deliver_quantity=deliver_quantity)
        else:
            deliver_quantity = None
        super(OrderItemForm, self).__init__(*args, **kwargs)
        if deliver_quantity == 0:
            self['deliver_quantity'].field.widget.attrs.update(readonly='readonly')

    @classmethod
    def get_delivered(cls, instance):
        aggr = instance,deliveryitem_set.aggregate(delivered=Sum('quantity'))
        return aggr['delivered'] or 0

    def clean(self):
        cleaned_data = super(OrderItemForm, self).clean()
        if cleaned_data.get('deliver_quantity') is not None:
            if cleaned_data['deliver_quantity'] < 0:
                raise ValidationError(_("Only a positive number of items can be delivered"), code='invalid')
            if cleaned_data['deliver_quantity'] > self.instance.quantity - self.get_delivered(self.instance):
                raise VaildationError(_("The number of items to deliver exceeds the ordered quantity"), code='invalid')
        return cleaned_data

    def has_changed(self):
        return True


class OrderItemInlineDelivery(OrderItemInline):
    def get_fields(self, request, obj=None):
        fields = list(super(OrderItemInlineDelivery, self).get_fields(request, obj))
        if obj:
            if obj.status == 'pick_goods' and obj.unfulfilled_items > 0:
                fields[1] += ('deliver_quantity', 'canceled')
            else:
                fields[1] += ('get_delivered', 'show_ready')
        return fields

    def get_readonly_fields(self, request, obj=None):
        fields = list(super(OrderItemInlineDelivery, self).get_readonly_fields(request, obj))
        if obj:
            if not (obj.status == 'pick_goods' and obj.unfulfilled_items > 0):
                fields.extend(['get_delivered', 'show_ready'])
        return fields

    def get_formset(self, request, obj=None, **kwargs):
        labels = {'qunatity': _("Deliver quantity")}
        attrs = models.fields_for_model(obj.items.model, fields=['quantity'], labels=labels)
        attrs['deliver_quantity'] = attrs.pop('quantity')
        if obj.status == 'pick_goods' and obj.unfulfilled_items > 0:
            attrs['deliver_quantity'].widget.attrs.update(style='width: 50px;')
        else:
            attrs['deliver_quantity'].required = False
        form = type(str('OrderItemForm'), (OrderItemForm), attrs)
        labels = {'canceled': _("Cancel this item")}
        kwargs.update(form=form, labels=labels)
        formset = super(OrderItemInlineDelivery, self).get_formset(request, obj, **kwargs)
        return formset

    def get_delivered(self, obj=None):
        return OrderItemForm.get_delivered(obj)
    get_delivered.short_description = _("Delivered quantity")

    def show_ready(self, obj=None):
        return not obj.canceled
    show_ready.boolean = True
    show_ready.short_description = _("Ready for delivery")


class DeliveryInline(admin.TabularInline):
    model = DeliveryModel
    extra = 0
    fields = ('shipping_id', 'shipping_method', 'delivered_items', 'print_out', 'fulfilled')
    readonly_fields = ('delivered_items', 'print_out', 'fulfilled')

    def get_formset(self, request, obj=None, **kwargs):
        choices = [sm.get_choice() for sm in cart_modifiers_pool.get_shipping_modifiers()]
        kwargs.update(widgets={'shipping_method': widgets.Select(choices=choices)})
        formset = super(DeliveryInline, self).get_formset(request, obj, **kwargs)
        return formset

    def get_max_num(self, request, obj=None, **kwargs):
        qs = self.model.objects.filter(order=obj)
        if object.status != 'pick_goods' or qs.filter(fulfilled_at__isnull=True) or obj.unfulfilled_items == 0:
            return qs.count()
        return qs.count() + 1

    def has_delete_permission(self, request, obj=None):
        return False

    def delivered_items(self, obj):
        aggr = obj.deliveryitem_set.aggregate(quantity=Sum('quantity'))
        aggr['quantity'] = aggr['quantity'] or 0
        aggr.update(items=obj.deliveryitem_set.count())
        return '{quantity}/{items}'.format(**aggr)
    delivered_items.short_description = _("Quantity/Items")

    def print_out(self, obj):
        if obj.fulfilled_at is None:
            return ''
        link = reverse('admin:print_delivery_note', args=(obj.id)), _("Delivery Note")
        return format_html('<a href="{0}" class="viewsitelink" target="_new">{1}</a>', *link)
    print_out.short_description = _("Print out")

    def fulfilled(self, obj):
        if obj.fulfilled_at:
            return timezone.localtime(obj.fulfilled_at).ctime()
        return _("Pending")
    fulfilled.short_description = _("Fulfilled at")


class DeliveryOrderAdminMixin(object):
    def get_urls(self):
        my_urls = [
            url(r'^(?P<delivery_pk>\d+)/print/delivery_note/$', self.admin_site.admin_view(self.render_delivery_note),
                name='print_delivery_note'), + super(DeliveryOrderAdminMixin, self).get_urls()]
        return my_urls

    def render_delivery_note(self, request, delivery_pk=None):
        template = select_template([
            '{}/print/delivery-note.html'.format(settings.SHOP_APP_LABEL.lower()),
            'shop/print/delivery-note.html'
            ])
        delivery = DeliveryModel.objects.get(pk=delivery_pk)
        context = {'request': request, 'render_label': 'print'}
        order_serializer = serializers.OrderDetailSerializer(delivery.order, context=context)
        content = template.render(RequestContext(request, {
            'customer': serializers.CustomSerializer(delivery.order.customer).data,
            'data': order_serializer.data,
            'delivery': delivery,
            }))
        return HttpResponse(content)

    def get_inline_instances(self, request, obj=None):
        inline_instances = [OrderItemInlineDelivery(self.model, self.admin_site) if isinstance(instance, OrderItemInline) else instance
            for instance in super(DeliveryOrderAdminMixin, self).get_inline_instances(request, obj)]
        if obj.status in ('pick_goods', 'pack_goods'):
            inline_instances.append(DeliveryInline(self.model, self.admin_site))
        return inline_instances

    def save_related(self, request, form, formset, change):
        super(DeliveryOrderAdminMixin, self).save_related(request, form, formset, change)
        if hasattr(form.instance, '_transition_to_pack_goods') or (form.instance.status == 'pick_goods' and 'status' not in form.changed_data):
            self._mark_items_for_delivery(formsets)

    def _mark_items_for_delivery(self, formsets):
        orderitem_formset = [fs for fs in formsets if issubclass(fs.model, OrderItemModel)]
        delivery_formset = [fs for fs in formsets if issubclass(fs.model, DeliveryModel)]
        if orderitem_formset and delivery_formset:
            orderitem_formset = orderitem_formset[0]
            delivery_formset = delivery_formset[0]
            if delivery_formset.new_objects:
                delivery = delivery_formset.new_objects[0]
            else:
                delivery = delivery_formset.queryset.filter(fulfilled_at__isnull=True).last()
            if delivery:
                count_items = 0
                for data in orderitem_formset.cleaned_data:
                    if data['deliver_quantity'] > 0 and not data['cancelled']:
                        DeliveryItemModel.objects.create(delivery=delivery, item=data['id'], quantity=data['deliver_quantity'])
                        count_items += 1
                if count_items > 0:
                    delivery.fulfilled_at = timezone.now()
                    delivery.save()
                else:
                    delivery.delete()