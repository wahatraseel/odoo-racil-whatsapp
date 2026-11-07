# -*- coding: utf-8 -*-
from odoo import fields, models

from . import phone_intl
from .raseel_wa_template import STYLES


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    raseel_wa_default_country = fields.Selection(
        phone_intl.COUNTRY_SELECTION, string='Default Country (WhatsApp)',
        config_parameter='raseel_whatsapp.default_country', default='SA',
        help="Country assumed for numbers typed without a country code when the contact has no country.")
    raseel_wa_open_mode = fields.Selection(
        [('wa_me', 'Automatic (wa.me) - app on phones, choice on computers'),
         ('web', 'Always WhatsApp Web'),
         ('api', 'api.whatsapp.com (compatibility)')],
        string='Open WhatsApp With', config_parameter='raseel_whatsapp.open_mode', default='wa_me')
    raseel_wa_default_style = fields.Selection(
        STYLES, string='Default Message Language', config_parameter='raseel_whatsapp.default_style',
        default='msa')
    raseel_wa_link_type = fields.Selection(
        [('portal', 'Customer portal page'), ('pdf', 'Direct PDF download')],
        string='Document Link', config_parameter='raseel_whatsapp.link_type', default='portal')
    raseel_wa_log_chatter = fields.Boolean('Log Sent Messages in Chatter')
    raseel_wa_overdue_days = fields.Integer(
        'Overdue After (days)', config_parameter='raseel_whatsapp.overdue_days', default=1,
        help="An invoice appears in Payment Reminders this many days after its due date.")
    raseel_wa_remind_interval = fields.Integer(
        'Remind Again After (days)', config_parameter='raseel_whatsapp.remind_interval', default=7,
        help="An invoice already reminded on WhatsApp is hidden from Payment Reminders for this many days. "
             "0 = always show it.")
    raseel_wa_reminder_activity = fields.Boolean(
        'Daily To-Do for Overdue Invoices', config_parameter='raseel_whatsapp.reminder_activity',
        help="Every morning, schedule a To-Do on each overdue invoice for its salesperson "
             "to send the WhatsApp payment reminder.")

    def get_values(self):
        res = super().get_values()
        param = self.env['ir.config_parameter'].sudo().get_param('raseel_whatsapp.log_chatter', 'True')
        res['raseel_wa_log_chatter'] = param == 'True'
        return res

    def set_values(self):
        super().set_values()
        self.env['ir.config_parameter'].sudo().set_param(
            'raseel_whatsapp.log_chatter', 'True' if self.raseel_wa_log_chatter else 'False')
