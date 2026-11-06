# -*- coding: utf-8 -*-
{
    "name": "Racil WhatsApp Button | زر واتساب رسيل — Free, No API, All Countries",
    "summary": "One-click WhatsApp for invoices, quotations, orders, deliveries & contacts — "
               "auto-formats phone numbers for 240+ countries, ready Arabic & English messages, "
               "portal/PDF link, no Meta API, no subscription. "
               "زر واتساب مجاني للفواتير وعروض الأسعار لكل دول العالم مع رسائل عربية وإنجليزية جاهزة",
    "description": """
Racil WhatsApp Button: send invoices, quotations, orders, purchase orders, deliveries and any
document to customers on WhatsApp in one click. Free forever: no WhatsApp Business API, no Meta
account, no monthly fee. Phone formatting for 240+ countries, ready Arabic (formal and Gulf dialect) and
English messages, smart template choice, portal or PDF link, chatter log.
""",
    "version": "17.0.1.0.0",
    "category": "Productivity/Discuss",
    "author": "Racil Oasis Trading Co. (واحة رسيل)",
    "maintainer": "Racil Oasis Trading Co.",
    "website": "https://wahatraseel.com",
    "support": "info@wahatraseel.com",
    "license": "LGPL-3",
    "depends": ["mail"],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_config_parameter_data.xml",
        "data/racil_wa_document_data.xml",
        "data/racil_wa_template_data.xml",
        "wizard/racil_wa_composer_views.xml",
        "views/racil_wa_template_views.xml",
        "views/res_config_settings_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "racil_whatsapp/static/src/scss/racil_wa.scss",
        ],
    },
    "images": ["static/description/banner.png"],
    "application": False,
    "installable": True,
}
