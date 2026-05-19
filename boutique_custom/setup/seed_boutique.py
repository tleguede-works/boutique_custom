"""Idempotent retail boutique seed for ERPNext (post setup wizard)."""

from __future__ import annotations

import frappe
from frappe import _

# French SYSCOHADA-style account name hints (suffix varies by company abbr)
FR_STOCK_ACCOUNT_HINTS = {
	"Stock": ["Marchandises A1", "Marchandises", "3111"],
	"Stock Adjustment": ["Variations des stocks de marchandises", "6031"],
	"Cost of Goods Sold": ["Achats de marchandises", "601"],
}

SYSCOHADA_ACCOUNT_TYPES = {
	"Stock": "Stock",
	"Stock Adjustment": "Stock Adjustment",
	"Cost of Goods Sold": "Cost of Goods Sold",
}


def run(
	company: str | None = None,
	warehouse: str = "Boutique",
	with_catalog: bool = False,
	dry_run: bool = False,
	force: bool = False,
):
	"""Entry point for bench execute."""
	frappe.only_for("System Manager")
	company = company or frappe.db.get_single_value("Global Defaults", "default_company")
	if not company:
		frappe.throw(_("No default company. Complete the ERPNext setup wizard first."))

	if not frappe.db.get_single_value("System Settings", "setup_complete"):
		frappe.throw(_("Setup wizard is not complete (setup_complete = 0)."))

	logs: list[str] = []

	def log(msg: str):
		logs.append(msg)
		frappe.logger("boutique_custom").info(msg)

	def apply():
		_set_language_fr(log, force)
		_fix_company_stock_accounts(company, log, force)
		wh = _ensure_warehouse(company, warehouse, log, force)
		_ensure_walk_in_customer(company, log)
		_ensure_payment_modes(company, log, force)
		_ensure_pos_profile(company, wh, warehouse, log, force)
		if with_catalog:
			_seed_catalog(company, wh, log, force)
		frappe.db.commit()
		frappe.clear_cache()

	if dry_run:
		log(f"[dry-run] company={company} warehouse={warehouse} with_catalog={with_catalog}")
		return {"dry_run": True, "logs": logs}

	apply()
	return {"ok": True, "company": company, "warehouse": warehouse, "logs": logs}


def _set_language_fr(log, force: bool):
	if frappe.db.get_single_value("System Settings", "language") == "fr" and not force:
		log("skip: System Settings.language already fr")
		return
	if not frappe.db.exists("Language", "fr"):
		frappe.get_doc({"doctype": "Language", "language_code": "fr", "enabled": 1}).insert(
			ignore_permissions=True
		)
		log("created: Language fr")
	frappe.db.set_single_value("System Settings", "language", "fr")
	log("set: System Settings.language = fr")


def _fix_company_stock_accounts(company: str, log, force: bool):
	company_doc = frappe.get_doc("Company", company)
	_tag_syscohada_accounts(company, log)
	if not force and company_doc.default_inventory_account:
		log("skip: Company stock accounts already set")
		return
	# Company.validate() normally sets this; required when calling set_default_accounts via bench execute
	company_doc.update_default_account = True
	company_doc.set_default_accounts()
	company_doc.save(ignore_permissions=True)
	if company_doc.default_inventory_account:
		log(f"set: Company.default_inventory_account = {company_doc.default_inventory_account}")
	else:
		inv = _find_account_by_type(company, "Stock")
		if inv:
			company_doc.db_set("default_inventory_account", inv)
			log(f"set: Company.default_inventory_account = {inv} (manual)")


def _tag_syscohada_accounts(company: str, log):
	for account_type, hints in FR_STOCK_ACCOUNT_HINTS.items():
		if frappe.db.exists(
			"Account",
			{"company": company, "account_type": account_type, "is_group": 0},
		):
			continue
		for hint in hints:
			name = frappe.db.get_value(
				"Account",
				{
					"company": company,
					"is_group": 0,
					"name": ["like", f"%{hint}%"],
				},
				"name",
			)
			if name:
				frappe.db.set_value("Account", name, "account_type", account_type, update_modified=False)
				log(f"tagged: {name} -> {account_type}")
				break


def _find_account_by_type(company: str, account_type: str) -> str | None:
	return frappe.db.get_value(
		"Account",
		{"company": company, "account_type": account_type, "is_group": 0},
		"name",
	)


