# -*- coding: utf-8 -*-
from odoo import _, api, fields, models

from .raseel_wa_template import MESSAGE_KEYS, STYLES

SOURCES = [
    ('single', 'Single message'),
    ('bulk', 'Bulk sending'),
    ('reminder', 'Payment reminder'),
]


class RaseelWaMessage(models.Model):
    """One line per WhatsApp message opened from Odoo - feeds the statistics report."""
    _name = 'raseel.wa.message'
    _description = 'WhatsApp Sent Message'
    _order = 'date desc, id desc'
    _rec_name = 'record_name'

    date = fields.Datetime('Sent On', default=fields.Datetime.now, required=True, readonly=True, index=True)
    user_id = fields.Many2one('res.users', 'Sent By', default=lambda self: self.env.user, readonly=True, index=True)
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company,
                                 readonly=True, index=True)
    partner_id = fields.Many2one('res.partner', 'Recipient', readonly=True, index=True)
    res_model = fields.Char('Document Model', readonly=True, index=True)
    res_id = fields.Integer('Document ID', readonly=True)
    record_name = fields.Char('Document', readonly=True)
    document_id = fields.Many2one('raseel.wa.document', 'Document Type', readonly=True, index=True,
                                  ondelete='set null')
    message_key = fields.Selection(MESSAGE_KEYS, 'Situation', readonly=True)
    style = fields.Selection(STYLES, 'Language', readonly=True)
    template_id = fields.Many2one('raseel.wa.template', 'Template', readonly=True, ondelete='set null')
    source = fields.Selection(SOURCES, 'Sent From', default='single', required=True, readonly=True)
    phone = fields.Char('Number', readonly=True)
    body = fields.Text('Message', readonly=True)
    # integers are summed in pivot/graph views (default aggregation on every version)
    message_count = fields.Integer('Messages', default=1, readonly=True)

    @api.model
    def _raseel_wa_document_type(self, model_name):
        """Readable name of a document model (configured name, else the model description)."""
        config = self.env['raseel.wa.document']._raseel_wa_config_for(model_name)
        if config:
            return config.name
        model = self.env['ir.model']._get(model_name) if model_name else False
        return model.name if model else (model_name or '')

    def action_open_document(self):
        self.ensure_one()
        if not self.res_model or self.res_model not in self.env:
            return False
        record = self.env[self.res_model].browse(self.res_id).exists()
        if not record:
            return False
        return {
            'type': 'ir.actions.act_window',
            'name': _("Document"),
            'res_model': self.res_model,
            'res_id': self.res_id,
            'view_mode': 'form',
            'views': [(False, 'form')],
            'target': 'current',
        }
