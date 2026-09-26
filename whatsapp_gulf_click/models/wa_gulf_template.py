# -*- coding: utf-8 -*-
import re

from odoo import api, fields, models

MESSAGE_KEYS = [
    ('any', 'General / any document'),
    ('contact', 'Contact / lead greeting'),
    ('invoice_open', 'Invoice ready'),
    ('invoice_overdue', 'Payment reminder (overdue)'),
    ('invoice_paid', 'Thank you for your payment'),
    ('refund', 'Credit note'),
    ('quotation', 'Quotation ready'),
    ('sale_confirmed', 'Order confirmed'),
    ('purchase', 'Purchase order to vendor'),
    ('delivery', 'Delivery / shipment'),
    ('received', 'Thank you after receipt'),
]

STYLES = [
    ('msa', 'Arabic (formal)'),
    ('gulf', 'Arabic (Gulf dialect)'),
    ('en', 'English'),
]

# canonical placeholder -> Arabic aliases accepted in templates
PLACEHOLDERS = {
    'partner': ['العميل', 'الاسم'],
    'company': ['الشركة', 'المنشأة'],
    'doc': ['المستند', 'الرقم'],
    'amount': ['المبلغ'],
    'residual': ['المتبقي'],
    'due_date': ['الاستحقاق', 'الصلاحية'],
    'date': ['التاريخ'],
    'link': ['الرابط'],
    'user': ['الموظف', 'المرسل'],
}
_ALIAS = {}
for _key, _aliases in PLACEHOLDERS.items():
    _ALIAS[_key] = _key
    for _a in _aliases:
        _ALIAS[_a] = _key
_TOKEN_RE = re.compile(r'\{([^{}\s]{1,30})\}')


def render_body(body, values):
    """Replace {placeholders} (English or Arabic) - unknown tokens are left untouched."""
    def _sub(match):
        key = _ALIAS.get(match.group(1))
        if key is None:
            return match.group(0)
        return values.get(key) or ''
    return _TOKEN_RE.sub(_sub, body or '')


def body_has_link(body):
    return any(tok in (body or '') for tok in ('{link}', '{الرابط}'))


class WaGulfTemplate(models.Model):
    _name = 'wa.gulf.template'
    _description = 'WhatsApp Message Template'
    _order = 'sequence, id'

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    model_name = fields.Char(
        'Document Model',
        help="Technical model this template is meant for (account.move, sale.order...). "
             "Leave empty to offer it on every document.")
    key = fields.Selection(MESSAGE_KEYS, 'Situation', required=True, default='any',
                           help="Used to pick the right template automatically (e.g. an overdue invoice "
                                "gets the payment reminder).")
    style = fields.Selection(STYLES, 'Language Style', required=True, default='msa')
    body = fields.Text(
        'Message', required=True,
        help="Placeholders: {partner} {company} {doc} {amount} {residual} {due_date} {date} {link} {user}\n"
             "Arabic aliases: {العميل} {الشركة} {المستند} {المبلغ} {المتبقي} {الاستحقاق} {التاريخ} {الرابط} {الموظف}\n"
             "WhatsApp formatting works too: *bold* _italic_ ~strike~")

    @api.model
    def _wa_gulf_pick(self, model_name, key, style):
        """Best template for a document situation and a language style."""
        templates = self.search(['|', ('model_name', '=', False), ('model_name', '=', model_name)])

        def score(tpl):
            return (
                0 if tpl.style == style else 1,
                0 if tpl.key == key else (1 if tpl.key == 'any' else 2),
                0 if tpl.model_name == model_name else 1,
                tpl.sequence,
                tpl.id,
            )
        candidates = templates.filtered(lambda t: t.key in (key, 'any'))
        if not candidates:
            return self.browse()
        return min(candidates, key=score)
