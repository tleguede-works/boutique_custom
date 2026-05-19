"""Import reviewed Translation rows from CSV into the site."""

from __future__ import annotations

import csv
from pathlib import Path

import frappe
from frappe import _


def run(csv_path: str, language: str = "fr"):
	frappe.only_for("System Manager")
	path = Path(csv_path)
	if not path.is_file():
		frappe.throw(_("CSV file not found: {0}").format(csv_path))

	created = updated = skipped = 0
	with path.open(newline="", encoding="utf-8") as f:
		reader = csv.DictReader(f)
		for row in reader:
			source = (row.get("source_text") or row.get("msgid") or "").strip()
			translated = (row.get("translated_text") or row.get("msgstr") or "").strip()
			if not source or not translated:
				skipped += 1
				continue
			existing = frappe.db.get_value(
				"Translation",
				{"language": language, "source_text": source},
				"name",
			)
			if existing:
				frappe.db.set_value("Translation", existing, "translated_text", translated)
				updated += 1
			else:
				frappe.get_doc(
					{
						"doctype": "Translation",
						"language": language,
						"source_text": source,
						"translated_text": translated,
					}
				).insert(ignore_permissions=True)
				created += 1

	frappe.db.commit()
	frappe.clear_cache()
	return {"created": created, "updated": updated, "skipped": skipped}
