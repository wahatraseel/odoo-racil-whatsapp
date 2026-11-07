# -*- coding: utf-8 -*-
from datetime import timedelta
from urllib.parse import unquote

from odoo import fields
from odoo.exceptions import AccessError
from odoo.tests import Form, TransactionCase, new_test_user, tagged


@tagged('post_install', '-at_install', 'raseel_wa')
class TestRaseelFeatures(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.sa = cls.env.ref('base.sa')
        cls.user_a = new_test_user(cls.env, login='wa_user_a', groups='base.group_user', name='Agent A')
        cls.user_b = new_test_user(cls.env, login='wa_user_b', groups='base.group_user', name='Agent B')
        Partner = cls.env['res.partner']
        cls.p1 = Partner.create({'name': 'عميل واحد', 'phone': '0501234567', 'country_id': cls.sa.id})
        cls.p2 = Partner.create({'name': 'Client Two', 'phone': '+971 50 123 4567', 'lang': 'en_US'})
        cls.p3 = Partner.create({'name': 'No Phone', 'country_id': cls.sa.id})

    # ------------------------------------------------------------------
    # Personal templates
    # ------------------------------------------------------------------
    def test_personal_templates(self):
        Template = self.env['raseel.wa.template']
        tpl = Template.with_user(self.user_a).create({
            'name': 'My hello', 'key': 'contact', 'style': 'gulf', 'body': 'يا هلا {العميل} - رسالتي الخاصة',
            'user_id': False,   # forced to the creator for non-administrators
        })
        self.assertEqual(tpl.user_id, self.user_a)
        self.assertTrue(tpl.is_personal)
        # invisible and untouchable for the other users
        self.assertNotIn(tpl, Template.with_user(self.user_b).search([]))
        with self.assertRaises(AccessError):
            Template.with_user(self.user_b).browse(tpl.id).write({'name': 'hack'})
        # users cannot edit shared templates
        shared = self.env.ref('raseel_whatsapp.tpl_contact_gulf')
        with self.assertRaises(AccessError):
            shared.with_user(self.user_a).write({'body': 'changed'})
        # the personal wording is picked first, for its owner only
        self.assertEqual(Template.with_user(self.user_a)._raseel_wa_pick('res.partner', 'contact', 'gulf'), tpl)
        self.assertEqual(Template.with_user(self.user_b)._raseel_wa_pick('res.partner', 'contact', 'gulf'), shared)

    def test_save_as_template_and_log(self):
        action = self.p1.with_user(self.user_a).action_raseel_wa_open()
        form = Form(self.env['raseel.wa.composer'].with_user(self.user_a).with_context(**action['context']))
        form.style = 'msa'
        form.body = 'السلام عليكم {العميل} *نص مخصص*'
        form.save_template = True
        form.new_template_name = 'تحية مختصرة'
        wiz = form.save()
        wiz.action_send()
        tpl = self.env['raseel.wa.template'].search([('name', '=', 'تحية مختصرة')])
        self.assertEqual(tpl.user_id, self.user_a)
        self.assertEqual(tpl.model_name, 'res.partner')
        log = self.env['raseel.wa.message'].search([('res_model', '=', 'res.partner'), ('res_id', '=', self.p1.id)])
        self.assertEqual(len(log), 1)
        self.assertEqual(log.user_id, self.user_a)
        self.assertEqual(log.source, 'single')
        self.assertEqual(log.partner_id, self.p1)
        self.assertEqual(log.document_id, self.env.ref('raseel_whatsapp.doc_res_partner'))
        self.assertIn('966501234567', log.phone.replace(' ', ''))

    # ------------------------------------------------------------------
    # Bulk sending
    # ------------------------------------------------------------------
    def test_bulk_actions_in_list_views(self):
        doc = self.env.ref('raseel_whatsapp.doc_res_partner')
        self.assertTrue(doc.bulk_action_id)
        self.assertEqual(doc.bulk_action_id.binding_model_id.model, 'res.partner')
        action = doc.bulk_action_id
        doc.active = False
        self.assertFalse(action.exists())
        doc.active = True
        self.assertTrue(doc.bulk_action_id.binding_model_id)

    def test_bulk_sending(self):
        partners = self.p1 | self.p2 | self.p3
        action = self.env['raseel.wa.bulk'].with_user(self.user_a).action_open_for(partners)
        wiz = self.env['raseel.wa.bulk'].with_user(self.user_a).browse(action['res_id'])
        self.assertEqual(wiz.state, 'setup')
        wiz.style = 'gulf'
        wiz.action_prepare()
        self.assertEqual(wiz.state, 'send')
        self.assertEqual(wiz.line_count, 3)
        self.assertEqual(wiz.invalid_count, 1)
        self.assertEqual(wiz.current_line_id.partner_id, self.p1)
        self.assertIn('هلا والله', wiz.current_body)
        # edit the current message before sending it
        wiz.current_body = wiz.current_body + '\nتعديل يدوي'
        res = wiz.action_send_current()
        self.assertEqual(res['type'], 'ir.actions.act_url')
        self.assertTrue(res['url'].startswith('https://wa.me/966501234567?text='))
        self.assertIn('تعديل يدوي', unquote(res['url']))
        self.assertEqual(wiz.sent_count, 1)
        self.assertEqual(wiz.current_line_id.partner_id, self.p2)
        res = wiz.action_send_current()
        self.assertIn('wa.me/971501234567', res['url'])
        # the contact without a number is skipped, then fixed and sent
        wiz.action_skip_current()
        self.assertEqual(wiz.state, 'done')
        wiz.action_restart_skipped()
        self.assertEqual(wiz.current_line_id.partner_id, self.p3)
        wiz.current_phone = '0559876543'
        res = wiz.action_send_current()
        self.assertIn('wa.me/966559876543', res['url'])
        self.assertEqual(wiz.state, 'done')
        logs = self.env['raseel.wa.message'].search([('source', '=', 'bulk')])
        self.assertEqual(len(logs), 3)
        self.assertEqual(set(logs.mapped('style')), {'gulf'})
        self.assertEqual(logs.user_id, self.user_a)

    def test_bulk_fixed_template(self):
        tpl = self.env.ref('raseel_whatsapp.tpl_any_en')
        action = self.env['raseel.wa.bulk'].action_open_for(self.p1 | self.p2)
        wiz = self.env['raseel.wa.bulk'].browse(action['res_id'])
        wiz.template_id = tpl
        wiz.action_prepare()
        self.assertEqual(wiz.line_ids.mapped('template_id'), tpl)
        self.assertTrue(all(line.body.startswith('Hello') for line in wiz.line_ids))

    # ------------------------------------------------------------------
    # Payment reminders
    # ------------------------------------------------------------------
    def _overdue_invoice(self, partner, days=10):
        product = self.env['product.product'].create({'name': 'Service', 'list_price': 100})
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice', 'partner_id': partner.id,
            'invoice_date': fields.Date.today() - timedelta(days=days + 30),
            'invoice_date_due': fields.Date.today() - timedelta(days=days),
            'invoice_user_id': self.user_a.id,
            'invoice_line_ids': [(0, 0, {'product_id': product.id, 'quantity': 1, 'price_unit': 100,
                                         'tax_ids': [(6, 0, [])]})],
        })
        invoice.action_post()
        return invoice

    def test_payment_reminders(self):
        if 'account.move' not in self.env:
            self.skipTest('Invoicing not installed')
        Bulk = self.env['raseel.wa.bulk']
        inv1 = self._overdue_invoice(self.p1)
        inv2 = self._overdue_invoice(self.p2, days=1)
        params = self.env['ir.config_parameter'].sudo()
        params.set_param('raseel_whatsapp.overdue_days', '5')
        self.assertIn(inv1, Bulk._raseel_wa_overdue_invoices())
        self.assertNotIn(inv2, Bulk._raseel_wa_overdue_invoices())
        params.set_param('raseel_whatsapp.overdue_days', '1')
        action = Bulk.action_open_overdue()
        wiz = Bulk.browse(action['res_id'])
        self.assertEqual(wiz.source, 'reminder')
        wiz.action_prepare()
        line = wiz.line_ids.filtered(lambda l: l.composer_id.res_id == inv1.id)
        self.assertEqual(line.template_id.key, 'invoice_overdue')
        res = line.action_send_line()
        self.assertTrue(res['url'].startswith('https://wa.me/966501234567?text='))
        log = self.env['raseel.wa.message'].search([('res_model', '=', 'account.move'), ('res_id', '=', inv1.id)])
        self.assertEqual(log.source, 'reminder')
        self.assertEqual(log.message_key, 'invoice_overdue')
        # reminded today: hidden until the interval is over
        self.assertNotIn(inv1, Bulk._raseel_wa_overdue_invoices())
        params.set_param('raseel_whatsapp.remind_interval', '0')
        self.assertIn(inv1, Bulk._raseel_wa_overdue_invoices())

    def test_reminder_activities(self):
        if 'account.move' not in self.env:
            self.skipTest('Invoicing not installed')
        invoice = self._overdue_invoice(self.p1)
        Bulk = self.env['raseel.wa.bulk']
        Bulk._cron_overdue_activities()
        self.assertFalse(invoice.activity_ids)   # disabled by default
        self.env['ir.config_parameter'].sudo().set_param('raseel_whatsapp.reminder_activity', 'True')
        Bulk._cron_overdue_activities()
        Bulk._cron_overdue_activities()          # no duplicate
        self.assertEqual(len(invoice.activity_ids), 1)
        self.assertEqual(invoice.activity_ids.user_id, self.user_a)

    def test_no_overdue_notification(self):
        if 'account.move' not in self.env:
            self.skipTest('Invoicing not installed')
        self.env['account.move'].search([('move_type', '=', 'out_invoice'), ('state', '=', 'posted')]).write(
            {'payment_state': 'paid'})
        res = self.env['raseel.wa.bulk'].action_open_overdue()
        self.assertEqual(res['tag'], 'display_notification')

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------
    def test_statistics(self):
        for partner in (self.p1, self.p2):
            action = partner.action_raseel_wa_open()
            wiz = Form(self.env['raseel.wa.composer'].with_user(self.user_b).with_context(**action['context'])).save()
            wiz.action_send()
        Message = self.env['raseel.wa.message'].with_user(self.user_b)
        self.assertEqual(Message.search_count([('user_id', '=', self.user_b.id)]), 2)
        with self.assertRaises(AccessError):
            Message.search([], limit=1).unlink()
        views = self.env['raseel.wa.message'].get_views([(False, 'pivot'), (False, 'graph'), (False, 'list')])
        self.assertIn('pivot', views['views'])
