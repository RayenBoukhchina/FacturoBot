from jinja2 import Environment, FileSystemLoader
from xhtml2pdf import pisa
import os

# Configuration de Jinja2
env = Environment(loader=FileSystemLoader('.'))
template = env.get_template("Invoice Generator/templates/template.html")

# Données de test
data = {
    "facture_numero": "FAC-2023-001",
    "date_emission": "25/11/2023",
    "fournisseur_nom": "TECH SOLUTIONS SARL",
    "fournisseur_adresse": "123 Rue des Entrepreneurs, Tunis",
    "fournisseur_matricule": "MF12345678",
    "client_nom": "CLIENT PRO",
    "client_adresse": "456 Avenue Habib Bourguiba, Sfax",
    "client_matricule": "MF87654321",
    "produits": [
        {"nom": "Ordinateur Portable", "prix_ht": 1500, "quantite": 2},
        {"nom": "Souris Sans Fil", "prix_ht": 35, "quantite": 5},
        {"nom": "Clavier Mécanique", "prix_ht": 120, "quantite": 3}
    ]
}

# Calculs automatiques
data["total_ht"] = sum(p["prix_ht"] * p["quantite"] for p in data["produits"])
data["tva"] = round(data["total_ht"] * 0.19, 3)
data["total_ttc"] = round(data["total_ht"] * 1.19 + 1, 3)

# Génération du PDF
html_out = template.render(data)

with open("Invoice Generator/factures/facture_test.pdf", "wb") as f:
    pisa.CreatePDF(html_out, dest=f)
print("Facture générée avec succès: facture_test.pdf")