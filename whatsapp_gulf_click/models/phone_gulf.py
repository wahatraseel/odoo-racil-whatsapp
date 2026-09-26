# -*- coding: utf-8 -*-
"""Pure-python phone normalisation tuned for Gulf / Arab mobile numbers.

No external dependency (no `phonenumbers`), so the module installs anywhere,
including Odoo.sh, without extra python requirements.

The function understands what people actually type in Saudi Arabia, the UAE,
Kuwait, Qatar, Bahrain, Oman and neighbouring Arab countries:

* Arabic-Indic (٠١٢٣٤٥٦٧٨٩) and Persian (۰۱۲۳۴۵۶۷۸۹) digits
* spaces, dashes, dots, parentheses, the invisible RTL/LTR marks
* ``+966``, ``00966``, ``966`` prefixes, or none at all
* the local trunk zero (``05x...``) and the classic mistake ``+966 05x...``
"""
import re

# ISO code: (dialing code, national mobile pattern (without trunk 0), trunk "0" used, flag, Arabic name, English name)
COUNTRIES = {
    'SA': ('966', r'5\d{8}', True, '🇸🇦', 'السعودية', 'Saudi Arabia'),
    'AE': ('971', r'5[024568]\d{7}', True, '🇦🇪', 'الإمارات', 'United Arab Emirates'),
    'KW': ('965', r'(?:[569]\d{7}|41\d{6})', False, '🇰🇼', 'الكويت', 'Kuwait'),
    'QA': ('974', r'[3567]\d{7}', False, '🇶🇦', 'قطر', 'Qatar'),
    'BH': ('973', r'(?:3\d|6[36])\d{6}', False, '🇧🇭', 'البحرين', 'Bahrain'),
    'OM': ('968', r'[79]\d{7}', False, '🇴🇲', 'عُمان', 'Oman'),
    'EG': ('20', r'1[0125]\d{8}', True, '🇪🇬', 'مصر', 'Egypt'),
    'JO': ('962', r'7[789]\d{7}', True, '🇯🇴', 'الأردن', 'Jordan'),
    'YE': ('967', r'7[01378]\d{7}', True, '🇾🇪', 'اليمن', 'Yemen'),
    'IQ': ('964', r'7[3-9]\d{8}', True, '🇮🇶', 'العراق', 'Iraq'),
    'SD': ('249', r'[19]\d{8}', True, '🇸🇩', 'السودان', 'Sudan'),
    'LB': ('961', r'(?:3\d{6}|7[01689]\d{6}|81\d{6})', True, '🇱🇧', 'لبنان', 'Lebanon'),
    'SY': ('963', r'9\d{8}', True, '🇸🇾', 'سوريا', 'Syria'),
    'PS': ('970', r'5[69]\d{7}', True, '🇵🇸', 'فلسطين', 'Palestine'),
    'MA': ('212', r'[67]\d{8}', True, '🇲🇦', 'المغرب', 'Morocco'),
    'DZ': ('213', r'[567]\d{8}', True, '🇩🇿', 'الجزائر', 'Algeria'),
    'TN': ('216', r'[2459]\d{7}', False, '🇹🇳', 'تونس', 'Tunisia'),
    'LY': ('218', r'9[1-6]\d{7}', True, '🇱🇾', 'ليبيا', 'Libya'),
}

GULF_FIRST = ['SA', 'AE', 'KW', 'QA', 'BH', 'OM']

# country selection usable directly in a fields.Selection
COUNTRY_SELECTION = [
    (iso, '%s %s' % (COUNTRIES[iso][3], COUNTRIES[iso][5]))
    for iso in GULF_FIRST + sorted(set(COUNTRIES) - set(GULF_FIRST), key=lambda c: COUNTRIES[c][5])
]

_DIGIT_MAP = {ord(a): str(i) for i, a in enumerate('٠١٢٣٤٥٦٧٨٩')}
_DIGIT_MAP.update({ord(a): str(i) for i, a in enumerate('۰۱۲۳۴۵۶۷۸۹')})
_CODE_TO_ISO = {}
for _iso, _data in COUNTRIES.items():
    _CODE_TO_ISO.setdefault(_data[0], _iso)
