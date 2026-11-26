"""The body of every Testifield webhook, as the Jinja template Frappe renders
for each event. Every value goes in through `tojson`, never inside a quoted
string, so a name, a modified time or a tf_ref holding a quote, a backslash or
a newline still gives valid JSON (a body that does not parse is refused by
Testifield, which would then never learn of the submit or the cancel). No
frappe import, so it can be rendered and tested on its own."""
import json

FIELDS = ("doctype", "name", "modified", "docstatus", "tf_ref")


def body_template(event):
    """The webhook_json for one event: doctype, name, event, modified,
    docstatus, tf_ref and the whole document, each a JSON value."""
    parts = [f'"event": {json.dumps(event)}']
    # a field the document does not carry is null, not a render error
    parts += [f'"{f}": {{{{ doc.{f} | default(none) | tojson }}}}' for f in FIELDS]
    parts.append('"doc": {{ doc | tojson }}')
    return "{" + ", ".join(parts) + "}"
