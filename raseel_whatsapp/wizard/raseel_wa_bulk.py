# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from ..models.raseel_wa_template import STYLES
from .raseel_wa_composer import render_preview

PARAM = 'raseel_whatsapp.%s'
MAX_RECORDS = 500


class RaseelWaBulk(models.TransientModel):
    """Send WhatsApp messages to many documents, one chat after the other.

    WhatsApp click-to-chat (wa.me) opens exactly one conversation per click, so bulk sending is a
    guided queue: every message is prepared in advance and the user opens them in turn with a single
    button - no API, no Meta account, no risk of the number being banned for automated spam.
    """
    _name = 'raseel.wa.bulk'
    _description = 'WhatsApp Bulk Sending'

    res_model = fields.Char('Document Model', required=True, readonly=True)
    model_label = fields.Char('Documents', compute='_compute_model_label')
    source = fields.Selection([('bulk', 'Bulk sending'), ('reminder', 'Payment reminder')],
                              default='bulk', required=True, readonly=True)
    state = fields.Selection([('setup', 'Setup'), ('send', 'Sending'), ('done', 'Done')],
                             default='setup', required=True)
    res_ids = fields.Char('Records', readonly=True, help="Technical: comma separated ids to prepare.")

    style = fields.Selection([('auto', "Automatic (contact's language)")] + STYLES, 'Language',
                             default='auto', required=True)
    template_id = fields.Many2one(
        'raseel.wa.template', 'Template',
        domain="['|', ('model_name', '=', False), ('model_name', '=', res_model), "
               "'|', ('user_id', '=', False), ('user_id', '=', uid)]",
        help="Leave empty to pick the best template for every document automatically "
             "(e.g. overdue invoices get the payment reminder).")
    link_type = fields.Selection([('portal', 'Customer portal page'), ('pdf', 'Direct PDF download')],
                                 'Link', default=lambda self: self._param('link_type', 'portal'))
    log_note = fields.Boolean('Log in chatter', default=lambda self: self._param('log_chatter', 'True') == 'True')

    line_ids = fields.One2many('raseel.wa.bulk.line', 'bulk_id', 'Messages')
    line_count = fields.Integer(compute='_compute_counts')
    sent_count = fields.Integer('Sent', compute='_compute_counts')
    skipped_count = fields.Integer('Skipped', compute='_compute_counts')
    pending_count = fields.Integer('Remaining', compute='_compute_counts')
    invalid_count = fields.Integer('Without a valid number', compute='_compute_counts')
    progress = fields.Float('Progress', compute='_compute_counts')

    current_line_id = fields.Many2one('raseel.wa.bulk.line', 'Current', compute='_compute_current_line_id',
                                      store=True)
    current_record = fields.Char('Document', related='current_line_id.record_name')
    current_partner_id = fields.Many2one('res.partner', 'Recipient', related='current_line_id.partner_id')
    current_phone = fields.Char('Mobile', related='current_line_id.phone', readonly=False)
    current_phone_display = fields.Char('Will be sent to', related='current_line_id.phone_display')
    current_phone_valid = fields.Boolean(related='current_line_id.phone_valid')
    current_body = fields.Text('Message', related='current_line_id.body', readonly=False)
    current_preview = fields.Html('Preview', related='current_line_id.preview')

    # ------------------------------------------------------------------
    def _param(self, key, default=False):
        return self.env['ir.config_parameter'].sudo().get_param(PARAM % key, default)

    @api.depends('res_model')
    def _compute_model_label(self):
        for wiz in self:
            wiz.model_label = self.env['raseel.wa.message']._raseel_wa_document_type(wiz.res_model)

    @api.depends('line_ids.state', 'line_ids.phone_valid', 'line_ids.sequence')
    def _compute_counts(self):
        for wiz in self:
            lines = wiz.line_ids.sorted(lambda l: (l.sequence, l.id))
            pending = lines.filtered(lambda l: l.state == 'pending')
            wiz.line_count = len(lines)
            wiz.sent_count = len(lines.filtered(lambda l: l.state == 'sent'))
            wiz.skipped_count = len(lines.filtered(lambda l: l.state == 'skipped'))
            wiz.pending_count = len(pending)
            wiz.invalid_count = len(lines.filtered(lambda l: not l.phone_valid))
            wiz.progress = 100.0 * (len(lines) - len(pending)) / len(lines) if lines else 0.0

    @api.depends('line_ids.state', 'line_ids.sequence')
    def _compute_current_line_id(self):
        for wiz in self:
            pending = wiz.line_ids.filtered(lambda l: l.state == 'pending')
            wiz.current_line_id = pending.sorted(lambda l: (l.sequence, l.id))[:1]

    # ------------------------------------------------------------------
    # Entry points
    # ------------------------------------------------------------------
    @api.model
    def action_open_for(self, records, source='bulk'):
        """Called from the "Send by WhatsApp" action of list views."""
        if not records:
            raise UserError(_("Select at least one document."))
        if len(records) > MAX_RECORDS:
            raise UserError(_("Please select at most %s documents at a time.", MAX_RECORDS))
        wiz = self.create({
            'res_model': records._name,
            'res_ids': ','.join(str(i) for i in records.ids),
            'source': source,
        })
        return wiz._action_reopen(_("Send by WhatsApp"))

    @api.model
    def action_open_overdue(self):
        """Menu "Payment Reminders": overdue customer invoices not reminded recently."""
        if 'account.move' not in self.env:
            raise UserError(_("Payment reminders need the Invoicing application."))
        invoices = self._raseel_wa_overdue_invoices()
        if not invoices:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _("Payment Reminders"),
                    'message': _("No overdue invoice needs a reminder today."),
                    'type': 'success',
                    'sticky': False,
                },
            }
        return self.action_open_for(invoices[:MAX_RECORDS], source='reminder')

    @api.model
    def _raseel_wa_overdue_invoices(self):
        overdue_days = int(self._param('overdue_days', '1') or 0)
        interval = int(self._param('remind_interval', '7') or 0)
        today = fields.Date.context_today(self)
        domain = [
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
            ('payment_state', 'in', ('not_paid', 'partial')),
            ('amount_residual', '>', 0),
            ('invoice_date_due', '<=', today - timedelta(days=max(overdue_days, 1))),
            ('company_id', 'in', self.env.companies.ids),
        ]
        invoices = self.env['account.move'].search(domain, order='invoice_date_due, id')
        if interval > 0 and invoices:
            since = fields.Datetime.now() - timedelta(days=interval)
            reminded = self.env['raseel.wa.message'].sudo().search([
                ('res_model', '=', 'account.move'),
                ('res_id', 'in', invoices.ids),
                ('message_key', '=', 'invoice_overdue'),
                ('date', '>=', since),
            ])
            done_ids = set(reminded.mapped('res_id'))
            invoices = invoices.filtered(lambda inv: inv.id not in done_ids)
        return invoices

    @api.model
    def _cron_overdue_activities(self):
        """Daily: remind salespeople (as a To-Do) to send the WhatsApp payment reminders."""
        if self._param('reminder_activity', 'False') != 'True' or 'account.move' not in self.env:
            return
        activity_type = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
        if not activity_type:
            return
        summary = _("Send a WhatsApp payment reminder")
        for company in self.env['res.company'].search([]):
            invoices = self.with_company(company).with_context(
                allowed_company_ids=company.ids)._raseel_wa_overdue_invoices()
            for invoice in invoices:
                if invoice.activity_ids.filtered(lambda a: a.summary == summary):
                    continue
                user = invoice.invoice_user_id or invoice.create_uid
                invoice.activity_schedule(
                    activity_type_id=activity_type.id,
                    summary=summary,
                    note=_("The invoice is overdue: open it and use the WhatsApp button to remind the customer."),
                    user_id=user.id if user and user.active else self.env.uid,
                )

    # ------------------------------------------------------------------
    # Steps
    # ------------------------------------------------------------------
    def _action_reopen(self, name=None):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': name or _("Send by WhatsApp"),
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'views': [(False, 'form')],
            'target': 'new',
            'context': dict(self.env.context, dialog_size='extra-large'),
        }

    def _records(self):
        self.ensure_one()
        if not self.res_model or self.res_model not in self.env:
            return self.env['res.partner'].browse()
        ids = [int(i) for i in (self.res_ids or '').split(',') if i.strip().isdigit()]
        return self.env[self.res_model].browse(ids).exists()

    def action_prepare(self):
        """Build one ready message per document."""
        self.ensure_one()
        self.line_ids.unlink()
        Composer = self.env['raseel.wa.composer'].with_context(raseel_wa_source=self.source)
        composers = []
        for record in self._records():
            vals = {'res_model': record._name, 'res_id': record.id,
                    'link_type': self.link_type, 'log_note': self.log_note}
            composer = Composer.create(vals)
            changes = {}
            if self.style != 'auto' and composer.style != self.style:
                changes['style'] = self.style
            if self.template_id:
                changes['template_id'] = self.template_id.id
            elif changes:
                changes['template_id'] = self.env['raseel.wa.template']._raseel_wa_pick(
                    record._name, composer.message_key or 'any', changes['style']).id
            if changes:
                composer.write(changes)
            composers.append(composer)
        # contacts with a valid number first, the ones to fix at the end
        composers.sort(key=lambda c: 0 if c.phone_valid else 1)
        vals_list = [{'bulk_id': self.id, 'sequence': seq, 'composer_id': c.id, 'body': c.body}
                     for seq, c in enumerate(composers, start=1)]
        if not vals_list:
            raise UserError(_("The selected documents no longer exist."))
        self.env['raseel.wa.bulk.line'].create(vals_list)
        self.state = 'send'
        return self._action_reopen()

    def _next_or_done(self):
        if not self.line_ids.filtered(lambda l: l.state == 'pending'):
            self.state = 'done'

    def action_send_current(self):
        """Open the current chat in WhatsApp, log it and move to the next one."""
        self.ensure_one()
        line = self.current_line_id
        if not line:
            self.state = 'done'
            return self._action_reopen()
        url = line._send()
        self._next_or_done()
        return {'type': 'ir.actions.act_url', 'url': url, 'target': 'new'}

    def action_skip_current(self):
        self.ensure_one()
        if self.current_line_id:
            self.current_line_id.state = 'skipped'
        self._next_or_done()
        return self._action_reopen()

    def action_back_to_setup(self):
        self.ensure_one()
        self.line_ids.unlink()
        self.state = 'setup'
        return self._action_reopen()

    def action_restart_skipped(self):
        self.ensure_one()
        self.line_ids.filtered(lambda l: l.state == 'skipped').write({'state': 'pending'})
        self.state = 'send' if self.line_ids.filtered(lambda l: l.state == 'pending') else self.state
        return self._action_reopen()


