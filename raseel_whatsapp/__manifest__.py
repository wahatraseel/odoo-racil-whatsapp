# -*- coding: utf-8 -*-
{
    "name": "Raseel WhatsApp | واتساب رسيل — Bulk Sending, Payment Reminders, Free, No API",
    "summary": "WhatsApp button on invoices, quotations, orders, deliveries & contacts, guided bulk sending "
               "from any list, overdue payment reminders, personal templates and statistics — "
               "240+ countries, Arabic & English messages, no Meta API, no subscription. "
               "واتساب مجاني لأودو: زر في كل مستند، إرسال جماعي، تذكير بالمتأخرات، قوالب خاصة وتقارير",
    "description": """
Raseel WhatsApp by Wahat Raseel: send invoices, quotations, orders, purchase orders, deliveries and any
document to customers on WhatsApp in one click, or to many customers with the guided bulk sending.
Overdue payment reminders, personal templates per user and sent-message statistics included.
Free forever: no WhatsApp Business API, no Meta account, no monthly fee. Phone formatting for 240+
countries, ready Arabic (formal and Gulf dialect) and English messages, smart template choice,
portal or PDF link, chatter log.
""",
    "version": "19.0.1.0.0",
    "category": "Productivity/Discuss",
    "author": "Wahat Raseel Trading Company (واحة رسيل)",
    "maintainer": "Wahat Raseel Trading Company",
    "website": "https://wahatraseel.com",
    "support": "info@wahatraseel.com",
    "license": "LGPL-3",
    "depends": ["mail"],
    "data": [
        "security/ir.model.access.csv",
        "security/raseel_wa_security.xml",
        "data/ir_config_parameter_data.xml",
        "data/raseel_wa_document_data.xml",
        "data/raseel_wa_template_data.xml",
        "wizard/raseel_wa_composer_views.xml",
        "wizard/raseel_wa_bulk_views.xml",
        "views/raseel_wa_message_views.xml",
        "views/raseel_wa_template_views.xml",
        "views/res_config_settings_views.xml",
        "data/raseel_wa_cron_data.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "raseel_whatsapp/static/src/scss/raseel_wa.scss",
        ],
    },
    "images": ["static/description/banner.png"],
    "application": False,
    "installable": True,
}
