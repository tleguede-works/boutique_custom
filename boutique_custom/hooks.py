app_name = "boutique_custom"
app_title = "Boutique Custom"
app_publisher = "tleguede-works"
app_description = "Low-code ERPNext customizations for a clothing retail MVP"
app_email = "you@example.com"
app_license = "MIT"

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
]
