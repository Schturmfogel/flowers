# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.forms.fields import CharField
from django.forms import widgets
from django.template import Engine
from django.template.loader import select_template
from django.utils.html import strip_tags
from django.utils.safestring import mark_safe
from django.utils.text import Truncator
from django.utils.translation import ugettext_lazy as _
try:
	from html.parser import HTMLParser   # python3
except ImportError:
	from HTMLParser import HTMLParser   # python2
from cms.plugin_pool import plugin_pool
from djangocms_text_ckeditor.widgets import TextEditorWidget
from djangocms_text_ckeditor.utils import plugin_tags_to_user_html
from cmsplugin_cascade.fields import GlossaryField
from cmsplugin_cascade.link.cms_plugins import TextLinkPlugin
from cmsplugin_cascade.link.forms import LinkForm, TextLinkFormMixin
from cmsplugin_cascade.link.plugin_base import LinkElementMixin
from cmsplugin_cascade.mixins import TransparentMixin
from cmsplugin_cascade.bootstrap3.buttons import BootstrapButtonMixin
from shop import settings as shop_settings
from shop.models.cart import CartModel
from shop.modifiers.pool import cart_modifiers_pool
from shop.cascade.plugin_base import ShopPluginBase, ShopButtonPluginBase, DialogFormPluginBase


class ProceedButtonForm(TextLinkFormMixin, LinkForm):
	link_content = CharField(label=_("Button Content"))
	LINK_TYPE_CHOICES = (('cmspage', _("CMS Page")), ('RELOAD_PAGE', _("Reload Page")),
		('PURCHASE_NOW', _("Purchase Now")),)


class ShopProceedButton(BootstrapButtonMixin, ShopButtonPluginBase):
	name = _("Proceed Button")
	parent_classes = ('BootstrapColumnPlugin', 'ProcessStepPlugin', 'ValidateSetOfFormsPlugin')
	model_mixins = (LinkElementMixin)
	glossary_field_order = ('button_type', 'button_size', 'button_options', 'quick_float',
		'icon_left', 'icon_right')

	def get_form(self, request, obj=None, **kwargs):
		kwargs.update(form=ProceedButtonForm)
		return super(ShopProceedButton, self).get_form(request, obj, **kwargs)

	def get_render_template(self, context, instance, placeholder):
		template_names = [
			'{}/checkout/proceed-button.html'.format(shop_settings.APP_LABEL),
			'shop/checkout/proceed-button.html']
		return select_template(template_names)

	def render(self, context, instance, placeholder):
		super(ShopProceedButton, self).render(context, instance, placeholder)
		try:
			cart = CartModel.objects.get_from_request(context['request'])
			cart.update(context['request'])
			context['cart'] = cart
		except CartModel.DoesNotExist:
			pass
		return context

plugin_pool.register_plugin(ShopProceedButton)


class CustomerFormPluginBase(DialogFormPluginBase):
	template_leaf_name = 'customer-{}.html'
	cache = False

	def get_form_data(self, context, instance, placeholder):
		form_data = super(CustomerFormPluginBase, self).get_form_data(context, instance, placeholder)
		form_data.update(instance=context['request'].customer)
		return form_data

	def get_render_template(self, context, instance, placeholder):
		if 'error_message' in context:
			return Engine().from_string('<p class="text-danger">{{ error_message }}</p>')
		return super(CustomerFormPluginBase, self).get_render_template(context, instance, placeholder)


class CustomerFormPlugin(CustomerFormPluginBase):
	name = _("Customer Form")
	form_class = 'shop.forms.checkout.CustomerForm'

	def render(self, context, instance, placeholder):
		if not context['request'].customer.is_registered():
			context['error_message'] = _("Only registered customers can access this form.")
			return context
		return super(CustomerFormPlugin, self).render(context, instance, placeholder)

DialogFormPluginBase.register_plugin(CustomerFormPlugin)


class GuestFormPlugin(CustomerFormPluginBase):
	name = _("Guest Form")
	form_class = 'shop.forms.checkout.GuestForm'

	def render(self, context, instance, placeholder):
		if not context['customer'].is_guest():
			context['error_message'] = _("Only guest customers can access this form.")
			return context
		return super(GuestFormPlugin, self).render(context, instance, placeholder)

DialogFormPluginBase.register_plugin(GuestFormPlugin)
