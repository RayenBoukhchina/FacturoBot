import numpy as np
import cv2
import math

def getAngle(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    bw = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2)
    x = bw.copy()
    y = bw.copy()

    # Détection des lignes verticales
    verticalStructure = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 50))
    x = cv2.erode(x, verticalStructure)
    x = cv2.dilate(x, verticalStructure)
    lines = cv2.HoughLinesP(x, 1, np.pi / 180, threshold=100, minLineLength=100, maxLineGap=10)
    angle = 0.0
    val = 0
    for line in lines:
        x1, y1, x2, y2 = line[0]
        lineAngle = np.arctan2(y2 - y1, x2 - x1) * 180 / np.pi
        if abs(lineAngle) > 80:  # Filtrer les lignes presque verticales
            val += abs(y1 - y2)
            angle += abs(y1 - y2) * lineAngle

    if val == 0:
        return 0  # Aucune ligne verticale détectée

    vertical_angle = angle / val

    # Détection des lignes horizontales
    horizontalStructure = cv2.getStructuringElement(cv2.MORPH_RECT, (50, 1))
    y = cv2.erode(y, horizontalStructure)
    y = cv2.dilate(y, horizontalStructure)
    lines = cv2.HoughLinesP(y, 1, np.pi / 180, threshold=100, minLineLength=100, maxLineGap=10)
    angle = 0.0
    val = 0
    for line in lines:
        x1, y1, x2, y2 = line[0]
        lineAngle = np.arctan2(y2 - y1, x2 - x1) * 180 / np.pi
        if abs(lineAngle) < 10:  # Filtrer les lignes presque horizontales
            val += abs(x1 - x2)
            angle += abs(x1 - x2) * lineAngle

    if val == 0:
        return vertical_angle  # Aucune ligne horizontale détectée

    horizontal_angle = angle / val

    # Calcul de l'angle moyen
    rotateAngle = (vertical_angle + horizontal_angle) / 2
    return rotateAngle

def rotate_image(image, angle):
    (h, w) = image.shape[:2]
    (cX, cY) = (w / 2, h / 2)
    M = cv2.getRotationMatrix2D((cX, cY), -angle, 1.0)
    cos = np.abs(M[0, 0])
    sin = np.abs(M[0, 1])
    nW = int((h * sin) + (w * cos))
    nH = int((h * cos) + (w * sin))
    M[0, 2] += (nW / 2) - cX
    M[1, 2] += (nH / 2) - cY
    rotated = cv2.warpAffine(image, M, (nW, nH), borderMode=cv2.BORDER_CONSTANT, borderValue=(255, 255, 255))
    return rotated

filename = '/Users/associationinsatjunior/Desktop/Projects/FactureDigiprint/abcd.jpeg'
img = cv2.imread(filename)
angle = getAngle(img)
rotatedImg = rotate_image(img, -angle)
cv2.imwrite('/Users/associationinsatjunior/Desktop/Projects/FactureDigiprint/rotated2.png', rotatedImg)