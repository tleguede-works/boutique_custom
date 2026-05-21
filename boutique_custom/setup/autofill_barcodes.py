"""Backfill barcodes on existing variants that have none."""

from __future__ import annotations

import frappe

from boutique_custom.item_autofill import _has_barcode, autofill_barcode


def run(dry_run: bool = False) -> dict:
	frappe.only_for("System Manager")

	updated = skipped = 0
	for name in frappe.get_all("Item", filters={"has_variants": 0}, pluck="name"):
		doc = frappe.get_doc("Item", name)
		if doc.get("has_variants") or _has_barcode(doc):
			skipped += 1
			continue
		before = len(doc.get("barcodes") or [])
		autofill_barcode(doc)
		if len(doc.get("barcodes") or []) <= before:
			skipped += 1
			continue
		if dry_run:
			updated += 1
			continue
		doc.save(ignore_permissions=True)
		updated += 1

	if not dry_run:
		frappe.db.commit()

	return {"updated": updated, "skipped": skipped, "dry_run": dry_run}
