# -*- coding: utf-8 -*-
from odoo import fields, models

from . import phone_intl
from .racil_wa_template import STYLES


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    racil_wa_default_country = fields.Selection(
        phone_intl.COUNTRY_SELECTION, string='Default Country (WhatsApp)',
        config_parameter='racil_whatsapp.default_country', default='SA',
        help="Country assumed for numbers typed without a country code when the contact has no country.")
    racil_wa_open_mode = fields.Selection(
        [('wa_me', 'Automatic (wa.me) - app on phones, choice on computers'),
         ('web', 'Always WhatsApp Web'),
         ('api', 'api.whatsapp.com (compatibility)')],
        string='Open WhatsApp With', config_parameter='racil_whatsapp.open_mode', default='wa_me')
    racil_wa_default_style = fields.Selection(
        STYLES, string='Default Message Language', config_parameter='racil_whatsapp.default_style',
        default='msa')
    racil_wa_link_type = fields.Selection(
        [('portal', 'Customer portal page'), ('pdf', 'Direct PDF download')],
        string='Document Link', config_parameter='racil_whatsapp.link_type', default='portal')
    racil_wa_log_chatter = fields.Boolean('Log Sent Messages in Chatter')

    def get_values(self):
        res = super().get_values()
        param = self.env['ir.config_parameter'].sudo().get_param('racil_whatsapp.log_chatter', 'True')
        res['racil_wa_log_chatter'] = param == 'True'
        return res

    def set_values(self):
        super().set_values()
        self.env['ir.config_parameter'].sudo().set_param(
            'racil_whatsapp.log_chatter', 'True' if self.racil_wa_log_chatter else 'False')
