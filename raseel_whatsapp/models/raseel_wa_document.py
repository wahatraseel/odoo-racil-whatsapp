# -*- coding: utf-8 -*-
from odoo import _, api, fields, models, tools


class RaseelWaDocument(models.Model):
    """Which models get the WhatsApp button, and where to find the phone."""
    _name = 'raseel.wa.document'
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
    bulk_action_id = fields.Many2one(
        'ir.actions.server', 'Bulk Sending Action', readonly=True, ondelete='set null', copy=False,
        help="\"Send by WhatsApp\" entry of the Actions menu in the list view of this document.")

    @api.depends('model_name')
    def _compute_is_installed(self):
        for rec in self:
            rec.is_installed = bool(rec.model_name) and rec.model_name in self.env

    @api.model
    @tools.ormcache()
    def _raseel_wa_enabled_models(self):
        self.flush_model(['model_name', 'active'])
        self.env.cr.execute("SELECT model_name FROM raseel_wa_document WHERE active IS TRUE")
        return frozenset(row[0] for row in self.env.cr.fetchall())

    def _raseel_wa_clear_caches(self):
        registry = self.env.registry
        registry.clear_cache()
        registry.clear_cache('templates')

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        self._raseel_wa_clear_caches()
        records._raseel_wa_sync_bulk_actions()
        return records

    def write(self, vals):
        res = super().write(vals)
        self._raseel_wa_clear_caches()
        if {'active', 'model_name', 'name'} & set(vals):
            self._raseel_wa_sync_bulk_actions()
        return res

    def unlink(self):
        actions = self.sudo().bulk_action_id
        res = super().unlink()
        actions.unlink()
        self._raseel_wa_clear_caches()
        return res

    # ------------------------------------------------------------------
    # "Send by WhatsApp" in the Actions menu of list views (bulk sending)
    # ------------------------------------------------------------------
    @api.model
    def _raseel_wa_sync_all_bulk_actions(self):
        """Called on install, every day and when apps are installed later."""
        self.with_context(active_test=False).search([])._raseel_wa_sync_bulk_actions()
        return True

    def _raseel_wa_sync_bulk_actions(self):
        IrModel = self.env['ir.model'].sudo()
        for doc in self.sudo():
            model = IrModel._get(doc.model_name) if doc.model_name else False
            wanted = bool(doc.active and model and doc.model_name in self.env)
            action = doc.bulk_action_id
            if not wanted:
                if action:
                    doc.bulk_action_id = False
                    action.unlink()
                continue
            vals = {
                'name': _("Send by WhatsApp"),
                'model_id': model.id,
                'binding_model_id': model.id,
                'binding_type': 'action',
                'binding_view_types': 'list',
                'state': 'code',
                'code': "action = env['raseel.wa.bulk'].action_open_for(records)",
            }
            if action:
                if action.model_id != model:
                    action.write(vals)
            else:
                doc.bulk_action_id = self.env['ir.actions.server'].sudo().create(vals)

    @api.model
    def _raseel_wa_config_for(self, model_name):
        return self.sudo().search([('model_name', '=', model_name)], limit=1)

    def _register_hook(self):
        """Apps installed after this module (Sales, Purchase...) get their bulk action right away."""
        res = super()._register_hook()
        try:
            with self.env.cr.savepoint():
                missing = self.sudo().search([('active', '=', True), ('bulk_action_id', '=', False)])
                missing = missing.filtered(lambda d: d.model_name in self.env)
                if missing:
                    missing._raseel_wa_sync_bulk_actions()
        except Exception:  # never block the server start-up for a convenience
            pass
        return res