class RaseelWaBulkLine(models.TransientModel):
    _name = 'raseel.wa.bulk.line'
    _description = 'WhatsApp Bulk Sending - Message'
    _order = 'sequence, id'

    bulk_id = fields.Many2one('raseel.wa.bulk', required=True, ondelete='cascade', index=True)
    sequence = fields.Integer(default=10)
    composer_id = fields.Many2one('raseel.wa.composer', required=True, ondelete='cascade')
    state = fields.Selection([('pending', 'To send'), ('sent', 'Sent'), ('skipped', 'Skipped')],
                             default='pending', required=True)
    record_name = fields.Char('Document', related='composer_id.record_name')
    partner_id = fields.Many2one('res.partner', 'Recipient', related='composer_id.partner_id')
    phone = fields.Char('Mobile', related='composer_id.phone', readonly=False)
    phone_display = fields.Char('Number', related='composer_id.phone_display')
    phone_valid = fields.Boolean('Valid Number', related='composer_id.phone_valid')
    template_id = fields.Many2one('raseel.wa.template', 'Template', related='composer_id.template_id')
    body = fields.Text('Message')
    preview = fields.Html('Preview', compute='_compute_preview', sanitize=False)

    @api.depends('body')
    def _compute_preview(self):
        for line in self:
            line.preview = render_preview(line.body)

    def _send(self):
        self.ensure_one()
        composer = self.composer_id
        if composer.body != self.body:
            composer.body = self.body
        composer._check_sendable()
        url = composer._wa_url()
        composer._log_sent(self.bulk_id.source)
        self.state = 'sent'
        return url

    def action_send_line(self):
        """Send this line now (from the list), whatever its position in the queue."""
        self.ensure_one()
        url = self._send()
        self.bulk_id._next_or_done()
        return {'type': 'ir.actions.act_url', 'url': url, 'target': 'new'}
