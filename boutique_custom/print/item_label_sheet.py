"""PDF grille d'étiquettes articles (image, nom, code-barres CODE128)."""

from __future__ import annotations

import json
from io import BytesIO

import frappe
from frappe import _
from frappe.utils.pdf import get_pdf

from boutique_custom.item_autofill import _has_barcode, _item_code


def _first_barcode_value(doc) -> str:
	for row in doc.get("barcodes") or []:
		val = (row.barcode or "").strip()
		if val:
			return val
	return _item_code(doc)


def _barcode_svg(value: str) -> str:
	try:
		from barcode import Code128
		from barcode.writer import SVGWriter
	except ImportError:
		frappe.throw(_("Install python-barcode in the bench env: bench pip install python-barcode"))

	buffer = BytesIO()
	Code128(value, writer=SVGWriter()).write(buffer)
	return buffer.getvalue().decode("utf-8")


def _item_image_url(doc) -> str:
	if not doc.image:
		return ""
	return frappe.utils.get_url(doc.image)


def _collect_items(item_codes: list[str]) -> list[dict]:
	rows: list[dict] = []
	for code in item_codes:
		code = (code or "").strip()
		if not code or not frappe.db.exists("Item", code):
			continue
		doc = frappe.get_doc("Item", code)
		if doc.get("has_variants"):
			continue
		barcode_value = _first_barcode_value(doc)
		if not barcode_value:
			continue
		rows.append(
			{
				"item_code": doc.item_code or doc.name,
				"item_name": doc.item_name or doc.name,
				"image_url": _item_image_url(doc),
				"barcode_value": barcode_value,
				"barcode_svg": _barcode_svg(barcode_value),
			}
		)
	return rows


@frappe.whitelist()
def download(items=None, columns: int = 3) -> None:
	"""Génère un PDF grille pour les articles sélectionnés (codes variante)."""
	frappe.only_for(("System Manager", "Stock Manager", "Stock User"))

	if isinstance(items, str):
		items = json.loads(items)
	if not items:
		frappe.throw(_("Sélectionnez au moins un article (variante)."))

	try:
		columns = int(columns)
	except (TypeError, ValueError):
		columns = 3
	columns = max(1, min(columns, 5))

	label_rows = _collect_items(list(items))
	if not label_rows:
		frappe.throw(
			_("Aucune variante avec code-barres. Enregistrez les articles ou lancez autofill_barcodes.")
		)

	html = frappe.render_template(
		"templates/print_formats/boutique_item_label_sheet.html",
		{"items": label_rows, "columns": columns},
	)

	pdf = get_pdf(html, options={"page-size": "A4", "margin-top": "10mm", "margin-bottom": "10mm"})

	frappe.local.response.filename = "etiquettes-articles.pdf"
	frappe.local.response.filecontent = pdf
	frappe.local.response.type = "download"
