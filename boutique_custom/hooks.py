app_name = "boutique_custom"
app_title = "Boutique Custom"
app_publisher = "Your Name"
app_description = "Low-code ERPNext customizations for a clothing retail MVP"
app_email = "you@example.com"
app_license = "MIT"

app_include_js = "/assets/boutique_custom/js/item_list_labels.js"

doc_events = {
	"Item": {
		"before_save": "boutique_custom.item_autofill.autofill_barcode",
	},
}

fixtures = [
    {
        "dt": "Custom Field",
        "filters": [
            [
                "name",
                "in",
                [
                    "Item-saison",
                    "Item-collection",
                ],
            ]
        ],
    },
    {
        "dt": "Print Format",
        "filters": [
            [
                "name",
                "in",
                [
                    "Boutique POS Ticket",
                    "Boutique Item Label",
                ],
            ]
        ],
    },
    {
        "dt": "Report",
        "filters": [
            [
                "name",
                "in",
                [
                    "Boutique Stock Bas",
                    "Boutique Ventes Du Jour",
                    "Boutique Ventes Par Article",
                    "Boutique Ventes Par Paiement",
                    "Boutique Stock Par Variante",
                ],
            ]
        ],
    },
    {
        "dt": "Translation",
        "filters": [["language", "=", "fr"]],
    },
]
