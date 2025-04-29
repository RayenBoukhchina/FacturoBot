import os
import csv
import speech_recognition as sr
from datetime import datetime
from jinja2 import Environment, FileSystemLoader
from xhtml2pdf import pisa

class FacturoBot:
    def __init__(self):
        # Configuration des chemins basée sur votre architecture
        self.BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        self.TEMPLATES_DIR = os.path.join(self.BASE_DIR, 'templates')
        self.FACTURES_DIR = os.path.join(self.BASE_DIR, 'factures')
        self.DATA_DIR = os.path.join(self.BASE_DIR, 'data')
        self.CSV_PATH = os.path.join(self.DATA_DIR, 'factures.csv')

        # Initialisation des composants
        self.recognizer = sr.Recognizer()
        self.env = Environment(loader=FileSystemLoader(self.TEMPLATES_DIR))
        self._setup_directories()

    def _setup_directories(self):
        """Crée les répertoires nécessaires s'ils n'existent pas"""
        os.makedirs(self.FACTURES_DIR, exist_ok=True)
        os.makedirs(self.DATA_DIR, exist_ok=True)
        
        if not os.path.exists(self.CSV_PATH):
            with open(self.CSV_PATH, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'Numéro', 'Date', 'Client', 'Adresse', 
                    'Matricule', 'Total HT', 'TVA', 'Total TTC', 
                    'Fichier PDF'
                ])

    def _get_user_input(self, prompt, is_required=True, is_numeric=False):
        """Capture la saisie vocale ou clavier"""
        while True:
            try:
                print(f"\n{prompt} (parlez maintenant)...")
                with sr.Microphone() as source:
                    audio = self.recognizer.listen(source, timeout=5)
                    text = self.recognizer.recognize_google(audio, language='fr-FR').strip()
                    
                    if text.lower() in ('stop', 'annuler'):
                        return None
                        
                    if is_required and not text:
                        raise ValueError("Champ obligatoire")
                        
                    if is_numeric:
                        return float(text.replace(',', '.'))
                    return text
                    
            except sr.UnknownValueError:
                print("Je n'ai pas compris. Répétez s'il vous plaît.")
            except sr.RequestError:
                # Fallback au clavier si erreur de reconnaissance
                text = input(f"{prompt} : ").strip()
                if is_numeric:
                    return float(text.replace(',', '.'))
                return text

    def collect_invoice_data(self):
        """Collecte les données de la facture"""
        print("\n\033[1m=== NOUVELLE FACTURE ===\033[0m")
        
        client = {
            'nom': self._get_user_input("Nom du client"),
            'adresse': self._get_user_input("Adresse du client"),
            'matricule': self._get_user_input("Matricule fiscal (ou 'passer')", False)
        }
        
        if client['matricule'] and client['matricule'].lower() == 'passer':
            client['matricule'] = None

        produits = []
        while True:
            print("\n\033[1m› Ajout d'un produit\033[0m")
            nom = self._get_user_input("Nom du produit (ou 'terminer')")
            if nom and nom.lower() == 'terminer':
                if not produits:
                    print("⚠️ Vous devez ajouter au moins un produit")
                    continue
                break
                
            produits.append({
                'nom': nom,
                'prix_ht': self._get_user_input("Prix unitaire HT", True, True),
                'quantite': self._get_user_input("Quantité", True, True)
            })

        return {'client': client, 'produits': produits}

    def generate_invoice(self, data):
        """Génère le PDF et sauvegarde les données"""
        # Numérotation automatique
        invoice_count = len([f for f in os.listdir(self.FACTURES_DIR) if f.endswith('.pdf')])
        invoice_number = f"FAC-{datetime.now().strftime('%Y')}-{invoice_count + 1:04d}"
        
        # Calculs financiers
        total_ht = sum(p['prix_ht'] * p['quantite'] for p in data['produits'])
        tva = round(total_ht * 0.19, 3)
        total_ttc = round(total_ht + tva + 1, 3)  # +1 DT pour timbre fiscal

        # Génération PDF
        pdf_filename = f"{invoice_number}.pdf"
        pdf_path = os.path.join(self.FACTURES_DIR, pdf_filename)
        
        template = self.env.get_template("template.html")
        html = template.render(
            facture_numero=invoice_number,
            date_emission=datetime.now().strftime('%d/%m/%Y'),
            client=data['client'],
            produits=data['produits'],
            total_ht=total_ht,
            tva=tva,
            total_ttc=total_ttc
        )

        with open(pdf_path, 'wb') as f:
            pisa.CreatePDF(html, dest=f)

        # Sauvegarde CSV
        with open(self.CSV_PATH, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                invoice_number,
                datetime.now().strftime('%Y-%m-%d'),
                data['client']['nom'],
                data['client']['adresse'],
                data['client']['matricule'] or '',
                total_ht,
                tva,
                total_ttc,
                pdf_path
            ])

        return pdf_path

    def run(self):
        """Point d'entrée principal"""
        print("\033[1m\n=== FACTUROBOT ===\033[0m")
        print("Dites 'stop' pour annuler ou 'terminer' pour finir\n")
        
        while True:
            data = self.collect_invoice_data()
            if not data:
                continue
                
            pdf_path = self.generate_invoice(data)
            print(f"\n\033[1;32m✓ Facture générée:\033[0m {os.path.basename(pdf_path)}")
            print(f"Chemin complet: {pdf_path}")
            
            continuer = self._get_user_input("\nNouvelle facture ? (oui/non)", False)
            if not continuer or continuer.lower() != 'oui':
                print("\nMerci d'avoir utilisé FacturoBot!")
                break

if __name__ == "__main__":
    try:
        bot = FacturoBot()
        bot.run()
    except KeyboardInterrupt:
        print("\nOpération annulée")
    except Exception as e:
        print(f"\n\033[1;31mErreur:\033[0m {str(e)}")