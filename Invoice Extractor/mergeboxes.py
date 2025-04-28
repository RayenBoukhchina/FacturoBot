import numpy as np
import cv2


# Fonction utilitaire pour assigner chaque mot à une ligne
def make_rows(contours, thresh_y=0.6):
    """
    Regroupe les contours en lignes de texte en fonction de leur position verticale.
    
    Args:
        contours: Liste des contours à organiser
        thresh_y: Seuil de tolérance pour l'écart vertical (défaut: 0.6)
        
    Returns:
        Dictionnaire des contours organisés par ligne (clé = position y de la ligne)
    """
    contoursBBS = {}
    height_list = []
    
    # Extraction des hauteurs de tous les contours
    for contour in contours:
        [x, y, w, h] = cv2.boundingRect(contour)
        height_list.append(h)
    
    # Tri des hauteurs pour calcul des seuils
    height_list.sort()
    
    # Calcul de la hauteur minimale (les contours plus petits seront ignorés)
    min_height = height_list[int(len(height_list)/2)] * 0.6
    print("Hauteur minimale: ", min_height)
    
    # Calcul de la hauteur typique d'une ligne de texte
    alpha = int(len(height_list)*0.3)
    line_height = 1.2 * sum(height_list[alpha:len(height_list)-alpha]) / (len(height_list)-2*alpha)

    # Organisation des contours par ligne
    for contour in contours:
        [x, y, w, h] = cv2.boundingRect(contour)
        if h < min_height: 
            continue  # Ignorer les contours trop petits
            
        cnt = [x, y, w, h]
        search_key = y
        
        # Vérifier si le contour appartient à une ligne existante
        if contoursBBS: 
            text_row = min(contoursBBS.keys(), key=lambda key: abs(key-search_key))
            
            # Si l'écart vertical dépasse le seuil, créer une nouvelle ligne
            if abs(text_row-y) > line_height:
                contoursBBS[y] = []
                contoursBBS[y].append(cnt)
            else:
                contoursBBS[text_row].append(cnt)
        else:
            # Première ligne
            contoursBBS[y] = [cnt]
    
    # Tri des contours par position horizontale dans chaque ligne
    for row in contoursBBS:
        contoursBBS[row].sort(key=lambda x: x[0])
    
    return contoursBBS

def detect_line(rect, x1, x2, y1, y2, w1, w2, h1, h2):
    """
    Détecte une ligne entre deux boîtes de texte en analysant les transitions de couleur.
    
    Args:
        rect: Zone d'image à analyser
        x1, y1, w1, h1: Coordonnées de la première boîte
        x2, y2, w2, h2: Coordonnées de la seconde boîte
        
    Returns:
        True si une ligne est détectée, False sinon
    """
    x1 = x1 + w1 + 1
    y = int((y1+h1)/2 + (y2+h2)/2)
    pos_edge = 0
    neg_edge = 0
    
    # Analyse des transitions de couleur sur la ligne médiane
    for i in range(x1, x2):
        diff = (int(rect[y][i][0]) + int(rect[y][i][1]) + int(rect[y][i][2]) - 
                int(rect[y][i-2][0]) - int(rect[y][i-2][1]) - int(rect[y][i-2][2])) / 2
        
        if diff >= 80: 
            pos_edge = 1  # Transition claire
        if diff <= -80: 
            neg_edge = 1   # Transition sombre
            
        if pos_edge and neg_edge: 
            print("Ligne détectée entre ", x1+w1, " ", x2)
            return True
            
    return False

def merge_boxes(rect, contoursBBS, thresh_x=0.3, thresh_y=0.3):
    """
    Fusionne les boîtes de texte proches horizontalement et verticalement.
    
    Args:
        rect: Image originale (pour détection des lignes)
        contoursBBS: Contours organisés par ligne
        thresh_x: Seuil de fusion horizontal (défaut: 0.3)
        thresh_y: Seuil de fusion vertical (défaut: 0.3)
        
    Returns:
        Dictionnaire des boîtes fusionnées par ligne
    """
    merge_cnt = {}
    i = 0
    
    for key in contoursBBS:
        j = 1
        i = 0
        de = []
        merge_cnt[key] = []
        [x1, y1, w1, h1] = contoursBBS[key][i]
        new_width = w1
        new_height = h1
        miny = y1
        
        # Parcours des contours de la ligne pour fusion
        while j < len(contoursBBS[key]):
            [x2, y2, w2, h2] = contoursBBS[key][j]
            
            # Conditions de fusion:
            # 1. Écart vertical faible
            # 2. Écart horizontal faible
            # 3. Hauteurs compatibles
            # 4. Pas de ligne détectée entre les boîtes
            if (abs(y1-y2) < h1*thresh_y and 
                abs(x1+new_width-x2) < h1*thresh_x and 
                abs(new_height-h2) < h2*thresh_y and 
                not (detect_line(rect, x1, x2, miny, y2, new_width, -1, new_height, h2) and 
                detect_line(rect, x1, x2, miny, y2, new_width, -1, int(new_height/2), int(h2/2))):
                
                miny = min(miny, y2)
                new_width = x2 - x1 + w2
                new_height = max(new_height, y2+h2-miny)
                j += 1
                
                if j == len(contoursBBS[key]):
                    merge_cnt[key].append([x1, miny, new_width, new_height])
            else:
                merge_cnt[key].append([x1, miny, new_width, new_height])
                i = j
                j += 1
                [x1, y1, w1, h1] = contoursBBS[key][i]
                new_width = w1
                new_height = h1
                miny = y1
                
                if j == len(contoursBBS[key]):
                    merge_cnt[key].append(contoursBBS[key][j-1])
                    
        # Cas où la ligne ne contient qu'un seul contour
        if len(contoursBBS[key]) == 1:
            merge_cnt[key].append(contoursBBS[key][0])
            
    return merge_cnt
    