# longest codes first so that "20" (Egypt) never shadows a 3-digit code
_CODES_SORTED = sorted(_CODE_TO_ISO, key=len, reverse=True)


def to_ascii_digits(value):
    return (value or '').translate(_DIGIT_MAP)


def _clean(raw):
    value = to_ascii_digits(raw).strip()
    # cut an extension such as "ext 12", "x12" or "تحويلة 12"
    value = re.split(r'(?i)\s*(?:ext\.?|extension|x|تحويلة|داخلي)\s*\d+\s*$', value)[0]
    plus = value.startswith('+')
    digits = re.sub(r'\D', '', value)
    return plus, digits


def _match(iso, national):
    """Return the national significant number if ``national`` is a valid mobile of ``iso``."""
    code, pattern, trunk = COUNTRIES[iso][:3]
    candidate = national.lstrip('0') if trunk or national.startswith('0') else national
    if re.fullmatch(pattern, candidate):
        return candidate
    return None


def _result(digits, iso=None, valid=False, national=''):
    return {
        'number': digits,                      # digits only, international, no "+" (what wa.me wants)
        'e164': '+' + digits if digits else '',
        'country': iso,
        'valid': bool(valid and digits),
        'national': national,
        'display': format_display(digits, iso) if digits else '',
    }


def format_display(digits, iso=None):
    """Human friendly: +966 50 123 4567"""
    if not digits:
        return ''
    code = COUNTRIES[iso][0] if iso in COUNTRIES else None
    if not code or not digits.startswith(code):
        return '+' + digits
    rest = digits[len(code):]
    if len(rest) == 9:
        groups = [rest[:2], rest[2:5], rest[5:]]
    elif len(rest) == 10:
        groups = [rest[:3], rest[3:6], rest[6:]]
    elif len(rest) == 8:
        groups = [rest[:4], rest[4:]]
    else:
        groups = [rest]
    return '+%s %s' % (code, ' '.join(groups))


def normalize(raw, default_country='SA'):
    """Normalise a phone number for WhatsApp click-to-chat.

    :param raw: what the user typed
    :param default_country: ISO code used for numbers typed without country code
    :return: dict(number, e164, country, valid, national, display)
    """
    plus, digits = _clean(raw)
    if not digits:
        return _result('')
    default_country = (default_country or 'SA').upper()

    international = plus or digits.startswith('00')
    if digits.startswith('00'):
        digits = digits[2:]

    if international:
        for code in _CODES_SORTED:
            if digits.startswith(code):
                iso = _CODE_TO_ISO[code]
                national = _match(iso, digits[len(code):])
                if national:
                    return _result(code + national, iso, True, national)
                rest = digits[len(code):].lstrip('0')
                return _result(code + rest, iso, False, rest)
        # unknown country code: trust the user if length is plausible (E.164)
        return _result(digits, None, 7 <= len(digits) <= 15, digits)

    # 1) national number of the default country (05xxxxxxxx / 5xxxxxxxx)
    if default_country in COUNTRIES:
        national = _match(default_country, digits)
        if national:
            code = COUNTRIES[default_country][0]
            return _result(code + national, default_country, True, national)

    # 2) typed with a country code but without "+" / "00" (9665xxxxxxxx)
    for code in _CODES_SORTED:
        if digits.startswith(code):
            iso = _CODE_TO_ISO[code]
            national = _match(iso, digits[len(code):])
            if national:
                return _result(code + national, iso, True, national)

    # 3) give our best guess, flagged as not valid so the user can review it
    if default_country in COUNTRIES:
        code = COUNTRIES[default_country][0]
        rest = digits.lstrip('0')
        return _result(code + rest, default_country, False, rest)
    return _result(digits, None, False, digits)


def country_label(iso, lang='ar'):
    if iso not in COUNTRIES:
        return ''
    data = COUNTRIES[iso]
    return '%s %s' % (data[3], data[4] if (lang or '').startswith('ar') else data[5])
