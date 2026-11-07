# -*- coding: utf-8 -*-
"""Pure-python phone normalisation for WhatsApp click-to-chat, for every country.

No external dependency (no `phonenumbers` at runtime): the dialing data ships in
``countries_data.py``, so the module installs anywhere, including Odoo.sh and Odoo Online.

It understands what people actually type:

* Arabic-Indic (٠١٢٣٤٥٦٧٨٩) and Persian (۰۱۲۳۴۵۶۷۸۹) digits
* spaces, dashes, dots, parentheses, the invisible RTL/LTR marks
* ``+966``, ``00966``, ``966`` prefixes, or none at all
* the local trunk prefix (``05x...``, ``07700...``, ``8 9xx...``) and mistakes such as ``+966 05x...``
"""
import re

from .countries_data import COUNTRIES, MAIN_COUNTRY_FOR_CODE

# shown first in country pickers (largest user base of this module), then every other country A-Z
PRIORITY = ['SA', 'AE', 'KW', 'QA', 'BH', 'OM', 'EG', 'JO', 'IQ', 'YE', 'SD', 'LB', 'SY', 'PS',
            'MA', 'DZ', 'TN', 'LY', 'TR', 'PK', 'IN', 'BD', 'ID', 'MY', 'NG', 'GB', 'US', 'FR', 'DE']
PRIORITY = [iso for iso in PRIORITY if iso in COUNTRIES]

COUNTRY_SELECTION = [
    (iso, '%s %s' % (COUNTRIES[iso][3], COUNTRIES[iso][5]))
    for iso in PRIORITY + sorted(set(COUNTRIES) - set(PRIORITY), key=lambda c: COUNTRIES[c][5])
]

_DIGIT_MAP = {ord(a): str(i) for i, a in enumerate('٠١٢٣٤٥٦٧٨٩')}
_DIGIT_MAP.update({ord(a): str(i) for i, a in enumerate('۰۱۲۳۴۵۶۷۸۹')})

# dialing code -> countries sharing it, main country first
_CODE_TO_ISOS = {}
for _iso in sorted(COUNTRIES):
    _CODE_TO_ISOS.setdefault(COUNTRIES[_iso][0], []).append(_iso)
for _code, _isos in _CODE_TO_ISOS.items():
    _main = MAIN_COUNTRY_FOR_CODE.get(_code)
    if _main in _isos:
        _isos.remove(_main)
        _isos.insert(0, _main)
# longest codes first so that "20" (Egypt) never shadows "212" (Morocco)
_CODES_SORTED = sorted(_CODE_TO_ISOS, key=len, reverse=True)
_PATTERNS = {iso: re.compile(data[1]) for iso, data in COUNTRIES.items()}


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
    trunk = COUNTRIES[iso][2]
    candidates = [national]
    if trunk and national.startswith(trunk):
        candidates.insert(0, national[len(trunk):])
    if national.startswith('0'):
        candidates.append(national.lstrip('0'))
    for candidate in candidates:
        if candidate and _PATTERNS[iso].fullmatch(candidate):
            return candidate
    return None


def _match_code(code, national):
    """Try every country sharing ``code``; return (iso, national) or (main iso, None)."""
    isos = _CODE_TO_ISOS[code]
    for iso in isos:
        found = _match(iso, national)
        if found:
            return iso, found
    return isos[0], None


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
    elif len(rest) == 7:
        groups = [rest[:3], rest[3:]]
    else:
        groups = [rest]
    return '+%s %s' % (code, ' '.join(groups))


def _strip_trunk(iso, national):
    trunk = COUNTRIES[iso][2] if iso in COUNTRIES else ''
    if trunk and national.startswith(trunk):
        return national[len(trunk):]
    return national.lstrip('0')


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
                iso, national = _match_code(code, digits[len(code):])
                if national:
                    return _result(code + national, iso, True, national)
                rest = _strip_trunk(iso, digits[len(code):])
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
        if len(code) > 1 and digits.startswith(code):
            iso, national = _match_code(code, digits[len(code):])
            if national:
                return _result(code + national, iso, True, national)

    # 3) give our best guess, flagged as not valid so the user can review it
    if default_country in COUNTRIES:
        code = COUNTRIES[default_country][0]
        rest = _strip_trunk(default_country, digits)
        return _result(code + rest, default_country, False, rest)
    return _result(digits, None, False, digits)


def country_label(iso, lang='ar'):
    if iso not in COUNTRIES:
        return ''
    data = COUNTRIES[iso]
    return '%s %s' % (data[3], data[4] if (lang or '').startswith('ar') else data[5])
