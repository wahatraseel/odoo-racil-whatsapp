# -*- coding: utf-8 -*-
from datetime import timedelta
from urllib.parse import unquote

from lxml import etree

from odoo import fields
from odoo.tests import Form, TransactionCase, tagged

from ..models.racil_wa_template import render_body


@tagged('post_install', '-at_install', 'racil_wa')
class TestComposer(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.sa = cls.env.ref('base.sa')
        cls.partner = cls.env['res.partner'].create({
            'name': 'مؤسسة الاختبار', 'phone': '٠٥٠١٢٣٤٥٦٧', 'country_id': cls.sa.id, 'lang': 'en_US',
        })

    def _composer(self, record):
        action = record.action_racil_wa_open()
        ctx = dict(action['context'])
        return Form(self.env['racil.wa.composer'].with_context(**ctx))

    def test_render_placeholders(self):
        body = render_body('هلا {العميل} - {partner} {unknown} {doc}', {'partner': 'Ali', 'doc': 'INV/1'})
        self.assertEqual(body, 'هلا Ali - Ali {unknown} INV/1')

    def test_button_injected_in_contact_form(self):
        arch = self.env['res.partner'].get_view(view_type='form')['arch']
        self.assertIn('action_racil_wa_open', arch)
        # disabled documents do not get the button
        self.env.ref('racil_whatsapp.doc_res_partner').active = False
        arch = self.env['res.partner'].get_view(view_type='form')['arch']
        self.assertNotIn('action_racil_wa_open', arch)

    def test_contact_message(self):
        form = self._composer(self.partner)
        self.assertEqual(form.phone, '٠٥٠١٢٣٤٥٦٧')
        self.assertEqual(form.country_code, 'SA')
        self.assertEqual(form.style, 'en')   # partner speaks English
        form.style = 'gulf'
        self.assertIn('هلا والله', form.body)
        self.assertIn('مؤسسة الاختبار', form.body)
        wiz = form.save()
        self.assertEqual(wiz.wa_number, '966501234567')
        self.assertTrue(wiz.phone_valid)
        self.assertIn('o_racil_wa_bubble', str(wiz.preview))
        action = wiz.action_send()
        self.assertEqual(action['type'], 'ir.actions.act_url')
        self.assertTrue(action['url'].startswith('https://wa.me/966501234567?text='))
        self.assertIn('هلا والله', unquote(action['url']))
        self.assertIn('966', self.partner.message_ids[:1].body)

    def test_invoice_flow(self):
        if 'account.move' not in self.env:
            self.skipTest('Invoicing not installed')
        product = self.env['product.product'].create({'name': 'Service', 'list_price': 100})
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice', 'partner_id': self.partner.id,
            'invoice_date': fields.Date.today() - timedelta(days=40),
            'invoice_date_due': fields.Date.today() - timedelta(days=10),
            'invoice_line_ids': [(0, 0, {'product_id': product.id, 'quantity': 1, 'price_unit': 100,
                                         'tax_ids': [(6, 0, [])]})],
        })
        arch = etree.fromstring(self.env['account.move'].get_view(view_type='form')['arch'])
        self.assertTrue(arch.xpath("//header/button[@name='action_racil_wa_open']"))
        self.assertEqual(invoice._racil_wa_message_key(), 'invoice_open')   # draft
        invoice.action_post()
        self.assertEqual(invoice._racil_wa_message_key(), 'invoice_overdue')
        form = self._composer(invoice)
        form.style = 'msa'
        self.assertEqual(form.template_id, self.env.ref('racil_whatsapp.tpl_invoice_overdue_msa'))
        self.assertIn(invoice.name, form.body)
        self.assertIn('/my/invoices/', form.body)
        self.assertIn('access_token=', form.body)
        form.link_type = 'pdf'
        self.assertIn('report_type=pdf', form.body)
        wiz = form.save()
        wiz.action_send()
        self.assertIn(invoice.name, invoice.message_ids[:1].body)

    def test_sale_flow(self):
        if 'sale.order' not in self.env:
            self.skipTest('Sales not installed')
        product = self.env['product.product'].create({'name': 'Item', 'list_price': 50})
        order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'order_line': [(0, 0, {'product_id': product.id, 'product_uom_qty': 2})],
        })
        form = self._composer(order)
        form.style = 'gulf'
        self.assertEqual(form.template_id, self.env.ref('racil_whatsapp.tpl_quotation_gulf'))
        self.assertIn(order.name, form.body)
        order.action_confirm()
        self.assertEqual(order._racil_wa_message_key(), 'sale_confirmed')

    def test_missing_phone_and_open_modes(self):
        partner = self.env['res.partner'].create({'name': 'No Phone'})
        form = self._composer(partner)
        self.assertFalse(form.phone)
        form.phone = '+971 50 123 4567'
        wiz = form.save()
        self.env['ir.config_parameter'].sudo().set_param('racil_whatsapp.open_mode', 'web')
        self.assertTrue(wiz._wa_url().startswith('https://web.whatsapp.com/send?phone=971501234567&text='))
