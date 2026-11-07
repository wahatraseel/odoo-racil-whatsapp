# -*- coding: utf-8 -*-
import re
from urllib.parse import quote

from markupsafe import Markup, escape

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError
from odoo.tools.misc import format_amount, format_date

from ..models import phone_intl
from ..models.raseel_wa_template import MESSAGE_KEYS, STYLES, body_has_link, render_body

PARAM = 'raseel_whatsapp.%s'

OPEN_MODES = {
    'wa_me': 'https://wa.me/{number}?text={text}',
    'api': 'https://api.whatsapp.com/send?phone={number}&text={text}',
    'web': 'https://web.whatsapp.com/send?phone={number}&text={text}',
}


def render_preview(body):
    """WhatsApp-like bubble (HTML) for a message, with *bold* _italic_ ~strike~ formatting."""
    html = str(escape(body or ''))
    html = re.sub(r'(?<![\w*])\*(?!\s)([^*\n]+?)(?<!\s)\*(?![\w*])', r'<b>\1</b>', html)
    html = re.sub(r'(?<![\w_])_(?!\s)([^_\n]+?)(?<!\s)_(?![\w_])', r'<i>\1</i>', html)
    html = re.sub(r'(?<![\w~])~(?!\s)([^~\n]+?)(?<!\s)~(?![\w~])', r'<s>\1</s>', html)
    html = re.sub(r'(https?://[^\s<]+)', r'<span class="o_raseel_wa_link">\1</span>', html)
    html = html.replace('\n', '<br/>')
    return Markup('<div class="o_raseel_wa_chat"><div class="o_raseel_wa_bubble" dir="auto">%s'
                  '<span class="o_raseel_wa_meta">✓✓</span></div></div>') % Markup(html)