def _ensure_warehouse(company: str, warehouse_name: str, log, force: bool) -> str:
	parent = frappe.db.get_value(
		"Warehouse",
		{"company": company, "is_group": 1, "parent_warehouse": ["is", "not set"]},
		"name",
	)
	if not parent:
		parent = frappe.db.get_value(
			"Warehouse", {"company": company, "is_group": 1}, "name", order_by="lft asc"
		)
	inv_account = frappe.db.get_value("Company", company, "default_inventory_account")
	existing = frappe.db.get_value("Warehouse", warehouse_name, "name")
	if existing and not force:
		log(f"skip: Warehouse {warehouse_name}")
		return existing

	if existing:
		doc = frappe.get_doc("Warehouse", existing)
	else:
		doc = frappe.new_doc("Warehouse")
		doc.warehouse_name = warehouse_name
		doc.company = company
	if parent:
		doc.parent_warehouse = parent
	doc.is_group = 0
	if inv_account:
		doc.account = inv_account
	if existing:
		doc.save(ignore_permissions=True)
		log(f"updated: Warehouse {doc.name}")
	else:
		doc.insert(ignore_permissions=True)
		log(f"created: Warehouse {doc.name}")
	return doc.name


def _ensure_walk_in_customer(company: str, log):
	name = frappe.db.get_value("Customer", {"customer_name": "Walk-in Customer"}, "name")
	if name:
		log("skip: Walk-in Customer")
		return name
	doc = frappe.get_doc(
		{
			"doctype": "Customer",
			"customer_name": "Walk-in Customer",
			"customer_type": "Individual",
			"customer_group": frappe.db.get_value("Customer Group", {"is_group": 0}, "name")
			or "Individual",
			"territory": frappe.db.get_value("Territory", {"is_group": 0}, "name") or "All Territories",
		}
	)
	doc.insert(ignore_permissions=True)
	log(f"created: Customer {doc.name}")
	return doc.name


def _ensure_payment_modes(company: str, log, force: bool):
	modes = [
		("Cash", "Espèces", "Cash"),
		("Bank", "Carte", "Bank"),
	]
	for mop_type, label, acc_type in modes:
		if frappe.db.exists("Mode of Payment", label) and not force:
			log(f"skip: Mode of Payment {label}")
			continue
		account = _find_account_by_type(company, mop_type)
		if not account and mop_type == "Cash":
			account = frappe.db.get_value(
				"Account",
				{
					"company": company,
					"is_group": 0,
					"name": ["like", "%Caisse en monnaie nationale%"],
				},
				"name",
			)
			if account:
				frappe.db.set_value("Account", account, "account_type", "Cash", update_modified=False)
		if not account and mop_type == "Bank":
			account = frappe.db.get_value(
				"Account",
				{"company": company, "account_type": "Bank", "is_group": 0},
				"name",
			)
		if not account:
			account = _first_leaf_account(company, "Asset" if mop_type == "Cash" else "Asset")
		if frappe.db.exists("Mode of Payment", label):
			doc = frappe.get_doc("Mode of Payment", label)
		else:
			doc = frappe.new_doc("Mode of Payment")
			doc.mode_of_payment = label
			doc.type = mop_type
		if account:
			exists = [r.account for r in doc.accounts if r.company == company]
			if company not in [r.company for r in doc.accounts] or force:
				doc.set("accounts", [r for r in doc.accounts if r.company != company])
				doc.append("accounts", {"company": company, "default_account": account})
		doc.enabled = 1
		if doc.get("name"):
			doc.save(ignore_permissions=True)
			log(f"updated: Mode of Payment {label}")
		else:
			doc.insert(ignore_permissions=True)
			log(f"created: Mode of Payment {label}")


def _first_leaf_account(company: str, root_type: str) -> str | None:
	return frappe.db.get_value(
		"Account",
		{"company": company, "root_type": root_type, "is_group": 0},
		"name",
		order_by="name asc",
	)


def _default_cost_center(company: str) -> str | None:
	return frappe.db.get_value("Company", company, "cost_center") or frappe.db.get_value(
		"Cost Center", {"company": company, "is_group": 0}, "name"
	)


def _default_write_off_account(company: str) -> str | None:
	for field in ("write_off_account", "stock_adjustment_account", "default_expense_account"):
		account = frappe.db.get_value("Company", company, field)
		if account:
			return account
	for hint in ("6031", "6015", "Charges", "Frais"):
		account = frappe.db.get_value(
			"Account",
			{"company": company, "is_group": 0, "name": ["like", f"%{hint}%"]},
			"name",
		)
		if account:
			return account
	return None


