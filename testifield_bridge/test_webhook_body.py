"""The webhook body renders to valid JSON whatever the document's name,
modified time or tf_ref holds. Rendered with Jinja's sandbox, as Frappe
renders webhook_json; needs only jinja2 (no site):

    python3 -m unittest testifield_bridge.test_webhook_body
"""
import json
import unittest

from jinja2.sandbox import SandboxedEnvironment

from testifield_bridge.webhook_body import body_template

ENV = SandboxedEnvironment()


def render(event, doc):
    return ENV.from_string(body_template(event)).render(doc=doc)


class WebhookBody(unittest.TestCase):
    def test_hostile_values_stay_valid_json_and_unchanged(self):
        doc = {
            "doctype": "Purchase Receipt",
            "name": 'MAT-PRE-"1"\\x\nend',
            "modified": "2026-11-26 10:00:00.123456",
            "docstatus": 1,
            "tf_ref": 'tf:rcpt:"quoted"',
            "items": [{"item_code": "LED-120W", "qty": 1}],
        }
        body = json.loads(render("on_submit", doc))
        self.assertEqual(body["event"], "on_submit")
        for field in ("doctype", "name", "modified", "docstatus", "tf_ref"):
            self.assertEqual(body[field], doc[field], field)
        self.assertEqual(body["doc"], doc)

    def test_a_document_without_tf_ref_sends_null_not_the_word_none(self):
        body = json.loads(render("on_update", {"doctype": "Project", "name": "PROJ-0001", "modified": "x", "docstatus": 0}))
        self.assertIsNone(body["tf_ref"])

    def test_html_characters_are_escaped_but_round_trip(self):
        doc = {"doctype": "Journal Entry", "name": "<b>&'", "modified": "m", "docstatus": 2, "tf_ref": "a</script>"}
        text = render("on_cancel", doc)
        self.assertNotIn("</script>", text)
        self.assertEqual(json.loads(text)["tf_ref"], "a</script>")


if __name__ == "__main__":
    unittest.main()
