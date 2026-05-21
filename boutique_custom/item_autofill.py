"""Auto-fill Item barcodes from SKU (item code); manual values are kept."""

from __future__ import annotations

import re

import frappe

# Vide = pas de validation CODE-39/EAN (SKU boutique : tirets, minuscules couleur, etc.)
# Le scan POS utilise la valeur du code-barres ; le type peut etre renseigne a la main.
DEFAULT_BARCODE_TYPE = ""


def _item_code(doc) -> str:
	return (doc.item_code or doc.name or "").strip()


def _has_barcode(doc) -> bool:
	return any((row.barcode or "").strip() for row in doc.get("barcodes") or [])


def code39_compatible(code: str) -> str:
	"""Uppercase + caracteres CODE-39 courants (optionnel pour etiquettes imprimees)."""
	return re.sub(r"[^0-9A-Z\-.$/+% ]", "", code.upper())


def autofill_barcode(doc, method=None) -> None:
	"""Add one barcode row when none exists (variants only, not template parents)."""
	if doc.get("has_variants"):
		return

	code = _item_code(doc)
	if not code:
		return

	if _has_barcode(doc):
		return

	row = {"barcode": code}
	if DEFAULT_BARCODE_TYPE:
		row["barcode_type"] = DEFAULT_BARCODE_TYPE
	doc.append("barcodes", row)
