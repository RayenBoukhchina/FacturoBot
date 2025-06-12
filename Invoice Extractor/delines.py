import cv2 
import numpy as np
import os

def stretch_columns(img):
    """
    Étend les boîtes de délimitation verticalement en utilisant des opérations morphologiques. 
    Args:
        img: Image binaire en entrée    
    Returns:
        Image après érosion/dilatation pour étendre les colonnes verticalement
    """
    # Création d'un élément structurant horizontal pour l'érosion
    structure = cv2.getStructuringElement(cv2.MORPH_RECT, (10,1))
    img = cv2.erode(img, structure, iterations=1) 
    
    # Dilatation verticale pour étendre les colonnes
    structure = cv2.getStructuringElement(cv2.MORPH_RECT, (1,20))
    x = cv2.dilate(img, structure, iterations=2) 
    
    # Dilatation horizontale finale
    structure = cv2.getStructuringElement(cv2.MORPH_RECT, (10,1))
    x = cv2.dilate(x, structure, iterations=1) 
    
    # Détection des contours
    contours, hierarchy = cv2.findContours(x, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    return x

def segment_columns(img, shape, contours):
    """
    Segmente l'image en colonnes à partir des contours détectés.
    Args:
        img: Image originale
        shape: Dimensions de l'image
        contours: Liste des contours détectés     
    Returns:
        Liste des contours des blocs de texte détectés
    """
    # Création d'un masque vide
    mask = np.zeros((shape[0], shape[1]), np.uint8)
    
    # Dessin des rectangles des contours sur le masque
    for key in contours:
        for i in contours[key]:
            [x, y, w, h] = i
            mask = cv2.rectangle(mask, (x, y), (x + w, y + h), (255, 0, 0), -1)
    
    # Opérations morphologiques pour affiner les colonnes
    structure = cv2.getStructuringElement(cv2.MORPH_RECT, (4,1))
    mask = cv2.erode(mask, structure, iterations=1)
    structure = cv2.getStructuringElement(cv2.MORPH_RECT, (1,20))
    mask = cv2.dilate(mask, structure, iterations=2)
    
    # Détection des contours finaux
    cont, hierarchy = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Dessin des rectangles sur l'image originale (optionnel)
    for c in cont:
        [x, y, w, h] = cv2.boundingRect(c)
        img = cv2.rectangle(img, (x, y), (x + w, y + h), (255, 0, 0), 3) 
    
    return cont

def ignore_lines(img):
    """
    Supprime les lignes horizontales et verticales de l'image.   
    Args:
        img: Image originale en couleur      
    Returns:
        Image binaire après suppression des lignes
    """
    # Conversion en niveaux de gris et seuillage
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    ret, bw = cv2.threshold(gray, 0, 255, cv2.THRESH_OTSU | cv2.THRESH_BINARY_INV) 
    ret = min(255, int(1.5 * ret))
    
    # Dilatation pour connecter les pixels
    structure = cv2.getStructuringElement(cv2.MORPH_RECT, (1,2))
    x = cv2.dilate(bw, structure, iterations=1) 
    y = bw
    
    # Détection des lignes verticales
    rows = x.shape[0]
    vertical_size = rows // 80
    verticalStructure = cv2.getStructuringElement(cv2.MORPH_RECT, (1, vertical_size))
    x = cv2.erode(x, verticalStructure)
    x = cv2.dilate(x, verticalStructure) 
    
    # Détection des lignes horizontales
    cols = y.shape[1]
    horizontal_size = cols // 90
    horizontalStructure = cv2.getStructuringElement(cv2.MORPH_RECT, (horizontal_size, 1))
    y = cv2.erode(y, horizontalStructure)
    y = cv2.dilate(y, horizontalStructure) 
    
    # Combinaison des masques de lignes
    ret, bw = cv2.threshold(gray, 0, 255, cv2.THRESH_OTSU) 
    bw = bw + x + y
    
    # Dilatation finale pour regrouper les zones de texte
    rect_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5)) 
    ret, thresh1 = cv2.threshold(bw, 0, 255, cv2.THRESH_OTSU | cv2.THRESH_BINARY_INV) 
    dilation = cv2.dilate(thresh1, rect_kernel, iterations=1) 
    
    return dilation

if __name__ == "__main__":
    # Configuration
    image_path = "Invoice Extractor/assets/Facture.png"
    
    # Chargement de l'image
    img = cv2.imread(image_path)
    if img is None:
        print(f"Erreur: Impossible de charger l'image {image_path}")
        exit()

    # Étape 1: Suppression des lignes et détection des contours
    dilation = ignore_lines(img)
    
    # Étape 2: Segmentation des colonnes
    shape = dilation.shape
    img_blocks = img.copy()  # Copie de l'image originale
    blocks = segment_columns(img_blocks, shape, {'contours': [cv2.boundingRect(c) for c in cv2.findContours(dilation, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[0]]})
    
    print("Traitement terminé avec succès.")