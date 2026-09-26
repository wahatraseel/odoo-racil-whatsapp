# -*- coding: utf-8 -*-
from lxml import etree

from odoo import _, api, fields, models


class Base(models.AbstractModel):
    """Adds the WhatsApp button to the form view of every enabled document.

    The button is injected when the view is served (not stored in ir.ui.view), so:
    * any model can be enabled from the settings, including custom ones,
    * installing Sales / Invoicing / Purchase after this module just works,
    * uninstalling leaves nothing behind.
    """
    _inherit = 'base'

    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id, view_type, **options)
        if (view_type == 'form' and self.env.registry.ready
                and 'wa.gulf.document' in self.env
                and self._name in self.env['wa.gulf.document']._wa_gulf_enabled_models()):
            self._wa_gulf_inject_button(arch)
        return arch, view

    @api.model
    def _wa_gulf_inject_button(self, arch):
        if arch is None or arch.tag != 'form':
            return
        header = arch.find('header')
        sheet = arch.find('sheet')
        if header is None and sheet is None:
            return  # sub-forms (address blocks, dialogs...) are left alone
        if arch.xpath(".//button[@name='action_wa_gulf_open']"):
            return
        label = _("WhatsApp")
        if header is None:
            button_box = arch.xpath(".//div[@name='button_box']")
            if button_box:
                # first position so it is never hidden in the "More" dropdown
                button_box[0].insert(0, etree.Element('button', {
                    'name': 'action_wa_gulf_open', 'type': 'object', 'string': label,
                    'class': 'oe_stat_button o_wa_gulf_stat', 'icon': 'fa-whatsapp',
                    'invisible': 'not id',
                }))
                return
            header = etree.Element('header')
            arch.insert(0, header)
        button = etree.Element('button', {
            'name': 'action_wa_gulf_open', 'type': 'object', 'string': label,
            'class': 'btn-secondary o_wa_gulf_btn', 'icon': 'fa-whatsapp',
            'invisible': 'not id', 'data-hotkey': 'shift+w',
        })
        statusbar = header.xpath("./field[@widget='statusbar']")
        if statusbar:
            statusbar[0].addprevious(button)
        else:
            header.append(button)

    def action_wa_gulf_open(self):
        """Open the WhatsApp composer for the current document."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _("Send by WhatsApp"),
            'res_model': 'wa.gulf.composer',
            'view_mode': 'form',
            'views': [(False, 'form')],
            'target': 'new',
            'context': {
                'default_res_model': self._name,
                'default_res_id': self.id,
            },
        }

    # ------------------------------------------------------------------
    # Helpers used by the composer (overridable per model)
    # ------------------------------------------------------------------
    def _wa_gulf_partner(self, config=None):
        self.ensure_one()
        if self._name == 'res.partner':
            return self
        field_name = (config and config.partner_field) or 'partner_id'
        field = self._fields.get(field_name)
        if field and field.type == 'many2one' and field.comodel_name == 'res.partner':
            return self[field_name]
        return self.env['res.partner']

    def _wa_gulf_phone_candidates(self, config=None):
        """Numbers to try, best first."""
        self.ensure_one()
        numbers = []
        doc_fields = [config.phone_field] if config and config.phone_field else []
        doc_fields += ['mobile', 'phone'] if self._name != 'res.partner' else []
        for fname in doc_fields:
            if fname in self._fields and self._fields[fname].type == 'char' and self[fname]:
                numbers.append(self[fname])
        partner = self._wa_gulf_partner(config)
        for contact in (partner, partner.commercial_partner_id) if partner else ():
            for fname in ('mobile', 'phone'):
                if fname in contact._fields and contact[fname]:
                    numbers.append(contact[fname])
        seen, result = set(), []
        for num in numbers:
            if num not in seen:
                seen.add(num)
                result.append(num)
        return result

    def _wa_gulf_message_key(self):
        """Situation of the document, used to pick the template automatically."""
        self.ensure_one()
        name = self._name
        state = self['state'] if 'state' in self._fields else False
        if name == 'account.move':
            if self.move_type in ('out_refund', 'in_refund'):
                return 'refund'
            if self.move_type in ('in_invoice', 'in_receipt'):
                return 'any'
            if self.payment_state in ('paid', 'in_payment'):
                return 'invoice_paid'
            due = self.invoice_date_due
            if state == 'posted' and due and due < fields.Date.context_today(self) and self.amount_residual > 0:
                return 'invoice_overdue'
            return 'invoice_open'
        if name == 'sale.order':
            return 'sale_confirmed' if state in ('sale', 'done') else 'quotation'
        if name == 'purchase.order':
            return 'purchase'
        if name == 'stock.picking':
            code = self.picking_type_code if 'picking_type_code' in self._fields else False
            return 'received' if code == 'incoming' else 'delivery'
        if name == 'pos.order':
            return 'invoice_paid'
        if name in ('res.partner', 'crm.lead'):
            return 'contact'
        return 'any'

    def _wa_gulf_link(self, link_type='portal'):
        """Public link to the document (customer portal page or direct PDF), if the model supports it."""
        self.ensure_one()
        if not hasattr(self, 'get_portal_url') or 'access_url' not in self._fields:
            return ''
        if not self.access_url or self.access_url == '#':
            return ''
        if link_type == 'pdf':
            path = self.get_portal_url(report_type='pdf', download=True)
        else:
            path = self.get_portal_url()
        return self.get_base_url() + path
