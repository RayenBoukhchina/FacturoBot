from jinja2 import Environment, FileSystemLoader
from xhtml2pdf import pisa
import csv
import os
from datetime import datetime

class InvoiceGenerator:
    def __init__(self):
        self.env = Environment(loader=FileSystemLoader('Invoice Generator/templates'))
        self.base_dir = 'Invoice Generator'
        os.makedirs(f'{self.base_dir}/factures', exist_ok=True)
        os.makedirs(f'{self.base_dir}/data', exist_ok=True)
        
        self.csv_file = f'{self.base_dir}/data/factures.csv'
        self._init_csv()
    
    def _init_csv(self):
        if not os.path.exists(self.csv_file):
            with open(self.csv_file, mode='w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'Numéro', 'Date', 'Client', 'Matricule', 'Adresse',
                    'Total HT', 'TVA', 'Timbre', 'Total TTC', 'Fichier PDF'
                ])
    
    def _generate_invoice_number(self):
        current_year = datetime.now().strftime("%Y")
        new_seq = 1
        
        if os.path.exists(self.csv_file):
            with open(self.csv_file, mode='r', encoding='utf-8') as f:
                reader = csv.reader(f)
                next(reader)  # Skip header
                last_row = None
                for row in reader:
                    last_row = row
                
                if last_row and last_row[0]:
                    last_num = last_row[0]
                    try:
                        # Gestion robuste des différents formats
                        if '-' in last_num:
                            parts = last_num.split('-')
                            if len(parts) >= 3:  # Format FAC-AAAA-NNNN
                                seq_part = parts[-1]
                                new_seq = int(seq_part) + 1
                            else:  # Autre format avec -
                                new_seq = int(parts[-1]) + 1
                        else:  # Juste un nombre
                            new_seq = int(last_num) + 1
                    except (ValueError, IndexError):
                        new_seq = 1  # Retour au défaut si erreur
        
        return f"FAC-{current_year}-{new_seq:04d}"
    
    def generate(self, client_data, products):
        # Génération du numéro
        invoice_number = self._generate_invoice_number()
        
        # Calculs financiers
        total_ht = sum(p['prix_ht'] * p['quantite'] for p in products)
        tva = round(total_ht * 0.19, 3)
        total_ttc = round(total_ht * 1.19 + 1, 3)  # +1 DT pour timbre fiscal
        
        # Génération PDF
        pdf_path = f"{self.base_dir}/factures/{invoice_number}.pdf"
        self._generate_pdf(
            invoice_number,
            datetime.now().strftime("%d/%m/%Y"),
            client_data,
            products,
            total_ht,
            tva,
            total_ttc,
            pdf_path
        )
        
        # Sauvegarde dans CSV
        self._save_to_csv(
            invoice_number,
            client_data,
            products,
            total_ht,
            tva,
            total_ttc,
            pdf_path
        )
        
        return pdf_path
    
    def _generate_pdf(self, numero, date, client, products, total_ht, tva, total_ttc, pdf_path):
        template = self.env.get_template("template.html")
        html = template.render(
            facture_numero=numero,
            date_emission=date,
            client_nom=client['nom'],
            client_adresse=client['adresse'],
            client_matricule=client.get('matricule', ''),
            produits=products,
            total_ht=total_ht,
            tva=tva,
            total_ttc=total_ttc
        )
        
        with open(pdf_path, "wb") as f:
            pisa_status = pisa.CreatePDF(html, dest=f, encoding='UTF-8')
            if pisa_status.err:
                raise Exception("Erreur génération PDF")
    
    def _save_to_csv(self, numero, client, products, total_ht, tva, total_ttc, pdf_path):
        with open(self.csv_file, mode='a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                numero,
                datetime.now().strftime("%Y-%m-%d"),
                client['nom'],
                client.get('matricule', ''),
                client['adresse'],
                f"{total_ht:.3f}",
                f"{tva:.3f}",
                "1.000",  # Timbre fiscal fixe
                f"{total_ttc:.3f}",
                pdf_path
            ])

# Partie exécution principale
if __name__ == "__main__":
    # Initialisation
    generator = InvoiceGenerator()
    
    # Données de test
    client = {
        'nom': 'Client Test',
        'adresse': '123 Rue Exemple, Tunis',
        'matricule': 'MF12345678'
    }
    
    products = [
        {'nom': 'Ordinateur Portable', 'prix_ht': 1500, 'quantite': 2},
        {'nom': 'Souris Sans Fil', 'prix_ht': 35, 'quantite': 3}
    ]
    
    # Génération
    try:
        pdf_path = generator.generate(client, products)
        print(f"Facture générée avec succès : {pdf_path}")
    except Exception as e:
        print(f"Erreur : {str(e)}")