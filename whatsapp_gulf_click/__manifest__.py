# -*- coding: utf-8 -*-
{
    "name": "Gulf WhatsApp Button | زر واتساب الخليجي — Free, No API",
    "summary": "One-click WhatsApp for invoices, quotations, orders, deliveries & contacts — "
               "auto-formats Saudi/UAE/Kuwait/Qatar/Bahrain/Oman numbers, ready Arabic (formal & Gulf) "
               "and English messages, portal/PDF link, no Meta API, no subscription. "
               "زر واتساب مجاني للفواتير وعروض الأسعار مع تنسيق أرقام الخليج ورسائل عربية جاهزة",
    "description": """
Gulf WhatsApp Button: send invoices, quotations, orders, purchase orders, deliveries and any
document to customers on WhatsApp in one click. Free forever: no WhatsApp Business API, no Meta
account, no monthly fee. Gulf-aware phone formatting, ready Arabic (formal and Gulf dialect) and
English messages, smart template choice, portal or PDF link, chatter log.
""",
    "version": "18.0.1.0.0",
    "category": "Productivity/Discuss",
    "author": "Mostafa Ibrahim Salem",
    "website": "https://github.com/mostafasalem3500-prog/odoo-whatsapp-gulf",
    "license": "LGPL-3",
    "depends": ["mail"],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_config_parameter_data.xml",
        "data/wa_gulf_document_data.xml",
        "data/wa_gulf_template_data.xml",
        "wizard/wa_gulf_composer_views.xml",
        "views/wa_gulf_template_views.xml",
        "views/res_config_settings_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "whatsapp_gulf_click/static/src/scss/wa_gulf.scss",
        ],
    },
    "images": ["static/description/banner.png"],
    "application": False,
    "installable": True,
    "price": 0,
    "currency": "USD",
}
