import cv2 
import numpy as np
import math
import os

def validate_image_path(image_path):
    """Vérifie que le fichier image existe et est lisible"""
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Le fichier {image_path} n'existe pas")
    if not os.access(image_path, os.R_OK):
        raise PermissionError(f"Pas de permission pour lire le fichier {image_path}")

def rotate_image(image, angle):
    """Rotation améliorée avec interpolation et gestion des bords"""
    (h, w) = image.shape[:2]
    (cX, cY) = (w // 2, h // 2)
    
    M = cv2.getRotationMatrix2D((cX, cY), -angle, 1.0)
    cos = np.abs(M[0, 0])
    sin = np.abs(M[0, 1])
    
    nW = int((h * sin) + (w * cos))
    nH = int((h * cos) + (w * sin))
    
    M[0, 2] += (nW / 2) - cX
    M[1, 2] += (nH / 2) - cY
    
    # Rotation avec interpolation cubique et bordure réfléchie
    return cv2.warpAffine(image, M, (nW, nH), 
                         flags=cv2.INTER_CUBIC,
                         borderMode=cv2.BORDER_REFLECT)

def preprocess_image(img):
    """Amélioration de la qualité d'image avant traitement"""
    # Dénosage
    img = cv2.fastNlMeansDenoisingColored(img, None, 10, 10, 7, 21)
    
    # Amélioration du contraste
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
    limg = cv2.merge((clahe.apply(l), a, b))
    return cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)

def getAngle(img):
    """Détection d'angle améliorée avec gestion des erreurs"""
    # Prétraitement
    img = preprocess_image(img)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Seuillage adaptatif
    thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                  cv2.THRESH_BINARY_INV, 11, 2)
    
    # Détection des contours du document
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    max_area = 0
    best_cnt = None
    
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area > max_area:
            max_area = area
            best_cnt = cnt
    
    if best_cnt is not None:
        # Utiliser le rectangle englobant pour l'angle
        rect = cv2.minAreaRect(best_cnt)
        angle = rect[-1]
        
        # Ajustement de l'angle selon l'orientation
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle
        
        # Limiter l'angle à ±15 degrés
        angle = max(min(angle, 15), -15)
        return angle
    
    # Fallback: méthode originale si la détection de contour échoue
    print("Utilisation de la méthode alternative de détection d'angle...")
    ret, bw = cv2.threshold(gray, 0, 255, cv2.THRESH_OTSU | cv2.THRESH_BINARY_INV)
    x = bw.copy()
    
    # Détection des lignes verticales
    vertical_size = x.shape[0] // 100
    verticalStructure = cv2.getStructuringElement(cv2.MORPH_RECT, (1, vertical_size))
    x = cv2.morphologyEx(x, cv2.MORPH_OPEN, verticalStructure)
    
    lines = cv2.HoughLinesP(x, 1, np.pi/180, 150, minLineLength=200, maxLineGap=20)
    
    if lines is None:
        return 0.0
    
    angle = 0.0
    val = 0
    
    for line in lines:
        for x1, y1, x2, y2 in line:
            lineAngle = math.degrees(math.atan2(y2 - y1, x2 - x1))
            length = math.sqrt((x2-x1)**2 + (y2-y1)**2)
            val += length
            angle += (length * lineAngle)
    
    if val == 0:
        return 0.0
    
    return angle / val

def process_invoice(input_path, output_path):
    """Pipeline complet de traitement"""
    try:
        validate_image_path(input_path)
        img = cv2.imread(input_path)
        
        if img is None:
            raise ValueError("Impossible de charger l'image")
        
        angle = getAngle(img)
        print(f"Angle de rotation détecté: {angle:.2f} degrés")
        
        rotatedImg = rotate_image(img, angle)
        cv2.imwrite(output_path, rotatedImg)
        print(f"Image corrigée sauvegardée sous: {output_path}")
        
        return rotatedImg
    
    except Exception as e:
        print(f"Erreur lors du traitement: {str(e)}")
        return None

if __name__ == "__main__":
    # Configuration des chemins
    input_path = 'Invoice Extractor/assets/Facture.png'
    output_path = 'Invoice Extractor/assets/rotated_improved.png'
    
    # Exécution
    result = process_invoice(input_path, output_path)
    
    # Affichage (optionnel)
    if result is not None:
        cv2.imshow("Original", cv2.imread(input_path))
        cv2.imshow("Corrigé", result)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
