# testifield_bridge

A small Frappe app installed on the ERPNext site that is a Testifield
instance's finance core (ADR-003). It is deliberately thin — ERPNext stays
unmodified; everything here is fixtures and a few whitelisted helpers:

- **Custom fields** `tf_ref` (the idempotency key Testifield stores on every
  document it creates, indexed, shown in the standard filter) and `tf_user`
  (who in Testifield caused the posting) on Project, Stock Entry, Purchase
  Receipt, Purchase Invoice, Sales Invoice, Journal Entry, Payment Entry,
  Warehouse and Cost Center.
- **Webhooks** on those doctypes (after insert, on submit, on cancel, on
  update after submit), posting a JSON body to Testifield and signing it with
  the shared secret (`X-Frappe-Webhook-Signature`, base64 HMAC-SHA256). The
  URL and the secret are set at install by `setup.point_webhooks`, never
  kept in the fixtures.
- **An integration user** with the least roles Testifield's posting map
  needs (`setup.make_integration_user`), whose API key and secret Testifield
  keeps in its server environment.
- `api.ping` and `api.find_by_tf_ref`, whitelisted, for the test exchange.
- `setup.make_sandbox_fixtures` for a sandbox: a company, a supplier, an
  item, a warehouse, a cost centre.

## Install (on a bench)

```
bench get-app /path/to/testifield_bridge          # or the public repository, once published
bench --site <site> install-app testifield_bridge
bench --site <site> execute testifield_bridge.setup.make_integration_user --kwargs '{"email": "testifield@erp.internal"}'
bench --site <site> execute testifield_bridge.setup.point_webhooks --kwargs '{"url": "https://<instance>/api/finance/webhook", "secret": "<shared secret>"}'
```

`ops/erpnext/site-setup.sh` runs these for the Docker sandbox.

Licence: GPL-3.0 (see license.txt). Trademark: this app is not ERPNext and
does not use the Frappe or ERPNext marks in its own name or branding.
