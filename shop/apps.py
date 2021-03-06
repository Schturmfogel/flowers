# ~*~ coding: utf-8 ~*~
from __future__ import unicode_literals

from django import get_version
from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _
from shop.deferred import ForeignKeyBuilder


class ShopConfig(AppConfig):
    name = 'shop'
    verbose_name = _("Shop")
    
    def ready(self):
        from django_fsm.signals import post_transition
        from shop.models.friends import JSONField
        from rest_framework.serializers import ModelSerializer
        from shop.rest.fields import JSONSerializerField
        from shop.models.notification import order_event_notification

        post_transition.connect(order_event_notification)

        ModelSerializer.serializer_field_mapping[JSONField] = JSONSerializerField

        ForeignKeyBuilder.check_for_pending_mappings()


def get_tuple_version(version=None):
    version = version or get_version()
    return tuple(map(lambda n: int(n), version.split('.')))
