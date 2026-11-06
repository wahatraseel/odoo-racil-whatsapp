# -*- coding: utf-8 -*-
from odoo import api, fields, models, tools


class RacilWaDocument(models.Model):
    """Which models get the WhatsApp button, and where to find the phone."""
    _name = 'racil.wa.document'
    _description = 'WhatsApp Button - Enabled Document'
    _order = 'sequence, id'

    name = fields.Char('Document', required=True, translate=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    model_name = fields.Char(
        'Technical Model', required=True,
        help="Technical name of the model, e.g. account.move, sale.order, crm.lead or any custom model.")
    partner_field = fields.Char(
        'Customer Field', default='partner_id',
        help="Many2one field pointing to the contact (res.partner). Leave empty for the Contacts model itself.")
    phone_field = fields.Char(
        'Phone Field on Document',
        help="Optional: a phone field stored on the document itself (e.g. 'phone' on CRM leads). "
             "It is tried before the contact's numbers.")
    is_installed = fields.Boolean('Available', compute='_compute_is_installed',
                                  help="The application providing this document is installed.")

    @api.depends('model_name')
    def _compute_is_installed(self):
        for rec in self:
            rec.is_installed = bool(rec.model_name) and rec.model_name in self.env

    @api.model
    @tools.ormcache()
    def _racil_wa_enabled_models(self):
        self.flush_model(['model_name', 'active'])
        self.env.cr.execute("SELECT model_name FROM racil_wa_document WHERE active IS TRUE")
        return frozenset(row[0] for row in self.env.cr.fetchall())

    def _racil_wa_clear_caches(self):
        registry = self.env.registry
        registry.clear_cache()
        registry.clear_cache('templates')

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        self._racil_wa_clear_caches()
        return records

    def write(self, vals):
        res = super().write(vals)
        self._racil_wa_clear_caches()
        return res

    def unlink(self):
        res = super().unlink()
        self._racil_wa_clear_caches()
        return res

    @api.model
    def _racil_wa_config_for(self, model_name):
        return self.sudo().search([('model_name', '=', model_name)], limit=1)