class RaseelWaComposer(models.TransientModel):
    _name = 'raseel.wa.composer'
    _description = 'Send by WhatsApp'

    res_model = fields.Char('Document Model', required=True, readonly=True)
    res_id = fields.Integer('Document ID', required=True, readonly=True)
    record_name = fields.Char('Document', compute='_compute_record_info')
    message_key = fields.Char(compute='_compute_record_info')
    partner_id = fields.Many2one('res.partner', 'Recipient', compute='_compute_partner', store=True, readonly=False)

    phone = fields.Char('Mobile', compute='_compute_phone', store=True, readonly=False)
    country_code = fields.Selection(phone_intl.COUNTRY_SELECTION, 'Country',
                                    compute='_compute_country_code', store=True, readonly=False,
                                    help="Used when the number is typed without its country code.")
    wa_number = fields.Char('WhatsApp Number', compute='_compute_wa_number')
    phone_valid = fields.Boolean(compute='_compute_wa_number')
    phone_display = fields.Char('Will be sent to', compute='_compute_wa_number')

    style = fields.Selection(STYLES, 'Language', compute='_compute_style', store=True, readonly=False)
    template_id = fields.Many2one('raseel.wa.template', 'Template', compute='_compute_template_id',
                                  store=True, readonly=False,
                                  domain="['|', ('model_name', '=', False), ('model_name', '=', res_model), "
                                         "'|', ('user_id', '=', False), ('user_id', '=', uid)]")
    has_link = fields.Boolean(compute='_compute_record_info')
    link_type = fields.Selection([('portal', 'Customer portal page'), ('pdf', 'Direct PDF download')],
                                 'Link', default=lambda self: self._param('link_type', 'portal'))
    body = fields.Text('Message', compute='_compute_body', store=True, readonly=False)
    preview = fields.Html('Preview', compute='_compute_preview', sanitize=False)
    log_note = fields.Boolean('Log in chatter', default=lambda self: self._param('log_chatter', 'True') == 'True')
    save_template = fields.Boolean('Save as my template',
                                   help="Keep this wording as a personal template for the next time.")
    new_template_name = fields.Char('Template Name')

    # ------------------------------------------------------------------
    def _param(self, key, default=False):
        return self.env['ir.config_parameter'].sudo().get_param(PARAM % key, default)

    def _record(self):
        self.ensure_one()
        if not self.res_model or self.res_model not in self.env or not self.res_id:
            return None
        return self.env[self.res_model].browse(self.res_id).exists() or None

    def _config(self):
        return self.env['raseel.wa.document']._raseel_wa_config_for(self.res_model)

    @api.depends('res_model', 'res_id')
    def _compute_record_info(self):
        for wiz in self:
            rec = wiz._record()
            wiz.record_name = rec.display_name if rec else ''
            wiz.message_key = rec._raseel_wa_message_key() if rec else 'any'
            wiz.has_link = bool(rec and rec._raseel_wa_link())

    @api.depends('res_model', 'res_id')
    def _compute_partner(self):
        for wiz in self:
            rec = wiz._record()
            wiz.partner_id = rec._raseel_wa_partner(wiz._config()) if rec else False

    @api.depends('partner_id')
    def _compute_country_code(self):
        default = (self._param('default_country') or '').upper()
        if default not in phone_intl.COUNTRIES:
            company_code = (self.env.company.country_id.code or '').upper()
            default = company_code if company_code in phone_intl.COUNTRIES else 'SA'
        for wiz in self:
            code = (wiz.partner_id.country_id.code or '').upper()
            wiz.country_code = code if code in phone_intl.COUNTRIES else default

    @api.depends('partner_id', 'country_code')
    def _compute_phone(self):
        for wiz in self:
            rec = wiz._record()
            candidates = []
            if rec:
                candidates = rec._raseel_wa_phone_candidates(wiz._config())
                if wiz.partner_id and wiz.partner_id != rec._raseel_wa_partner(wiz._config()):
                    candidates = [n for n in (wiz.partner_id['mobile'] if 'mobile' in wiz.partner_id._fields else False,
                                              wiz.partner_id.phone) if n] + candidates
            elif wiz.partner_id:
                candidates = [n for n in (wiz.partner_id.phone,) if n]
            best = next((n for n in candidates if phone_intl.normalize(n, wiz.country_code)['valid']), False)
            wiz.phone = best or (candidates[0] if candidates else False)

    @api.depends('phone', 'country_code')
    def _compute_wa_number(self):
        for wiz in self:
            res = phone_intl.normalize(wiz.phone or '', wiz.country_code or 'SA')
            wiz.wa_number = res['number']
            wiz.phone_valid = res['valid']
            label = phone_intl.country_label(res['country'], self.env.lang or 'en')
            wiz.phone_display = ('%s  %s' % (res['display'], label)).strip() if res['number'] else ''

    @api.depends('partner_id')
    def _compute_style(self):
        default = self._param('default_style', 'msa')
        for wiz in self:
            lang = wiz.partner_id.lang or ''
            wiz.style = 'en' if lang and not lang.startswith('ar') else default

    @api.depends('style', 'res_model', 'res_id')
    def _compute_template_id(self):
        Template = self.env['raseel.wa.template']
        for wiz in self:
            wiz.template_id = Template._raseel_wa_pick(wiz.res_model, wiz.message_key or 'any', wiz.style or 'msa')

    def _render_values(self):
        self.ensure_one()
        rec = self._record()
        partner = self.partner_id
        values = {
            'partner': partner.name or '',
            'company': self.env.company.name,
            'user': self.env.user.name,
        }
        if not rec:
            return values
        lang = 'en_US' if self.style == 'en' else self.env.lang

        def first(*names):
            for name in names:
                if name in rec._fields and rec[name]:
                    return rec[name]
            return False
        if 'company_id' in rec._fields and rec.company_id:
            values['company'] = rec.company_id.name
        values['doc'] = (rec.name if 'name' in rec._fields and isinstance(rec.name, str) and rec.name
                         and rec.name != '/' else rec.display_name) or ''
        currency = first('currency_id') or self.env.company.currency_id
        amount = first('amount_total')
        if amount is not False:
            values['amount'] = format_amount(self.env, amount, currency, lang_code=lang)
        if 'amount_residual' in rec._fields:
            values['residual'] = format_amount(self.env, rec.amount_residual, currency, lang_code=lang)
        due = first('invoice_date_due', 'validity_date', 'date_deadline', 'scheduled_date', 'date_planned')
        if due:
            values['due_date'] = format_date(self.env, due, lang_code=lang)
        date = first('invoice_date', 'date_order', 'date_done', 'scheduled_date', 'date')
        if date:
            values['date'] = format_date(self.env, date, lang_code=lang)
        values['link'] = rec._raseel_wa_link(self.link_type or 'portal')
        return values

    @api.depends('template_id', 'link_type', 'partner_id')
    def _compute_body(self):
        for wiz in self:
            if not wiz.template_id:
                wiz.body = wiz.body or ''
                continue
            values = wiz._render_values()
            text = render_body(wiz.template_id.body, values)
            if values.get('link') and not body_has_link(wiz.template_id.body):
                text = '%s\n%s' % (text.rstrip(), values['link'])
            # remove lines left empty by a missing placeholder, keep paragraph breaks
            wiz.body = re.sub(r'\n{3,}', '\n\n', text).strip()

    @api.depends('body')
    def _compute_preview(self):
        for wiz in self:
            wiz.preview = render_preview(wiz.body)

    # ------------------------------------------------------------------
    def _wa_url(self):
        self.ensure_one()
        mode = self._param('open_mode', 'wa_me')
        pattern = OPEN_MODES.get(mode, OPEN_MODES['wa_me'])
        return pattern.format(number=self.wa_number, text=quote(self.body or '', safe=''))

    def _check_sendable(self):
        self.ensure_one()
        if not self.wa_number or len(self.wa_number) < 7:
            raise UserError(_("Please enter the recipient's mobile number."))
        if not (self.body or '').strip():
            raise UserError(_("The message is empty."))

    def _log_sent(self, source='single'):
        """Chatter note + statistics line, then the personal template if asked."""
        self.ensure_one()
        rec = self._record()
        if self.log_note and rec is not None and hasattr(rec, 'message_post'):
            note = Markup('<p><b>%s</b> %s</p><p>%s</p>') % (
                _("WhatsApp message sent to"),
                self.phone_display or ('+' + self.wa_number),
                Markup('<br/>').join(escape(line) for line in (self.body or '').split('\n')),
            )
            try:
                with self.env.cr.savepoint():
                    rec.sudo(False).message_post(body=note, message_type='comment',
                                                 subtype_xmlid='mail.mt_note')
            except AccessError:
                # users allowed to read the document but not to post on it (e.g. contacts):
                # the note is still logged, under their name
                rec.sudo().message_post(body=note, message_type='comment', subtype_xmlid='mail.mt_note',
                                        author_id=self.env.user.partner_id.id)
        company = self.env.company
        if rec is not None and 'company_id' in rec._fields and rec.company_id:
            company = rec.company_id
        Message = self.env['raseel.wa.message']
        Message.sudo().create({
            'user_id': self.env.uid,
            'company_id': company.id,
            'partner_id': self.partner_id.id,
            'res_model': self.res_model,
            'res_id': self.res_id,
            'record_name': self.record_name,
            'document_id': self._config().id,
            'message_key': self.message_key if self.message_key in dict(MESSAGE_KEYS) else 'any',
            'style': self.style,
            'template_id': self.template_id.id,
            'source': source,
            'phone': self.phone_display or ('+' + self.wa_number),
            'body': self.body,
        })
        if self.save_template:
            self._save_personal_template()

    def _save_personal_template(self):
        self.ensure_one()
        name = (self.new_template_name or '').strip() or _("My template - %s", self.record_name or self.res_model)
        return self.env['raseel.wa.template'].create({
            'name': name,
            'body': self.body,
            'key': self.message_key if self.message_key in dict(MESSAGE_KEYS) else 'any',
            'style': self.style or 'msa',
            'model_name': self.res_model,
            'user_id': self.env.uid,
            'sequence': 1,
        })

    def action_send(self):
        self._check_sendable()
        url = self._wa_url()
        self._log_sent(self.env.context.get('raseel_wa_source', 'single'))
        return {'type': 'ir.actions.act_url', 'url': url, 'target': 'new', 'close': True}

    def action_open_contact(self):
        self.ensure_one()
        if not self.partner_id:
            return False
        return {
            'type': 'ir.actions.act_window', 'res_model': 'res.partner',
            'res_id': self.partner_id.id, 'view_mode': 'form', 'target': 'current',
        }
