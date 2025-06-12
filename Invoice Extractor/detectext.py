import csv
import cv2
import pytesseract
import numpy as np
import os
import re
import json
from datetime import datetime
from delines import ignore_lines, segment_columns
from mergeboxes import make_rows, merge_boxes
from graph import make_graph

# Fonction utilitaire pour résoudre les chemins relatifs
def get_path(relative_path):
    """Convertit un chemin relatif en chemin absolu basé sur le dossier du script"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(script_dir, relative_path)

# Chargement des fichiers labels et synonymes
labels = {}
try:
    with open(get_path('assets/labels.csv'), mode='r') as infile:
        reader = csv.reader(infile)
        labels = {rows[1]: rows[0] for rows in reader}
    print("Fichier labels.csv chargé avec succès")
except FileNotFoundError:
    print("ATTENTION: Fichier labels.csv introuvable")
    labels = {}

synonyms = {}
try:
    with open(get_path('assets/label_synonyms.csv'), mode='r') as infile:
        reader = csv.reader(infile)
        synonyms = {rows[0]: rows[1:] for rows in reader}
    print("Fichier label_synonyms.csv chargé avec succès")
except FileNotFoundError:
    print("ATTENTION: Fichier label_synonyms.csv introuvable")
    synonyms = {}

keys = ['state', 'code', 'cgst', 'igst', 'sku', 'sales', 'supplier', 'taxable', 'item', 'freight', 'shipping', 'address', 'Discount', 'info', 'amt', 'amount', 'vehicle', 'bill', 'details', 'state', 'payment', 'insurance', 'charges', 'tax', 'value', 'dispatch', 'dispatched', 'seller', 'buyer', 'name', 'id', 'no.', 'number', 'gst', 'date', 'percent', 'invoice', 'total', 'cost', 'price', 'rate', 'description', 'article', 'quantity', 'amount', 'hsn', 'sl', 'buyer', 'receiver']

def levenshtein_ratio_and_distance(s, t, ratio_calc=True):
    """
    Calcule la distance de Levenshtein entre deux chaînes
    et retourne le ratio de similarité si ratio_calc=True.
    """
    rows = len(s) + 1
    cols = len(t) + 1
    distance = np.zeros((rows, cols), dtype=int)
    for i in range(1, rows): distance[i][0] = i
    for k in range(1, cols): distance[0][k] = k
    for col in range(1, cols):
        for row in range(1, rows):
            cost = 0 if s[row - 1] == t[col - 1] else (2 if ratio_calc else 1)
            distance[row][col] = min(
                distance[row - 1][col] + 1,
                distance[row][col - 1] + 1,
                distance[row - 1][col - 1] + cost
            )
    if ratio_calc:
        return ((len(s) + len(t)) - distance[row][col]) / (len(s) + len(t))
    else:
        return distance[row][col]

def visualize_all_contours(image, contoursBBS, merge_cnt, key_nodes, filename):
    """
    Génère une visualisation combinée avec différentes couleurs pour les contours.
    
    Args:
        image: Image originale
        contoursBBS: Contours initiaux (non fusionnés)
        merge_cnt: Contours fusionnés
        key_nodes: Indices des nœuds contenant des mots-clés
        filename: Nom du fichier de sortie
    """
    debug_img = image.copy()
    
    # Dessiner tous les contours initiaux en rouge (couleur plus claire)
    for key in contoursBBS:
        for cnt in contoursBBS[key]:
            x, y, w, h = cnt
            cv2.rectangle(debug_img, (x, y), (x+w, y+h), (0, 0, 200), 1)  # Rouge plus clair
    
    # Dessiner les contours fusionnés en vert
    for key in merge_cnt:
        for cnt in merge_cnt[key]:
            x, y, w, h = cnt
            cv2.rectangle(debug_img, (x, y), (x+w, y+h), (0, 200, 0), 1)  # Vert
    
    # Créer une carte pour trouver les contours correspondant aux nœuds clés
    node_idx = 0
    node_map = {}
    
    for cnt_key in sorted(merge_cnt):
        for cnt_idx, cnt in enumerate(merge_cnt[cnt_key]):
            node_map[node_idx] = (cnt_key, cnt_idx)
            node_idx += 1
    
    # Dessiner les contours des mots-clés avec une bordure bleue plus épaisse
    for node_idx in key_nodes:
        if node_idx in node_map:
            cnt_key, cnt_idx = node_map[node_idx]
            [x, y, w, h] = merge_cnt[cnt_key][cnt_idx]
            cv2.rectangle(debug_img, (x, y), (x+w, y+h), (255, 0, 0), 2)  # Bleu
    
    # Ajouter une légende
    font = cv2.FONT_HERSHEY_SIMPLEX
    legend_start_y = 30
    cv2.putText(debug_img, 'Contours initiaux', (10, legend_start_y), font, 0.5, (0, 0, 200), 1)
    cv2.putText(debug_img, 'Contours fusionnes', (10, legend_start_y+20), font, 0.5, (0, 200, 0), 1)
    cv2.putText(debug_img, 'Mots-cles', (10, legend_start_y+40), font, 0.5, (255, 0, 0), 1)
    
    cv2.imwrite(filename, debug_img)
    print(f"Image de visualisation complète enregistrée: {filename}")
    
    return debug_img

def extract_important_data(text_dict, key_nodes, contours):
    """Extrait les données importantes du texte OCR comme la référence, date, etc."""
    
    data = {
        "reference": None,
        "date": None,
        "total": None,
        "montant_ht": None,
        "tva": None,
        "timbre_fiscal": None,
        "adresse_fournisseur": None,
        "adresse_client": None,
        "matricule_fiscale_fournisseur": None,
        "matricule_fiscale_client": None
    }
    
    # Patterns de recherche pour les différentes informations
    patterns = {
        "reference": [
            r'\b(?:facture|invoice|fact)(?:\s+n[°o]?\.?|:|\s+)?\s*([A-Z0-9\-/]{3,})',
            r'\bn[°o]\.?:?\s*([A-Z0-9\-/]{3,})'
        ],
        "date": [
            r'\b(?:date|du):?\s*(\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4})',
            r'(\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4})'
        ],
        "total": [
            r'\btotal\s*(?:ttc|ttc:)?:?\s*(\d+[,.]\d*)\s*(?:dt|tnd|d\.t)',
            r'\btotal\s*(?:ttc|ttc:)?:?\s*(\d+)'
        ],
        "montant_ht": [
            r'\btotal\s*(?:ht|h\.t|ht:)?:?\s*(\d+[,.]\d*)',
            r'\bmontant\s*(?:ht|h\.t|ht:)?:?\s*(\d+[,.]\d*)'
        ],
        "tva": [
            r'\btva\s*(?:\d*%)?:?\s*(\d+[,.]\d*)',
            r'\btva\s*(\d+[,.]\d*)'
        ],
        "timbre_fiscal": [
            r'\btimbre\s*fiscal:?\s*(\d+[,.]\d*)',
            r'\btimbre:?\s*(\d+[,.]\d*)'
        ],
        "matricule_fiscale_fournisseur": [
            r'\b(?:mf|matricule\s*fiscale):?\s*(\d{7}[A-Z/]\w{1,3})'
        ],
        "matricule_fiscale_client": [
            r'\bclient(?:.*?)(?:mf|matricule\s*fiscale):?\s*(\d{7}[A-Z/]\w{1,3})'
        ]
    }
    
    # Recherche contextuelle dans tous les textes
    for node_id, text in text_dict.items():
        normalized_text = text.lower().strip().replace('\n', ' ')
        
        # Vérifier chaque pattern pour chaque type de donnée
        for data_type, pattern_list in patterns.items():
            if data[data_type] is not None:
                continue  # Si on a déjà trouvé cette donnée, passer au suivant
                
            for pattern in pattern_list:
                match = re.search(pattern, normalized_text)
                if match:
                    data[data_type] = match.group(1)
                    break
    
    # Recherche spéciale pour les adresses (généralement plus longues)
    adresse_found = False
    for node_id, text in text_dict.items():
        if "adresse" in text.lower() or "address" in text.lower():
            # Trouver les nœuds suivants qui pourraient contenir l'adresse
            # Cette logique simplifiée suppose que l'adresse est dans les 2-3 nœuds suivants
            for i in range(1, 4):
                if node_id + i in text_dict:
                    addr_text = text_dict[node_id + i]
                    if len(addr_text.split()) > 3:  # Une adresse a généralement plusieurs mots
                        if not adresse_found:
                            data["adresse_fournisseur"] = addr_text
                            adresse_found = True
                        else:
                            data["adresse_client"] = addr_text
                            break
    
    return data

def ensure_all_outputs(image_path, output_dir):
    """S'assure que tous les fichiers de sortie sont générés correctement."""
    
    file_stem = os.path.splitext(os.path.basename(image_path))[0]
    
    # 1. Vérifier et générer l'image sans lignes
    no_lines_path = os.path.join(output_dir, f"{file_stem}_no_lines.jpg")
    if not os.path.exists(no_lines_path):
        # Générer spécifiquement l'image sans lignes
        img = cv2.imread(image_path)
        if img is not None:
            try:
                img_no_lines = ignore_lines(img)
                cv2.imwrite(no_lines_path, img_no_lines)
                print(f"Image sans lignes générée: {no_lines_path}")
            except Exception as e:
                print(f"Erreur lors de la génération de l'image sans lignes: {e}")
    
    # 2. Vérifier et générer l'image de visualisation combinée
    combined_vis_path = os.path.join(output_dir, f"{file_stem}_visualisation.jpg")
    if not os.path.exists(combined_vis_path):
        # Tenter de recréer à partir des données déjà extraites
        csv_path = os.path.join(output_dir, f"{file_stem}_output.csv")
        if os.path.exists(csv_path):
            try:
                # Lire les données du CSV pour trouver les mots-clés
                keywords_nodes = []
                with open(csv_path, 'r', encoding='utf-8') as f:
                    reader = csv.reader(f)
                    next(reader)  # Sauter l'en-tête
                    for row in reader:
                        if len(row) >= 3 and row[2] == 'Yes':
                            keywords_nodes.append(int(row[0]) - 1)
                
                # Si on a trouvé des mots-clés, recréer la visualisation
                if keywords_nodes:
                    generate_keywords_visualization(image_path, output_dir, keywords_nodes)
            except Exception as e:
                print(f"Erreur lors de la régénération de la visualisation: {e}")

