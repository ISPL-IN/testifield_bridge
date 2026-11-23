import json

import frappe
from frappe.utils.password import get_decrypted_password

from testifield_bridge.api import TF_DOCTYPES

WEBHOOK_EVENTS = ["after_insert", "on_submit", "on_cancel", "on_update_after_submit"]

# The least roles the posting map needs. Nothing about HR, nothing about
# system settings; the accountant and payroll use their own accounts.
INTEGRATION_ROLES = [
    "Projects User", "Stock User", "Purchase User", "Accounts User", "Sales User", "Item Manager",
]


def after_install():
    # Only the fields: Frappe will not save a webhook without a request URL,
    # so the webhooks are made by point_webhooks (site-setup.sh) once the
    # instance's address and secret are known.
    ensure_custom_fields()


def after_migrate():
    ensure_custom_fields()
    ensure_webhooks()  # re-applies the shape of webhooks that already exist


# where the two fields sit on each form: after the first field every form has
INSERT_AFTER = {"Project": "project_name", "Warehouse": "warehouse_name", "Cost Center": "cost_center_name"}


def ensure_custom_fields():
    """tf_ref and tf_user on every doctype the posting map writes. Idempotent."""
    from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

    fields = {}
    for dt in TF_DOCTYPES:
        fields[dt] = [
            {
                "fieldname": "tf_ref", "label": "Testifield ref", "fieldtype": "Data", "length": 140,
                "insert_after": INSERT_AFTER.get(dt, "naming_series"),
                "read_only": 1, "allow_on_submit": 0, "in_standard_filter": 1, "search_index": 1, "no_copy": 1,
                "description": "Idempotency key from Testifield; the same event never makes two documents",
            },
            {
                "fieldname": "tf_user", "label": "Testifield user", "fieldtype": "Data", "length": 140,
                "insert_after": "tf_ref", "read_only": 1, "no_copy": 1,
                "description": "Who in Testifield caused this posting",
            },
        ]
    create_custom_fields(fields, ignore_validate=True, update=True)
    frappe.db.commit()


def ensure_webhooks(url=None, secret=None):
    """One webhook per doctype per event, named 'TF <Doctype> <event>'. The
    URL and the secret come from point_webhooks; without a URL only webhooks
    that already exist are re-shaped (Frappe refuses one with no URL)."""
    for dt in TF_DOCTYPES:
        for ev in WEBHOOK_EVENTS:
            name = f"TF {dt} {ev}"
            if frappe.db.exists("Webhook", name):
                wh = frappe.get_doc("Webhook", name)
            elif url:
                wh = frappe.new_doc("Webhook")
                wh.name = name
                wh.flags.name_set = True  # keep our name, not the doctype's autoname
            else:
                continue
            wh.webhook_doctype = dt
            wh.webhook_docevent = ev
            wh.request_method = "POST"
            wh.request_structure = "JSON"
            wh.webhook_json = json.dumps({
                "doctype": "{{ doc.doctype }}", "name": "{{ doc.name }}", "event": ev,
                "modified": "{{ doc.modified }}", "docstatus": "{{ doc.docstatus }}", "tf_ref": "{{ doc.tf_ref }}",
                "doc": "{{ doc.as_json() }}",
            })
            wh.set("webhook_headers", [])
            wh.append("webhook_headers", {"key": "Content-Type", "value": "application/json"})
            wh.enable_security = 1
            if url is not None:
                wh.request_url = url
            if secret is not None:
                wh.webhook_secret = secret
            wh.enabled = 1 if (wh.request_url and (secret or wh.get_password("webhook_secret", raise_exception=False))) else 0
            wh.flags.ignore_permissions = True
            wh.save()
    frappe.db.commit()


def point_webhooks(url, secret):
    """Where the webhooks go and what they are signed with. Run at install
    and whenever the Testifield instance's address or secret changes."""
    ensure_webhooks(url=url, secret=secret)
    n = frappe.db.count("Webhook", {"name": ["like", "TF %"], "enabled": 1})
    return {"enabled": n, "url": url}


def make_integration_user(email="testifield@localhost", full_name="Testifield", regenerate=False):
    """The one user Testifield's server signs in as. Returns the API key and
    secret ONCE; keep them in the server's environment, never in a database."""
    if frappe.db.exists("User", email):
        user = frappe.get_doc("User", email)
    else:
        user = frappe.new_doc("User")
        user.email = email
        user.first_name = full_name
        user.user_type = "System User"
        user.send_welcome_email = 0
        user.enabled = 1
    user.set("roles", [])
    for r in INTEGRATION_ROLES:
        if frappe.db.exists("Role", r):
            user.append("roles", {"role": r})
    if not user.api_key or regenerate:
        user.api_key = frappe.generate_hash(length=15)
        user.api_secret = frappe.generate_hash(length=15)
    user.flags.ignore_permissions = True
    user.save()
    frappe.db.commit()
    secret = get_decrypted_password("User", user.name, "api_secret", raise_exception=False)
    return {"user": user.name, "api_key": user.api_key, "api_secret": secret, "roles": INTEGRATION_ROLES}


def make_sandbox_fixtures(company="INOV IT Solutions Pvt Ltd", abbr="ISPL"):
    """A sandbox's minimum: a company, a free-issue supplier, a serialised
    LED item, a site warehouse, a project cost centre. Idempotent."""
    out = {}
    if not frappe.db.exists("Company", company):
        c = frappe.new_doc("Company")
        c.company_name = company
        c.abbr = abbr
        c.default_currency = "INR"
        c.country = "India"
        c.chart_of_accounts = "Standard"
        c.flags.ignore_permissions = True
        c.insert()
    out["company"] = company
    if not frappe.db.exists("Supplier", "PWD (free issue)"):
        s = frappe.new_doc("Supplier")
        s.supplier_name = "PWD (free issue)"
        s.supplier_group = frappe.db.get_value("Supplier Group", {"is_group": 0}, "name") or "All Supplier Groups"
        s.flags.ignore_permissions = True
        s.insert()
    out["supplier"] = "PWD (free issue)"
    if not frappe.db.exists("Item", "LED-120W"):
        i = frappe.new_doc("Item")
        i.item_code = "LED-120W"
        i.item_name = "LED fitting 120 W"
        i.item_group = frappe.db.get_value("Item Group", {"is_group": 0}, "name") or "All Item Groups"
        i.stock_uom = "Nos"
        i.is_stock_item = 1
        i.has_serial_no = 1
        i.serial_no_series = "LED120-.#####"
        i.flags.ignore_permissions = True
        i.insert()
    out["item"] = "LED-120W"
    wh = f"Delhi store - {abbr}"
    if not frappe.db.exists("Warehouse", wh):
        w = frappe.new_doc("Warehouse")
        w.warehouse_name = "Delhi store"
        w.company = company
        w.flags.ignore_permissions = True
        w.insert()
    out["warehouse"] = wh
    cc = f"PWD-SSL - {abbr}"
    if not frappe.db.exists("Cost Center", cc):
        c = frappe.new_doc("Cost Center")
        c.cost_center_name = "PWD-SSL"
        c.company = company
        c.parent_cost_center = frappe.db.get_value("Cost Center", {"company": company, "is_group": 1}, "name")
        c.flags.ignore_permissions = True
        c.insert()
    out["cost_center"] = cc
    frappe.db.commit()
    return out
