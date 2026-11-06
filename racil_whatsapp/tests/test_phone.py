# -*- coding: utf-8 -*-
from odoo.tests import BaseCase, tagged

from ..models.phone_intl import normalize


@tagged('post_install', '-at_install', 'racil_wa')
class TestIntlPhone(BaseCase):

    def assertWa(self, raw, expected, country='SA', valid=True):
        res = normalize(raw, country)
        self.assertEqual(res['number'], expected, raw)
        self.assertEqual(res['valid'], valid, raw)

    def test_saudi(self):
        for raw in ('0501234567', '501234567', '+966501234567', '00966501234567', '966501234567',
                    '+966 050 123 4567', '(050) 123-4567', '٠٥٠١٢٣٤٥٦٧', '۰۵۰۱۲۳۴۵۶۷', '+٩٦٦٥٠١٢٣٤٥٦٧',
                    '‏050 123 4567', '050.123.4567'):
            self.assertWa(raw, '966501234567')

    def test_arab_countries(self):
        self.assertWa('0501234567', '971501234567', 'AE')
        self.assertWa('+971 50 123 4567', '971501234567')
        self.assertWa('00971501234567', '971501234567')
        self.assertWa('51234567', '96551234567', 'KW')
        self.assertWa('+965 9123 4567', '96591234567')
        self.assertWa('33123456', '97433123456', 'QA')
        self.assertWa('36123456', '97336123456', 'BH')
        self.assertWa('92123456', '96892123456', 'OM')
        self.assertWa('01012345678', '201012345678', 'EG')
        self.assertWa('+20 010 1234 5678', '201012345678')
        self.assertWa('0791234567', '962791234567', 'JO')

    def test_foreign_number_with_default_saudi(self):
        # a UAE number typed with its code but without "+" while the default country is Saudi Arabia
        self.assertWa('971501234567', '971501234567', 'SA')
        self.assertEqual(normalize('971501234567', 'SA')['country'], 'AE')

    def test_other_international(self):
        self.assertWa('+44 7400 123456', '447400123456')
        self.assertWa('07400123456', '447400123456', 'GB')
        self.assertWa('(415) 555-2671', '14155552671', 'US')
        self.assertWa('0612345678', '33612345678', 'FR')
        self.assertWa('03001234567', '923001234567', 'PK')
        self.assertWa('8 912 345 6789', '79123456789', 'RU')
        self.assertWa('9876543210', '919876543210', 'IN')
        self.assertWa('081234567890', '6281234567890', 'ID')

    def test_invalid(self):
        self.assertWa('0112345678', '966112345678', valid=False)  # Riyadh landline, not WhatsApp mobile
        self.assertWa('', '', valid=False)
        self.assertWa('abc', '', valid=False)

    def test_extension_and_display(self):
        res = normalize('0501234567 ext 12', 'SA')
        self.assertEqual(res['number'], '966501234567')
        self.assertEqual(res['display'], '+966 50 123 4567')
        self.assertEqual(normalize('51234567', 'KW')['display'], '+965 5123 4567')
