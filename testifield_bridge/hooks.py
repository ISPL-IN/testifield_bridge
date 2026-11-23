app_name = "testifield_bridge"
app_title = "Testifield Bridge"
app_publisher = "INOV IT Solutions Private Limited"
app_description = "tf_ref and tf_user fields, signed webhooks and an integration user for a Testifield instance's finance core"
app_email = "dev@inovit.in"
app_license = "GPL-3.0"
required_apps = ["erpnext"]

# Everything this app adds to the site is a fixture, exported here, so a
# fresh site gets the same fields and webhooks and a migrate re-applies them.
fixtures = [
    {"dt": "Custom Field", "filters": [["name", "like", "%-tf_%"]]},
    {"dt": "Property Setter", "filters": [["name", "like", "%tf_%"]]},
    {"dt": "Webhook", "filters": [["name", "like", "TF %"]]},
]

after_install = "testifield_bridge.setup.after_install"
after_migrate = "testifield_bridge.setup.after_migrate"
