# ~*~ coding: utf-8 ~*~
from __future__ import unicode_literals

from decimal import Decimal
from django.conf import settings

APP_LABEL = settings.SHOP_APP_LABEL

DEFAULT_CURRENCY = getattr(settings, 'SHOP_DEFAULT_CURRENCY', 'EUR')
MONEY_FORMAT = getattr(settings, 'SHOP_MONEY_FORMAT', '{symbol} {amount}')

USE_TZ = True
DECIMAL_PLACES = getattr(settings, 'SHOP_DECIMAL_PLACES', 2)

CART_MODIFIERS = getattr(settings, 'SHOP_CART_MODIFIERS', ('shop.modifiers.defaults.DefaultCartModifier',))
VALUE_ADDED_TAX = getattr(settings, 'SHOP_VALUE_ADDED_TAX', Decimal('20'))
ORDER_WORKFLOWS = getattr(settings, 'SHOP_ORDER_WORKFLOWS', ())

ADD2CART_NG_MODEL_OPTIONS = getattr(settings, 'SHOP_ADD2CART_NG_MODEL_OPTIONS', "{updateOn: 'default blur', debounce: {'default': 500, 'blur': 0}}")
EDITCART_NG_MODEL_OPTIONS = getattr(settings, 'SHOP_EDITCART_NG_MODEL_OPTIONS', "{updateOn: 'default blur', debounce: {'default': 500, 'blur': 0}}")

GUEST_IS_ACTIVE_USER = getattr(settings, 'SHOP_GUEST_IS_ACTIVE_USER', False)

CACHE_DURATIONS = {
    'product_html_snippet': 86400,
}
CACHE_DURATIONS.update(getattr(settings, 'SHOP_CACHE_DURATIONS', {}))