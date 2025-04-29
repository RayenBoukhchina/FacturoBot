import pandas as pd
from googletrans import Translator
import re

# 1. Traduction des Labels en Français
def translate_labels_to_french(input_csv, output_csv):
    """
    Traduit les labels de labels.csv en français et sauvegarde le résultat.
    """
    translator = Translator()
    df = pd.read_csv(input_csv)
    
    # Dictionnaire de traductions manuelles
    manual_translations = {
        "Seller Address": "Adresse du Vendeur",
        "Seller GSTIN Number": "Numéro GSTIN du Vendeur",
        "Country of Origin": "Pays d'Origine",
        "Currency": "Devise",
        "Description": "Description",
        "Total Invoice amount entered by WH operator": "Montant Total de la Facture (Saisi par l'Opérateur)",
        "Total Invoice Quantity entered by WH operator": "Quantité Totale (Saisie par l'Opérateur)",
        "Total TCS Collected": "Total TCS Collecté",
        "Round Off Charges": "Frais d'Arrondi",
        "PO Number": "Numéro de Commande",
        "Invoice Items Total Amount": "Montant Total des Articles",
        "Invoice Items total quantity": "Quantité Totale des Articles",
        "Buyer GSTIN Number": "Numéro GSTIN de l'Acheteur",
        "Ship to Address": "Adresse de Livraison",
        "S.No": "N°",
        "Product ID": "ID Produit",
        "HSN": "HSN",
        "Title": "Titre",
        "Quantity": "Quantité",
        "Unit Price": "Prix Unitaire",
        "Excise Duty": "Droit d'Accise",
        "Discount Percent": "Pourcentage de Remise",
        "SGST Percent": "Pourcentage SGST",
        "CGST Percent": "Pourcentage CGST",
        "IGST Percent": "Pourcentage IGST",
        "Cess Percent": "Pourcentage de Cess",
        "TCS Percent": "Pourcentage TCS",
        "Total Amount": "Montant Total",
        "APP %": "Pourcentage APP"
    }
    
    df['French_Label'] = df.iloc[:, 0].map(manual_translations)
    df.to_csv(output_csv, index=False)
    print(f"Traduction terminée. Résultats sauvegardés dans {output_csv}")

# 2. Enrichissement des Synonymes avec le Français (version corrigée)
def add_french_synonyms(synonyms_csv):
    """
    Ajoute des synonymes français au fichier original label_synonyms.csv.
    """
    df = pd.read_csv(synonyms_csv, header=None)
    french_synonyms = {
        0: ["Adresse Fournisseur", "Adresse Vendeur", "Adresse du Vendeur"],
        1: ["Numéro GST du Vendeur", "GSTIN Vendeur", "N° GST Vendeur"],
        2: ["Pays d'Origine", "Origine du Produit", "Provenance"],
        3: ["Devise", "Monnaie"],
        4: ["Description", "Détails", "Informations Facture"],
        5: ["Montant Total Facture", "Total Facture", "Somme Totale"],
        6: ["Quantité Totale", "Nombre d'Articles", "Total des Quantités"],
        7: ["TCS Total", "Taxe Collectée", "Total TCS"],
        8: ["Arrondi", "Frais d'Arrondi"],
        9: ["Numéro PO", "N° Commande", "Référence Commande"],
        10: ["Montant Total Articles", "Total des Articles"],
        11: ["Quantité Totale Articles", "Total Quantités"],
        12: ["GSTIN Acheteur", "Numéro GST Acheteur"],
        13: ["Adresse Livraison", "Lieu de Livraison"],
        14: ["Numéro", "N°", "Numéro de Série"],
        15: ["ID Article", "Référence Produit"],
        16: ["Code HSN", "HSN/SAC"],
        17: ["Titre", "Libellé"],
        18: ["Qté", "Nombre"],
        19: ["Prix Unitaire", "Prix de Vente"],
        20: ["Taxe d'Accise"],
        21: ["Remise %", "Pourcentage Remise"],
        22: ["SGST %", "Taux SGST"],
        23: ["CGST %", "Taux CGST"],
        24: ["IGST %", "Taux IGST"],
        25: ["Cess %", "Taux Cess"],
        26: ["TCS %", "Taux TCS"],
        27: ["Montant Total", "Total à Payer"],
        28: ["APP %", "Pourcentage APP"]
    }
    
    for index, synonyms in french_synonyms.items():
        # Trouver la ligne correspondante
        mask = df[0] == index
        if not mask.any():
            continue

        # Récupérer les synonymes existants (non nuls)
        existing = df.loc[mask].iloc[0, 1:].dropna().tolist()

        # Combiner avec les nouveaux synonymes, en supprimant les doublons
        combined = list(dict.fromkeys(existing + synonyms))

        # Vérifier combien de colonnes il faut
        needed_cols = len(combined)

        # Ajouter dynamiquement des colonnes vides si besoin
        if df.shape[1] < needed_cols + 1:  # +1 à cause de la colonne 0 (l'index)
            for _ in range(needed_cols + 1 - df.shape[1]):
                df[df.shape[1]] = None  # Ajoute des colonnes vides

        # Maintenant écrire **cellule par cellule**
        row_idx = df.index[mask][0]  # l'indice de la ligne
        for i, value in enumerate(combined):
            df.iat[row_idx, i + 1] = value  # +1 pour commencer à partir de la colonne 1

    
    # Sauvegarder dans le fichier original
    df.to_csv(synonyms_csv, index=False, header=False)
    print(f"Synonymes français ajoutés au fichier original {synonyms_csv}")

# Exécution du Script
if __name__ == "__main__":
    # 1. Traduire les labels (crée un nouveau fichier)
    translate_labels_to_french(
        "Invoice Extractor/assets/labels.csv", 
        "Invoice Compliance Checking/assets/labels_fr.csv"
    )
    
    # 2. Enrichir le fichier original des synonymes
    add_french_synonyms("Invoice Extractor/assets/label_synonyms.csv")
    
    # 3. Charger les données pour vérification
    labels_fr = pd.read_csv("Invoice Compliance Checking/assets/labels_fr.csv")
    synonyms_fr = pd.read_csv("Invoice Extractor/assets/label_synonyms.csv", header=None)
    
    # Convertir en dictionnaire
    # Convertir en dictionnaire
    synonym_dict = {}
    for _, row in synonyms_fr.iterrows():
        label_index = row[0]
        if label_index >= len(labels_fr):
            print(f"⚠️ Warning: Index {label_index} hors limite pour labels_fr ({len(labels_fr)} lignes). Ignoré.")
            continue

        label_name = labels_fr.iloc[label_index, 0]
        synonym_dict[label_name] = [s for s in row[1:] if pd.notna(s)]

