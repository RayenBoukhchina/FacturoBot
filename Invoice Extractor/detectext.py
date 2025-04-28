import csv
import cv2
import pytesseract
import numpy as np
import os
from delines import ignore_lines, segment_columns
from mergeboxes import make_rows, merge_boxes
from graph import make_graph

# Chargement des fichiers labels et synonymes
labels = {}
with open('Invoice Extractor/assets/labels.csv', mode='r') as infile:
    reader = csv.reader(infile)
    labels = {rows[1]: rows[0] for rows in reader}

synonyms = {}
with open('Invoice Extractor/assets/label_synonyms.csv', mode='r') as infile:
    reader = csv.reader(infile)
    synonyms = {rows[0]: rows[1:] for rows in reader}

keys = ['state', 'code', 'cgst', 'igst', 'sku', 'sales', 'supplier', 'taxable', 'item', 'freight', 'shipping', 'address', 'Discount', 'info', 'amt', 'amount', 'vehicle', 'bill', 'details', 'state', 'payment', 'insurance', 'charges', 'tax', 'value', 'dispatch', 'dispatched', 'seller', 'buyer', 'name', 'id', 'no.', 'number', 'gst', 'date', 'percent', 'invoice', 'total', 'cost', 'price', 'rate', 'description', 'article', 'quantity', 'amount', 'hsn', 'sl', 'buyer', 'receiver']

def levenshtein_ratio_and_distance(s, t, ratio_calc=True):
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

def get_text(image_path, output_dir, write_=False):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    img = cv2.imread(image_path)
    rect = img.copy()
    img2 = img.copy()
    file_name = os.path.basename(image_path)
    file_stem = os.path.splitext(file_name)[0]

    contours, hierarchy, img = ignore_lines(img, output_dir, file_name)

    # Fichiers de sortie
    recognized_txt_path = os.path.join(output_dir, f"{file_stem}_recognized.txt")
    file = open(recognized_txt_path, "w", encoding='utf-8')

    output_csv_path = os.path.join(output_dir, f"{file_stem}_output.csv")
    output_csv = open(output_csv_path, mode='w', newline='', encoding='utf-8')
    csv_writer = csv.writer(output_csv)
    csv_writer.writerow(['Node Number', 'Text', 'Key Detected'])

    contoursBBS = make_rows(contours)
    merge_cnt = merge_boxes(rect, contoursBBS, thresh_x=1.0, thresh_y=0.6)
    column_contours = segment_columns(img2, img.shape, merge_cnt)

    key_nodes = []
    text_val = {}
    node_number = 0

    for cnt in sorted(merge_cnt):
        for contour in merge_cnt[cnt]:
            node_number += 1
            [x, y, w, h] = contour
            if h < 10: continue

            cropped = img[max(0, y - 2):y + h + 2, max(0, x - 2): x + w + 2]
            text = pytesseract.image_to_string(cropped, lang='eng', config='--psm 6')

            key_detected = False
            for tex in text.split():
                tex = tex.lower()
                if tex in keys or any(k in tex or levenshtein_ratio_and_distance(k, tex) > 0.8 for k in keys):
                    key_detected = True
                    break

            text_val[node_number - 1] = text
            csv_writer.writerow([node_number, text, 'Yes' if key_detected else 'No'])
            if text.strip():
                file.write(text + "\n\n")

    output_csv.close()
    file.close()

    # Image annotée
    boxed_img_path = os.path.join(output_dir, f"boxed_{file_name}")
    cv2.imwrite(boxed_img_path, rect)

    make_graph(rect, merge_cnt, key_nodes, column_contours, text_val, synonyms, labels)

def main():
    image_path = 'Invoice Extractor/assets/Facture.png'
    output_dir = 'Invoice Extractor/output'
    if os.path.isfile(image_path):
        get_text(image_path, output_dir, write_=False)

if __name__ == "__main__":
    main()
