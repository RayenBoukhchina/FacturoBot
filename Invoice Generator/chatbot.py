import os
import csv
import json
import re
import google.generativeai as genai
from jinja2 import Environment, FileSystemLoader
from xhtml2pdf import pisa
from datetime import datetime

class InvoiceChatbot:

    def __init__(self):
        # Clé API Gemini
        api_key = "CLE_API_GEMINI"
        genai.configure(api_key=api_key)
    
        # Vérification de la clé API
        try:
            models = genai.list_models()
            print("✅ Connexion à l'API réussie")
            print("Modèles disponibles :")
            for model in models:
                print(f" - {model.name}")
        except Exception as e:
            print(f"❌ Erreur de connexion à l'API Gemini: {str(e)}")
        

        # Config dossiers
        self.BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        self.TEMPLATES_DIR = os.path.join(self.BASE_DIR, 'templates')
        self.FACTURES_DIR = os.path.join(self.BASE_DIR, 'factures')
        self.DATA_DIR = os.path.join(self.BASE_DIR, 'data')
        self.CSV_PATH = os.path.join(self.DATA_DIR, 'factures.csv')

        self.env = Environment(loader=FileSystemLoader(self.TEMPLATES_DIR))
        self._setup_directories()

        self.system_prompt = """Tu es un assistant de facturation. Analyse la demande et retourne UNIQUEMENT un JSON valide avec:
        {
            "client": {
                "nom": "str (obligatoire)",
                "adresse": "str (obligatoire)",
                "matricule_fiscal": "str (obligatoire)"
            },
            "produits": [{
                "nom": "str (obligatoire)",
                "prix_ht": "float (obligatoire)",
                "quantite": "int (obligatoire)"
            }]
        }
                RÈGLES IMPORTANTES:
            1. Si le client mentionne un montant "total", calcule le prix unitaire en divisant par la quantité
            2. Si le client dit "X produits à Y DT", Y est le prix unitaire
            3. Si le client dit "X produits pour un total de Z DT", calcule le prix unitaire = Z ÷ X
            4. Le champ "prix_ht" doit TOUJOURS contenir le prix unitaire, jamais le prix total
            5. Si l'information est ambiguë, fais une supposition raisonnable basée sur le contexte
            6. CORRIGE automatiquement les fautes d'orthographe dans les noms de produits:
                    -  "pc", "ordi" → "Ordinateur"
                    - "souri", "suri" → "Souris"
                    - "imprimant", "imprimente" → "Imprimante"
                    - "écrant", "écran plat" → "Écran"
                    - "tel", "téléphon", "téléfone" → "Téléphone"
                    - "formatage" → "Service de formatage"
                    ....
                    - Applique un formatage professionnel aux noms (majuscule au début)
               7.. Normalise les prix: arrondis à 3 décimales maximum
    9. Standardise les unités: "dt", "TD", "dinars" → tout convertir en DT
    10. Si le client mentionne une remise, calcule le prix après remise et indique-le dans un champ "remise" (pourcentage)
    11. Pour les services, ajoute automatiquement "Service de..." au début s'il ne s'agit pas d'un produit physique
            
            Exemples:
            - "9 PCs à 800 DT" → prix_ht = 800 (c'est le prix unitaire)
            - "9 PCs pour 7200 DT au total" → prix_ht = 800 (7200 ÷ 9)
            - "9 PCs, le total est 7200 DT" → prix_ht = 800 (7200 ÷ 9)
            -   2 souri à 15dt" → prix_ht = 15, nom = "Souris"
             - "3 pc pour un total de 2400dt" → prix_ht = 800, nom = "Ordinateur"

             n'oubliee pas  de calculer le prix unitaire et de le mettre dans le champ "prix_ht" et pas le prix total 
        """

    def _setup_directories(self):
        os.makedirs(self.FACTURES_DIR, exist_ok=True)
        os.makedirs(self.DATA_DIR, exist_ok=True)
        
        # Recréer le fichier CSV avec le bon ordre des colonnes
        if not os.path.exists(self.CSV_PATH):
            with open(self.CSV_PATH, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'Référence', 'Date', 'Client', 'Adresse', 'Matricule',
                    'Total HT', 'TVA (19%)', 'Timbre', 'Total TTC', 'Fichier PDF'
                ])
        else:
            # Vérifier l'en-tête du CSV existant
            with open(self.CSV_PATH, 'r', newline='', encoding='utf-8') as f:
                reader = csv.reader(f)
                header = next(reader, None)
                
            if header and (header[3] == 'Matricule' and header[4] == 'Adresse'):
                print("⚠️ L'en-tête du fichier CSV a un ordre incorrect. Correction...")
                
                # Sauvegarder l'ancien fichier
                import shutil
                backup_path = self.CSV_PATH + '.backup'
                shutil.copy(self.CSV_PATH, backup_path)
                print(f"✅ Sauvegarde créée: {backup_path}")
                
                # Lire toutes les données
                with open(self.CSV_PATH, 'r', newline='', encoding='utf-8') as f:
                    reader = csv.reader(f)
                    rows = list(reader)
                
                # Réécrire avec le bon ordre
                with open(self.CSV_PATH, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    # Écrire le nouvel en-tête
                    writer.writerow([
                        'Référence', 'Date', 'Client', 'Adresse', 'Matricule',
                        'Total HT', 'TVA (19%)', 'Timbre', 'Total TTC', 'Fichier PDF'
                    ])
                    
                    # Écrire les données en échangeant les colonnes 3 et 4
                    for row in rows[1:]:  # Skip header
                        new_row = row.copy()
                        if len(row) > 4:
                            new_row[3], new_row[4] = row[4], row[3]  # Échanger Matricule et Adresse
                        writer.writerow(new_row)
                    
                print("✅ Fichier CSV restructuré avec succès")


    """def _log_raw_extraction(self, data):
        extraction_path = os.path.join(self.DATA_DIR, 'extractions.csv')
        is_new_file = not os.path.exists(extraction_path)

        with open(extraction_path, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            if is_new_file:
                writer.writerow(['Horodatage', 'Client', 'Adresse', 'Matricule', 'Produits (nom:prix:qté)'])

            produits_str = '; '.join([f"{p['nom']}:{p['prix_ht']}:{p['quantite']}" for p in data.get('produits', [])])
            writer.writerow([
                datetime.now().isoformat(),
                data.get('client', {}).get('nom', ''),
                data.get('client', {}).get('adresse', ''),
                data.get('client', {}).get('matricule_fiscal', ''),
                produits_str
            ])"""

    def get_invoice_data(self, user_input):
        """Utilise Gemini pour extraire les données de facturation"""
        try:
            model = genai.GenerativeModel(model_name='models/gemini-1.5-pro-latest')
            prompt = f"{self.system_prompt}\n\nDemande: {user_input}"
            response = model.generate_content(prompt)

            text_response = response.text.strip()
            json_str = text_response.replace('```json', '').replace('```', '').strip()
            data = json.loads(json_str)

            # Collecte des champs manquants
            missing_fields = []
            
            # Vérification des champs obligatoires client
            client = data.get('client', {})
            if not client.get('nom'):
                missing_fields.append(('nom', "Nom du client"))
            if not client.get('adresse'):
                missing_fields.append(('adresse', "Adresse du client"))
            if not client.get('matricule_fiscal'):
                missing_fields.append(('matricule_fiscal', "Matricule fiscal"))
            
            # Vérification des produits
            if not data.get('produits') or len(data['produits']) == 0:
                raise ValueError("Au moins un produit est requis")
            
            for i, p in enumerate(data['produits']):
                for field, name in [('nom', 'nom'), ('prix_ht', 'prix HT'), ('quantite', 'quantité')]:
                    if field not in p:
                        missing_fields.append((f"produits[{i}].{field}", f"{name} du produit {i+1}"))
            
            # Demander les champs manquants
            if missing_fields:
                print("\n⚠️ Certaines informations sont manquantes. Veuillez les compléter :")
                for field, description in missing_fields:
                    while True:
                        value = input(f"- {description} : ").strip()
                        if value:
                            # Mise à jour du champ dans la structure de données
                            if "." in field and field.startswith("produits["):
                                # Accéder à un champ de produit: produits[0].nom
                                match = re.match(r"produits\[(\d+)\]\.(\w+)", field)
                                if match:
                                    index = int(match.group(1))
                                    subfield = match.group(2)
                                    if subfield == 'prix_ht':
                                        try:
                                            value = float(value)
                                        except ValueError:
                                            print("❌ Le prix doit être un nombre. Réessayez.")
                                            continue
                                    elif subfield == 'quantite':
                                        try:
                                            value = int(value)
                                        except ValueError:
                                            print("❌ La quantité doit être un nombre entier. Réessayez.")
                                            continue
                                    data['produits'][index][subfield] = value
                            else:
                                # Mettre à jour un champ client
                                if not 'client' in data:
                                    data['client'] = {}
                                data['client'][field] = value
                            break
                        else:
                            print("❌ Ce champ est obligatoire. Veuillez fournir une valeur.")
            
            return data

        except json.JSONDecodeError:
            print("❌ Erreur: JSON invalide dans la réponse Gemini")
            return None
        except Exception as e:
            print(f"❌ Erreur d'analyse: {str(e)}")
            return None

    """def generate_invoice(self, data):
        ref = f"FAC-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        produits = data['produits']
        total_ht = sum(p['prix_ht'] * p['quantite'] for p in produits)
        tva = total_ht * 0.19
        total_ttc = total_ht + tva + 1

        pdf_path = os.path.join(self.FACTURES_DIR, f"{ref}.pdf")
        template = self.env.get_template("template.html")
        html = template.render(
            reference=ref,
            date=datetime.now().strftime('%d/%m/%Y'),
            client=data['client'],
            produits=produits,
            total_ht=f"{total_ht:.3f}",
            tva=f"{tva:.3f}",
            total_ttc=f"{total_ttc:.3f}"
        )

        with open(pdf_path, 'wb') as f:
            pisa.CreatePDF(html, dest=f)

        self._save_to_csv(ref, data, total_ht, tva, total_ttc, pdf_path)
        return pdf_path"""
    
    def generate_invoice(self, data):
        ref = f"FAC-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        produits = data['produits']
        total_ht = sum(p['prix_ht'] * p['quantite'] for p in produits)
        tva = total_ht * 0.19
        total_ttc = total_ht + tva + 1

        pdf_path = os.path.join(self.FACTURES_DIR, f"{ref}.pdf")
        template = self.env.get_template("template.html")
        
        # Extraire les données du client pour les passer directement au template
        client_nom = data['client'].get('nom', '')
        client_adresse = data['client'].get('adresse', '')
        client_matricule = data['client'].get('matricule_fiscal', '')
        
        html = template.render(
            facture_numero=ref,  # Notez ce changement pour correspondre au template
            date_emission=datetime.now().strftime('%d/%m/%Y'),  # Changé pour correspondre au template
            client_nom=client_nom,
            client_adresse=client_adresse,
            client_matricule=client_matricule,
            fournisseur_nom="Association INSAT Junior",  # Ajouté
            fournisseur_adresse="RDC , CHEZ L'INSAT , CENTRE URB NORD , 1082",  # Ajouté
            fournisseur_matricule="1730424/R",  # Ajouté
            produits=produits,
            total_ht=f"{total_ht:.3f}",
            tva=f"{tva:.3f}",
            total_ttc=f"{total_ttc:.3f}"
        )

        with open(pdf_path, 'wb') as f:
            pisa.CreatePDF(html, dest=f)

        self._save_to_csv(ref, data, total_ht, tva, total_ttc, pdf_path)
        return pdf_path

    def _save_to_csv(self, ref, data, total_ht, tva, total_ttc, pdf_path):
    # Assurez-vous que l'ordre correspond à celui défini dans _setup_directories
        with open(self.CSV_PATH, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                ref,
                datetime.now().strftime('%Y-%m-%d'),
                data['client']['nom'],  # Client
                data['client'].get('adresse', ''),  # Adresse
                data['client'].get('matricule_fiscal', ''),  # Matricule fiscal
                f"{total_ht:.3f}",
                f"{tva:.3f}",
                "1.000",  # Timbre
                f"{total_ttc:.3f}",
                os.path.basename(pdf_path)
            ])

if __name__ == "__main__":
    bot = InvoiceChatbot()
    print("=== CHATBOT DE FACTURATION — GEMINI ===")
    print("Décrivez votre facture naturellement")
    print("Exemple: Facture pour client XYZ, 2 ordis à 1000 DT, 1 souris à 50 DT")

    while True:
        try:
            user_input = input("\nDescription ('quit' pour sortir): ").strip()
            if user_input.lower() in ('quit', 'exit', 'q'):
                break

            if not user_input:
                continue

            data = bot.get_invoice_data(user_input)
            if data:
                pdf_path = bot.generate_invoice(data)
                print(f"\n✅ Facture générée: {os.path.basename(pdf_path)} dans {os.path.dirname(pdf_path)}")
            else:
                print("\n❌ Requête non comprise. Réessayez.")
        except KeyboardInterrupt:
            print("\nOpération annulée.")
            break
        except Exception as e:
            print(f"\n❌ Erreur: {str(e)}")