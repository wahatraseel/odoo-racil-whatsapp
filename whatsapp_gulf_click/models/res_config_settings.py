# -*- coding: utf-8 -*-
from odoo import fields, models

from . import phone_gulf
from .wa_gulf_template import STYLES


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    wa_gulf_default_country = fields.Selection(
        phone_gulf.COUNTRY_SELECTION, string='Default Country (WhatsApp)',
        config_parameter='whatsapp_gulf_click.default_country', default='SA',
        help="Country assumed for numbers typed without a country code when the contact has no country.")
    wa_gulf_open_mode = fields.Selection(
        [('wa_me', 'Automatic (wa.me) - app on phones, choice on computers'),
         ('web', 'Always WhatsApp Web'),
         ('api', 'api.whatsapp.com (compatibility)')],
        string='Open WhatsApp With', config_parameter='whatsapp_gulf_click.open_mode', default='wa_me')
    wa_gulf_default_style = fields.Selection(
        STYLES, string='Default Message Language', config_parameter='whatsapp_gulf_click.default_style',
        default='msa')
    wa_gulf_link_type = fields.Selection(
        [('portal', 'Customer portal page'), ('pdf', 'Direct PDF download')],
        string='Document Link', config_parameter='whatsapp_gulf_click.link_type', default='portal')
    wa_gulf_log_chatter = fields.Boolean('Log Sent Messages in Chatter')

    def get_values(self):
        res = super().get_values()
        param = self.env['ir.config_parameter'].sudo().get_param('whatsapp_gulf_click.log_chatter', 'True')
        res['wa_gulf_log_chatter'] = param == 'True'
        return res

    def set_values(self):
        super().set_values()
        self.env['ir.config_parameter'].sudo().set_param(
            'whatsapp_gulf_click.log_chatter', 'True' if self.wa_gulf_log_chatter else 'False')
