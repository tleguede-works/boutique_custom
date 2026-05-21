frappe.listview_settings["Item"] = {
	onload(listview) {
		listview.page.add_inner_button(__("Etiquettes grille PDF"), () => {
			const checked = listview.get_checked_items(true);
			if (!checked.length) {
				frappe.msgprint({
					title: __("Etiquettes"),
					message: __("Cochez une ou plusieurs variantes (articles sans « A des variantes »)."),
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
		});
	},
};
