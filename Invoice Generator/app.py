from flask import Flask, render_template, request, jsonify, send_file, url_for, redirect
import os
import sys
import json
import csv
from datetime import datetime
from chatbot import InvoiceChatbot  # Import direct, car nous sommes dans le même dossier

app = Flask(__name__)
bot = InvoiceChatbot()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/history')
def history():
    # Lecture du fichier CSV des factures
    csv_path = bot.CSV_PATH
    invoices = []
    
    if os.path.exists(csv_path):
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            invoices = list(reader)
    
    return render_template('history.html', invoices=invoices)

@app.route('/api/parse', methods=['POST'])
def parse_description():
    """Analyse la description et retourne les données extraites"""
    user_input = request.form.get('description')
    if not user_input:
        return jsonify({"error": "Description vide"}), 400

    try:
        # Utiliser le mode web pour récupérer les champs manquants
        data, missing_or_error = bot.get_invoice_data(user_input, web_mode=True)
        
        # Si une erreur est survenue
        if data is None:
            return jsonify({"error": missing_or_error}), 400
            
        # Si des champs sont manquants
        if missing_or_error:
            missing_fields = []
            for field, description in missing_or_error:
                missing_fields.append({
                    "field": field,
                    "description": description
                })
            return jsonify({"missing_fields": missing_fields, "partial_data": data}), 200
        
        # Calculs pour l'aperçu
        for product in data['produits']:
            product['total'] = product['prix_ht'] * product['quantite']
        
        total_ht = sum(p['prix_ht'] * p['quantite'] for p in data['produits'])
        tva = total_ht * 0.19
        total_ttc = total_ht + tva + 1
        
        # Préparer les données pour l'aperçu avec les totaux
        preview_data = {
            "client": data['client'],
            "produits": data['produits'],
            "total_ht": round(total_ht, 3),
            "tva": round(tva, 3),
            "total_ttc": round(total_ttc, 3),
            "raw_data": data  # Pour la génération ultérieure
        }
        
        return jsonify(preview_data)
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/generate', methods=['POST'])
def generate_invoice():
    """Génère la facture PDF à partir des données"""
    try:
        data = request.json
        if not data:
            return jsonify({"error": "Données manquantes"}), 400
        
        # Générer le PDF
        pdf_path = bot.generate_invoice(data)
        
        # Obtenir le nom de fichier pour le téléchargement
        filename = os.path.basename(pdf_path)
        
        return jsonify({
            "success": True, 
            "message": "Facture générée avec succès",
            "file": filename,
            "download_url": url_for('download_file', filename=filename)
        })
    
    except Exception as e:
        return jsonify({"error": f"Erreur lors de la génération: {str(e)}"}), 500

@app.route('/download/<filename>')
def download_file(filename):
    """Téléchargement du fichier PDF généré"""
    file_path = os.path.join(bot.FACTURES_DIR, filename)
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    else:
        return "Fichier non trouvé", 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5050, debug=True)