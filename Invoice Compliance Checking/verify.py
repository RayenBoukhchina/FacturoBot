# verify_invoice_data.py

import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import time
import re

def verify_fiscal_matricule_online(matricule):
    """Vérifie un matricule fiscal via web scraping."""
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')

    service = Service('chromedriver')
    driver = webdriver.Chrome(service=service, options=chrome_options)

    try:
        driver.get('https://www.registre-entreprises.tn/rne-public/#/recherche-pm')
        time.sleep(3)  # Attendre que la page se charge

        input_field = driver.find_element(By.ID, 'mat-input-0')
        input_field.send_keys(matricule)
        input_field.send_keys(Keys.RETURN)
        time.sleep(3) # Attendre les résultats

        page_source = driver.page_source
        # Ici, vous devrez analyser le page_source pour trouver le nom de l'entreprise
        # et d'autres informations pour la validation.
        # Pour cet exemple, nous allons juste vérifier si le matricule est trouvé.
        if "Aucun résultat trouvé" in page_source:
            return False, "Matricule non trouvé en ligne"
        else:
            # Vous pouvez ajouter une logique plus sophistiquée ici pour extraire le nom
            # de l'entreprise et le comparer avec celui de la facture.
            # Par exemple, en utilisant BeautifulSoup pour parser le HTML.
            return True, "Matricule trouvé en ligne"

    except Exception as e:
        print(f"Erreur lors du web scraping: {e}")
        return False, f"Erreur de scraping: {e}"
    finally:
        driver.quit()

def validate_invoice_data(invoice_data_path):
    """Valide les données extraites d'une facture."""
    try:
        df = pd.read_csv(invoice_data_path)
    except FileNotFoundError:
        print(f"Erreur: Le fichier {invoice_data_path} n'a pas été trouvé.")
        return

    results = []

    for index, row in df.iterrows():
        invoice_id = row.get('invoice_number', f'Ligne {index}')
        validation_status = {
            'invoice_id': invoice_id,
            'overall_status': 'SUCCESS',
            'details': []
        }

        # Critères de vérification d'existence
        required_fields = [
            'invoice_number', 'invoice_date', 'vendor_name',
            'vendor_fiscal_matricule', 'vendor_address', 'total_amount'
        ]
        for field in required_fields:
            if pd.isna(row.get(field)) or str(row.get(field)).strip() == '':
                validation_status['overall_status'] = 'FAILED'
                validation_status['details'].append(f"Champ manquant: {field}")

        # Validation du format des montants
        amount_fields = ['total_amount', 'total_ht', 'total_tva'] # Ajoutez d'autres champs de montant si nécessaire
        for field in amount_fields:
            if field in row and not pd.isna(row[field]):
                try:
                    float(str(row[field]).replace(',', '.')) # Gérer les virgules comme séparateur décimal
                except ValueError:
                    validation_status['overall_status'] = 'FAILED'
                    validation_status['details'].append(f"Format de montant invalide pour {field}: {row[field]}")

        # Validation du format de la date (exemple simple, peut être plus robuste)
        if 'invoice_date' in row and not pd.isna(row['invoice_date']):
            if not re.match(r'\d{2}/\d{2}/\d{4}', str(row['invoice_date'])):
                validation_status['overall_status'] = 'FAILED'
                validation_status['details'].append(f"Format de date invalide: {row['invoice_date']}")

        # Validation externe: Web scraping du matricule fiscal
        fiscal_matricule = str(row.get('vendor_fiscal_matricule', '')).strip()
        if fiscal_matricule:
            online_found, online_message = verify_fiscal_matricule_online(fiscal_matricule)
            if not online_found:
                validation_status['overall_status'] = 'FAILED'
                validation_status['details'].append(f"Validation matricule fiscal en ligne: {online_message}")
            else:
                validation_status['details'].append(f"Validation matricule fiscal en ligne: {online_message}")
        else:
            validation_status['details'].append("Matricule fiscal fournisseur manquant pour validation en ligne.")

        results.append(validation_status)

    return results

if __name__ == "__main__":
    input_csv_path = '1_output.csv'
    validation_results = validate_invoice_data(input_csv_path)

    if validation_results:
        for res in validation_results:
            print(f"\nFacture ID: {res['invoice_id']}")
            print(f"Statut Global: {res['overall_status']}")
            if res['details']:
                print("Détails:")
                for detail in res['details']:
                    print(f"  - {detail}")
            else:
                print("  Aucun problème détecté.")
    else:
        print("Aucun résultat de validation à afficher.")


