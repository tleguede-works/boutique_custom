// Charge via doctype_list_js après item_list.js (ERPNext) — ne pas écraser listview_settings.
(function () {
	const settings = frappe.listview_settings.Item || {};

	const previous_onload = settings.onload;
	settings.onload = function (listview) {
		if (previous_onload) {
			previous_onload(listview);
		}

		listview.page.add_button(
			__("Etiquettes grille PDF"),
			() => {
				const checked = listview.get_checked_items(true);
				if (!checked.length) {
					frappe.msgprint({
						title: __("Etiquettes"),
						message: __(
							"Cochez une ou plusieurs variantes (articles sans « A des variantes »)."
						),
						indicator: "orange",
					});
					return;
				}
				const items = checked.map((row) => row.name);
				frappe.call({
					method: "boutique_custom.print.item_label_sheet.download",
					args: { items, columns: 3 },
					freeze: true,
					freeze_message: __("Génération du PDF…"),
				});
			},
			{ btn_class: "btn-primary" }
		);
	};

	frappe.listview_settings.Item = settings;
})();