def _ensure_pos_profile(company: str, warehouse: str, profile_name: str, log, force: bool):
	if frappe.db.exists("POS Profile", profile_name) and not force:
		log(f"skip: POS Profile {profile_name}")
		return profile_name

	walk_in = frappe.db.get_value("Customer", {"customer_name": "Walk-in Customer"}, "name")
	price_list = (
		frappe.db.get_value("Price List", {"selling": 1, "enabled": 1}, "name")
		or "Standard Selling"
	)
	write_off_account = _default_write_off_account(company)
	write_off_cost_center = _default_cost_center(company)
	if not write_off_account or not write_off_cost_center:
		frappe.throw(
			_("POS Profile requires write-off account and cost center. Check Company defaults.")
		)

	if frappe.db.exists("POS Profile", profile_name):
		doc = frappe.get_doc("POS Profile", profile_name)
	else:
		doc = frappe.new_doc("POS Profile")
		doc.name = profile_name
		doc.company = company
		doc.warehouse = warehouse
		doc.currency = frappe.db.get_value("Company", company, "default_currency") or "EUR"
		doc.customer = walk_in
		doc.selling_price_list = price_list
		doc.update_stock = 1

	doc.company = company
	doc.warehouse = warehouse
	doc.write_off_account = write_off_account
	doc.write_off_cost_center = write_off_cost_center
	if walk_in:
		doc.customer = walk_in
	doc.payments = []
	for label in ("Espèces", "Carte"):
		if frappe.db.exists("Mode of Payment", label):
			doc.append("payments", {"mode_of_payment": label, "default": 1 if label == "Espèces" else 0})

	if doc.get("name"):
		doc.save(ignore_permissions=True)
		log(f"updated: POS Profile {profile_name}")
	else:
		doc.insert(ignore_permissions=True)
		log(f"created: POS Profile {profile_name}")
	return profile_name


def _seed_catalog(company: str, warehouse: str, log, force: bool):
	_ensure_item_group("Vêtements", None, log, force)
	_ensure_item_group("Robes", "Vêtements", log, force)
	_ensure_item_attribute("Taille", ["S", "M", "L"], log, force)
	_ensure_item_attribute("Couleur", ["Noir", "Blanc"], log, force)
	template_code = "ROB-ALBA"
	if frappe.db.exists("Item", template_code) and not force:
		log(f"skip: Item template {template_code}")
	else:
		if frappe.db.exists("Item", template_code):
			frappe.delete_doc("Item", template_code, force=1)
		tmpl = frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": template_code,
				"item_name": "Robe Alba",
				"item_group": "Robes",
				"stock_uom": "Nos",
				"has_variants": 1,
				"attributes": [
					{"attribute": "Taille"},
					{"attribute": "Couleur"},
				],
			}
		)
		tmpl.insert(ignore_permissions=True)
		log(f"created: Item template {template_code}")
		from erpnext.controllers.item_variant import create_variant

		for size in ("S", "M"):
			for color in ("Noir",):
				variant = create_variant(template_code, {"Taille": size, "Couleur": color})
				variant.standard_rate = 49.0
				variant.save(ignore_permissions=True)
				log(f"created: variant {variant.item_code}")

	_stock_entry(company, warehouse, log)


def _ensure_item_group(name: str, parent: str | None, log, force: bool):
	if frappe.db.exists("Item Group", name) and not force:
		log(f"skip: Item Group {name}")
		return
	if frappe.db.exists("Item Group", name):
		return
	is_group = 1 if name == "Vêtements" else 0
	doc = frappe.get_doc(
		{
			"doctype": "Item Group",
			"item_group_name": name,
			"parent_item_group": parent or "All Item Groups",
			"is_group": is_group,
		}
	)
	doc.insert(ignore_permissions=True)
	log(f"created: Item Group {name}")


def _abbr_for_attribute_value(value: str) -> str:
	"""ERPNext 16 requires abbr on each Item Attribute Value row."""
	v = value.strip()
	if len(v) <= 4:
		return v
	return v[:3].upper()


def _ensure_item_attribute(name: str, values: list[str], log, force: bool):
	if frappe.db.exists("Item Attribute", name) and not force:
		log(f"skip: Item Attribute {name}")
		return
	if frappe.db.exists("Item Attribute", name):
		if not force:
			return
		frappe.delete_doc("Item Attribute", name, force=1)
	doc = frappe.get_doc(
		{
			"doctype": "Item Attribute",
			"attribute_name": name,
			"item_attribute_values": [
				{"attribute_value": v, "abbr": _abbr_for_attribute_value(v)} for v in values
			],
		}
	)
	doc.insert(ignore_permissions=True)
	log(f"created: Item Attribute {name}")


def _stock_entry(company: str, warehouse: str, log):
	items = frappe.get_all(
		"Item",
		filters={"variant_of": "ROB-ALBA", "disabled": 0},
		pluck="name",
		limit=5,
	)
	if not items:
		return
	se = frappe.get_doc(
		{
			"doctype": "Stock Entry",
			"stock_entry_type": "Material Receipt",
			"company": company,
			"items": [
				{
					"item_code": item,
					"qty": 5,
					"t_warehouse": warehouse,
					"basic_rate": 25,
				}
				for item in items
			],
		}
	)
	se.insert(ignore_permissions=True)
	se.submit()
	log(f"submitted: Stock Entry {se.name}")