def generate_keywords_visualization(image_path, output_dir, key_nodes):
    """Génère une visualisation des mots-clés identifiés."""
    
    file_stem = os.path.splitext(os.path.basename(image_path))[0]
    img = cv2.imread(image_path)
    if img is None:
        print(f"Impossible de charger l'image pour la visualisation: {image_path}")
        return
    
    # Retraitement minimal pour obtenir les contours
    img_no_lines = ignore_lines(img)
    gray = cv2.cvtColor(img_no_lines, cv2.COLOR_BGR2GRAY) if len(img_no_lines.shape) > 2 else img_no_lines
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    contours = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if len(contours) == 3:
        _, contours, _ = contours
    else:
        contours, _ = contours
    
    # Refaire le processus d'organisation et de fusion
    contoursBBS = make_rows(contours)
    merge_cnt = merge_boxes(img, contoursBBS, thresh_x=1.0, thresh_y=0.6)
    
    # Générer la visualisation combinée
    combined_vis_path = os.path.join(output_dir, f"{file_stem}_visualisation.jpg") 
    visualize_all_contours(img, contoursBBS, merge_cnt, key_nodes, combined_vis_path)

def get_text(image_path, output_dir, write_=False, visualize=True):
    """
    Extrait le texte d'une image de facture.
    
    Args:
        image_path: Chemin vers l'image
        output_dir: Répertoire de sortie
        write_: Écrire les résultats dans un fichier
        visualize: Générer des images de visualisation
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"Impossible de charger l'image: {image_path}")
        
    rect = img.copy()
    img2 = img.copy()
    file_name = os.path.basename(image_path)
    file_stem = os.path.splitext(file_name)[0]

    try:
        # Suppression des lignes et récupération des contours
        img_no_lines = ignore_lines(img)
        
        # Conversion en niveaux de gris si nécessaire
        if len(img_no_lines.shape) > 2:
            gray = cv2.cvtColor(img_no_lines, cv2.COLOR_BGR2GRAY)
        else:
            gray = img_no_lines
            
        # Binarisation et détection des contours
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        contours = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Ajuster selon la version d'OpenCV
        if len(contours) == 3:
            _, contours, hierarchy = contours
        else:
            contours, hierarchy = contours
            
        # Sauvegarde pour débogage
        no_lines_path = os.path.join(output_dir, f"{file_stem}_no_lines.jpg")
        cv2.imwrite(no_lines_path, img_no_lines)
        print(f"Image sans lignes enregistrée: {no_lines_path}")
        
    except Exception as e:
        print(f"Erreur lors de la suppression des lignes: {e}")
        print("Utilisation de l'image originale comme fallback")
        img_no_lines = img.copy()
        gray = cv2.cvtColor(img_no_lines, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        contours = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if isinstance(contours, tuple) and len(contours) >= 2:
            contours = contours[-2]
        elif isinstance(contours, list):
            contours = contours
    
    # Fichiers de sortie
    recognized_txt_path = os.path.join(output_dir, f"{file_stem}_recognized.txt")
    file = open(recognized_txt_path, "w", encoding='utf-8')

    # Organisation des contours par lignes
    contoursBBS = make_rows(contours)

    # Fusion des contours proches pour reconstituer les mots
    merge_cnt = merge_boxes(rect, contoursBBS, thresh_x=1.0, thresh_y=0.6)
    
    try:
        # Segmentation en colonnes
        column_contours = segment_columns(img2, img_no_lines.shape, merge_cnt)
    except Exception as e:
        print(f"Erreur lors de la segmentation en colonnes: {e}")
        column_contours = {}

    key_nodes = []
    text_val = {}
    node_number = 0
    
    # Extraction du texte par OCR pour chaque contour fusionné
    all_text_segments = []
    
    for cnt in sorted(merge_cnt):
        for contour in merge_cnt[cnt]:
            node_number += 1
            [x, y, w, h] = contour
            if h < 10: continue  # Ignorer les contours trop petits
            
            # Extraction de la zone de l'image correspondant au contour
            try:
                cropped = img_no_lines[max(0, y - 2):y + h + 2, max(0, x - 2): x + w + 2]
                
                if cropped.size == 0:
                    print(f"ATTENTION: Contour vide ignoré: x={x}, y={y}, w={w}, h={h}")
                    continue
                
                # OCR avec Tesseract
                text = pytesseract.image_to_string(cropped, lang='eng', config='--psm 6')
                text = text.strip()
            except Exception as e:
                print(f"Erreur d'extraction OCR: {e}")
                text = ""
            
            if not text:
                continue
                
            # Détection des mots-clés
            key_detected = False
            for tex in text.split():
                tex = tex.lower()
                if tex in keys or any(k in tex or levenshtein_ratio_and_distance(k, tex) > 0.8 for k in keys):
                    key_detected = True
                    key_nodes.append(node_number - 1)
                    break
            
            # Stockage des résultats
            text_val[node_number - 1] = text
            
            # Diviser le texte en lignes et créer une entrée pour chaque ligne
            lines = text.split('\n') 
            for line in lines:
                line = line.strip()
                if line:  # Ne pas ajouter de lignes vides
                    line_key_detected = False
                    for word in line.lower().split():
                        if word in keys or any(k in word or levenshtein_ratio_and_distance(k, word) > 0.8 for k in keys):
                            line_key_detected = True
                            break
                    
                    all_text_segments.append((node_number, line, line_key_detected))
                        
            if write_:
                file.write(text + "\n\n")
    
    file.close()
    
    # Écriture du fichier CSV avec une ligne par segment de texte
    output_csv_path = os.path.join(output_dir, f"{file_stem}_output.csv")
    with open(output_csv_path, mode='w', newline='', encoding='utf-8') as output_csv:
        csv_writer = csv.writer(output_csv)
        csv_writer.writerow(['Node Number', 'Text', 'Key Detected'])
        
        for node_num, text_segment, key_detected in all_text_segments:
            csv_writer.writerow([node_num, text_segment, 'Yes' if key_detected else 'No'])
    
    print(f"Fichier CSV créé avec succès: {output_csv_path}")

    # Visualisation combinée avec tous les contours
    if visualize:
        combined_vis_path = os.path.join(output_dir, f"{file_stem}_visualisation.jpg")
        visualize_all_contours(img, contoursBBS, merge_cnt, key_nodes, combined_vis_path)
        print(f"Visualisation combinée enregistrée: {combined_vis_path}")

    try:
        # Construction du graphe de relations
        make_graph(rect, merge_cnt, key_nodes, column_contours, text_val, synonyms, labels)
    except Exception as e:
        print(f"Erreur lors de la construction du graphe: {e}")
    
    # Extraction des données importantes
    important_data = extract_important_data(text_val, key_nodes, merge_cnt)
    
    # Ajout de méta-informations pour le fichier CSV global
    important_data["nom_fichier"] = file_name
    important_data["date_extraction"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Enregistrement dans le fichier CSV global
    update_global_csv(important_data, get_path('output/factures_extraites.csv'))
    
    return {
        "text": text_val,
        "key_nodes": key_nodes,
        "contours": merge_cnt,
        "columns": column_contours,
        "important_data": important_data
    }

def update_global_csv(data, csv_path):
    """
    Met à jour le fichier CSV global avec les données extraites d'une facture.
    
    Args:
        data: Dictionnaire des données importantes extraites
        csv_path: Chemin vers le fichier CSV global
    """
    # Définir les entêtes du CSV global
    fieldnames = [
        "nom_fichier", "date_extraction", "reference", "date", "total", 
        "montant_ht", "tva", "timbre_fiscal", "adresse_fournisseur", 
        "adresse_client", "matricule_fiscale_fournisseur", "matricule_fiscale_client"
    ]
    
    file_exists = os.path.isfile(csv_path)
    
    # Ouvrir le fichier en mode ajout ou création
    with open(csv_path, mode='a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        
        # Écrire l'entête seulement si le fichier est nouveau
        if not file_exists:
            writer.writeheader()
        
        # Écrire les données de la facture
        writer.writerow(data)
    
    print(f"Données ajoutées au fichier CSV global: {csv_path}")

def show_image(image, title='Image'):
    """Affiche une image dans une fenêtre redimensionnable"""
    cv2.namedWindow(title, cv2.WINDOW_NORMAL)
    cv2.imshow(title, image)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

def main():
    """Fonction principale"""
    # Utiliser get_path pour résoudre les chemins de manière robuste
    image_path = get_path('assets/1.jpg')
    output_dir = get_path('output')
    
    # Créer le répertoire de sortie s'il n'existe pas
    os.makedirs(output_dir, exist_ok=True)
    
    if os.path.isfile(image_path):
        print(f"Traitement de l'image: {image_path}")
        try:
            # Extraction du texte et des données importantes
            result = get_text(image_path, output_dir, write_=False, visualize=True)
            print("Extraction terminée avec succès!")
            
            # S'assurer que tous les fichiers nécessaires sont générés
            ensure_all_outputs(image_path, output_dir)
            
            # Afficher les données importantes extraites
            print("\n=== DONNÉES IMPORTANTES EXTRAITES ===")
            for key, value in result["important_data"].items():
                if key not in ["nom_fichier", "date_extraction"]:
                    print(f"{key}: {value if value else 'Non détecté'}")
            
            print("\n=== STATISTIQUES ===")
            print(f"Nombre de lignes de texte: {len(result['contours'])}")
            print(f"Nombre de mots-clés détectés: {len(result['key_nodes'])}")
            print(f"Données ajoutées au fichier CSV global: {get_path('output/factures_extraites.csv')}")
            
        except Exception as e:
            print(f"Erreur lors du traitement: {e}")
            import traceback
            traceback.print_exc()
    else:
        print(f"Erreur: Le fichier {image_path} n'existe pas")
        
        # Afficher les fichiers disponibles dans le dossier assets
        assets_dir = get_path('assets')
        if os.path.exists(assets_dir):
            files = os.listdir(assets_dir)
            if files:
                print("Fichiers disponibles dans le dossier assets:")
                for file in files:
                    if file.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.tiff')):
                        print(f" - {file} (image)")
                    else:
                        print(f" - {file}")
            else:
                print("Le dossier assets est vide.")
        else:
            print(f"Le dossier assets n'existe pas. Création du dossier...")
            os.makedirs(assets_dir, exist_ok=True)
        
    print(f"Tous les résultats ont été enregistrés dans: {output_dir}")

if __name__ == "__main__":
    main()