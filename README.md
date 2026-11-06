# زر واتساب رسيل | Racil WhatsApp Button — Odoo 17 / 18 / 19

وحدة أودو **مجانية للأبد** تضيف زر «واتساب» إلى الفواتير وعروض الأسعار وأوامر البيع والشراء والتسليمات وجهات الاتصال،
تعمل مع أرقام كل دول العالم (أكثر من ٢٤٠ دولة ومنطقة). **بدون WhatsApp Business API، بدون حساب Meta، بدون اشتراك شهري.**

A **free-forever** Odoo module that adds a WhatsApp button to invoices, quotations, sales/purchase orders, deliveries and contacts —
for customers in any country (240+ countries and territories). **No WhatsApp Business API, no Meta account, no monthly fee.**

## المزايا | Features
- **تنسيق الأرقام تلقائيًا لكل الدول**: `05XXXXXXXX`، `+966 05…`، `00971…`، الأرقام الهندية `٠٥٥…`، المسافات والشرطات والأقواس. يدعم أكثر من ٢٤٠ دولة ومنطقة (بيانات libphonenumber مدمجة)، دون أي مكتبة خارجية.
- **٣٣ رسالة جاهزة** بالفصحى واللهجة الخليجية والإنجليزية: الفاتورة جاهزة، تذكير سداد، شكر بعد السداد، إشعار دائن، عرض سعر، تأكيد طلب، أمر شراء، الشحنة في الطريق، استلام البضاعة، تحية لجهة اتصال.
- **اختيار ذكي للقالب**: الفاتورة المتأخرة تحصل على تذكير، والمسددة على شكر، وجهة الاتصال بالإنجليزية تحصل على الإنجليزي.
- **رابط بوابة العميل أو PDF مباشر** مع رمز وصول آمن.
- **معاينة بشكل فقاعة واتساب** مع تنسيق `*عريض*` `_مائل_` `~مشطوب~`.
- **يعمل مع أي نموذج** (حتى المخصص) من الإعدادات دون برمجة، والزر يُحقن وقت عرض الواجهة، فلا يترك أثرًا عند إلغاء التثبيت.
- **تسجيل كل رسالة في سجل المستند** (قابل للإيقاف).
- الاعتمادية الوحيدة: `mail` (المناقشة). متوافق مع Community وEnterprise وOdoo.sh.

## الفروع | Branches
| الفرع | إصدار أودو |
|---|---|
| `17.0` | Odoo 17 |
| `18.0` | Odoo 18 |
| `19.0` | Odoo 19 ← هذا الفرع |

## التثبيت | Installation
1. انسخ مجلد `racil_whatsapp` من فرع إصدارك إلى مسار الإضافات (على Odoo.sh: أضف المستودع كـ submodule أو ادفع المجلد إلى مستودعك).
2. حدّث قائمة التطبيقات وثبّت **Racil WhatsApp Button**.
3. الإعدادات ← زر واتساب: الدولة الافتراضية، لغة الرسائل، نوع الرابط، المستندات المفعّلة.

## المتغيرات | Placeholders
`{partner} {company} {doc} {amount} {residual} {due_date} {date} {link} {user}`
أو بالعربية: `{العميل} {الشركة} {المستند} {المبلغ} {المتبقي} {الاستحقاق} {التاريخ} {الرابط} {الموظف}`

## الاختبارات | Tests
```
odoo-bin -d test -i racil_whatsapp,sale_management,purchase,stock,crm --test-tags=racil_wa --stop-after-init
```
تمر كل الاختبارات (١٦ اختبارًا) على أودو 17 و18 و19.

---
WhatsApp is a trademark of WhatsApp LLC. This module is not affiliated with or endorsed by WhatsApp or Meta; it only opens the public click-to-chat link (`wa.me`).

Publisher: Racil Oasis Trading Co. (واحة رسيل) — https://wahatraseel.com — info@wahatraseel.com — License: LGPL-3
