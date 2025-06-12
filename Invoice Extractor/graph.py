import cv2 
import numpy as np


def detect_line(rect, x, y1, y2):
    """
    Détecte une ligne verticale dans une zone rectangulaire en analysant les transitions de couleur.  
    Args:
        rect: Zone d'image à analyser (format BGR)
        x: Position horizontale à analyser
        y1, y2: Bornes verticales de la zone d'analyse    
    Returns:
        True si une ligne est détectée, False sinon
    """
    pos_edge = 0  # Détection de transition claire
    neg_edge = 0  # Détection de transition sombre
    
    for y in range(y1, y2):
        # Calcul de la différence de luminosité entre le pixel courant et 2 pixels au-dessus
        diff = (int(rect[y][x][0]) + int(rect[y][x][1]) + int(rect[y][x][2]) - 
               int(rect[y-2][x][0]) - int(rect[y-2][x][1]) - int(rect[y-2][x][2])) / 2
        
        if diff >= 80:
            pos_edge = 1
        if diff <= -80:
            neg_edge = 1
            
        if pos_edge and neg_edge:
            print(f"Ligne détectée entre {y1} et {y2}")
            return True
            
    return False


def levenshtein_ratio_and_distance(s, t, ratio_calc=True):
    """
    Calcule la distance ou le ratio de Levenshtein entre deux chaînes.   
    Args:
        s, t: Chaînes à comparer
        ratio_calc: Si True, retourne un ratio normalisé (défaut: True)       
    Returns:
        Ratio de similarité (si ratio_calc=True) ou distance brute (sinon)
    """
    # Initialisation de la matrice
    rows = len(s) + 1
    cols = len(t) + 1
    distance = np.zeros((rows, cols), dtype=int)

    # Remplissage des indices
    for i in range(1, rows):
        for k in range(1, cols):
            distance[i][0] = i
            distance[0][k] = k

    # Calcul des coûts
    for col in range(1, cols):
        for row in range(1, rows):
            if s[row-1] == t[col-1]:
                cost = 0  # Même caractère
            else:
                cost = 2 if ratio_calc else 1  # Coût de substitution
                
            distance[row][col] = min(
                distance[row-1][col] + 1,      # Suppression
                distance[row][col-1] + 1,      # Insertion
                distance[row-1][col-1] + cost  # Substitution
            )

    if ratio_calc:
        # Calcul du ratio normalisé
        return ((len(s) + len(t)) - distance[row][col]) / (len(s) + len(t))
    else:
        return distance[row][col]


class Node:  
    """
    Classe représentant un nœud dans le graphe de structure du document.    
    Attributs:
        i: Identifiant unique
        x1, x2, y1, y2: Coordonnées de la boîte englobante
        edges: Liste des nœuds connectés
        parent: Nœud parent (-1 si aucun)
        is_key: Booléen indiquant si c'est un champ clé
        column: Numéro de colonne
        down, right, left: Nœuds adjacents
        text_value: Texte contenu dans le nœud
        match_percent: Pourcentage de correspondance avec les synonymes
    """
    def __init__(self, i, x1, x2, y1, y2, text_val):  
        self.i = i
        self.x1 = x1  
        self.x2 = x2
        self.y1 = y1
        self.y2 = y2
        self.edges = []  # Nœuds connectés
        self.parent = -1
        self.is_key = False
        self.column = -1
        self.down = -1
        self.right = -1
        self.left = -1
        self.parents = []  # Historique des parents
        self.table_number = -1
        self.table_col = -1
        self.table_row = -1
        self.text_value = text_val
        self.match_percent = 0


def overlapping(x1, x2, y1, y2, a1, a2, b1, b2):
    """
    Vérifie si deux rectangles se chevauchent.
    
    Returns:
        True si chevauchement, False sinon
    """
    if x2 <= a1 or x1 >= a2: 
        return False
    elif y2 <= b1 or y1 >= b2:
        return False
    else: 
        return True


def x_overlapping(x1, x2, y1, y2, a1, a2, b1, b2):
    """
    Vérifie le chevauchement horizontal entre deux rectangles.
    
    Returns:
        0: Pas de chevauchement
        1: Chevauchement partiel (<70%)
        2: Chevauchement significatif (>=70%)
    """
    if x2 <= a1 or x1 >= a2: 
        return 0
    if abs(x1 - a1) > 200:
        return 0
        
    l = max(x1, a1)
    r = min(x2, a2)
    overlap_ratio1 = (r - l) / (x2 - x1)
    overlap_ratio2 = (r - l) / (a2 - a1)
    
    if overlap_ratio1 >= 0.7 or overlap_ratio2 >= 0.7:
        return 2
    return 1


def dfs(img, row, column, contours, Nodes, go_down, go_right, parent, root):
    """
    Parcours en profondeur pour construire les relations entre les nœuds.
    
    Args:
        img: Image pour visualisation
        row, column: Position courante dans les contours
        contours: Structure organisée des contours
        Nodes: Liste des nœuds
        go_down, go_right: Directions de recherche
        parent, root: Nœuds parents
    """
    if row >= len(contours) or column >= len(contours[row]):
        return
        
    current_node = contours[row][column]
    x1 = Nodes[current_node].x1
    x2 = Nodes[current_node].x2
    y1 = Nodes[current_node].y1
    y2 = Nodes[current_node].y2
    
    # Recherche vers la droite
    if go_right and column < len(contours[row])-1 and not Nodes[contours[row][column+1]].is_key:
        next_node = contours[row][column+1]
        a1 = Nodes[next_node].x1
        b1 = Nodes[next_node].y1
        cv2.line(img, (x1, y1), (a1, b1), (167, 88, 162), 2)
        Nodes[current_node].right = next_node
        Nodes[next_node].left = current_node
        dfs(img, row, column+1, contours, Nodes, False, True, current_node, root)
    
    # Recherche vers le bas
    if go_down and row < len(contours)-1:
        flag = False
        for next_row in range(row+1, min(row+5, len(contours))):
            if flag: 
                break
                
            for i in range(len(contours[next_row])):
                if flag: 
                    break
                    
                a1 = Nodes[contours[next_row][i]].x1
                a2 = Nodes[contours[next_row][i]].x2
                b1 = Nodes[contours[next_row][i]].y1
                b2 = Nodes[contours[next_row][i]].y2

                overlap = x_overlapping(x1, x2, y1, y2, a1, a2, b1, b2)
                
                if overlap == 1: 
                    flag = True
                    break 
                elif overlap == 2:
                    if not Nodes[contours[next_row][i]].is_key:
                        Nodes[current_node].down = contours[next_row][i]
                        Nodes[contours[next_row][i]].parent = current_node
                        Nodes[contours[next_row][i]].root = root
                        cv2.line(img, (x1, y1), (a1, b1), (167, 88, 162), 2)
                        dfs(img, next_row, i, contours, Nodes, True, False, current_node, root)
                        flag = True
                    else: 
                        flag = True
                        break


def assign_columns(img,columns, Nodes):
	node_columns = {}
	i=0

	for i in range(0,len(Nodes) ):
		x1=Nodes[i].x1
		x2=Nodes[i].x2
		y1=Nodes[i].y1
		y2=Nodes[i].y2
		for j in range(0,len(columns) ):
			[a1,b1,w,h] = cv2.boundingRect(columns[j])
			a2 = a1+w
			b2 = b1+h
			if ( overlapping(x1,x2,y1,y2,a1,a2,b1,b2) ):
				Nodes[i].column = j
				#cv2.line(img,(x1,y1),(a1,b1),(204,100,0),2)
				#print(a1,a2,b1,b2,x1,x2,y1,y2)
				break
			

def make_graph(img,contours,key_fields,column_contours, text_val, synonyms, labels):

	#indexing countours with node numbers
	i=0
	node_map={}
	contours_as_nodes={}
	Nodes = []
	node_to_row={}
	row_key = {}
	j=0
	table_count = 0

	for key in sorted(contours):
		contours_as_nodes[j]=[]
		row_key[j]=key 
		for Node in contours[key]:
			if(i in text_val):
				Nodes.append(node(i,Node[0],Node[0]+Node[2],Node[1],Node[1]+Node[3],text_val[i]))
			else:
				Nodes.append(node(i,Node[0],Node[0]+Node[2],Node[1],Node[1]+Node[3],""))
			node_map[i] = Node
			contours_as_nodes[j].append(i)
			node_to_row[i] = j
			i+=1
		j+=1

	graph = np.zeros((i,i),dtype= bool )
	
	for Node in key_fields:
		Nodes[Node].is_key = True
	#for row in contours_as_nodes:
	#	for column in range(0,len(contours_as_nodes[row])):

	# print('Printing.......')

	key_row = 0
	maxi = 0
	for row in contours_as_nodes:
		count = 0
		print(contours_as_nodes[row])
		for column in range(0, len(contours_as_nodes[row])):
			if(Nodes[contours_as_nodes[row][column]].is_key):
				count += 1
		if(count >= maxi):
			maxi = count
			key_row = row

	#we get the table start here, this row is the header	
	print(key_row)
	y1 = Nodes[contours_as_nodes[key_row][0]].y1
	for j in range(0,len(contours_as_nodes[key_row])):
		Nodes[contours_as_nodes[key_row][j]].is_key=True
		Nodes[contours_as_nodes[key_row][j]].table_number = table_count
		Nodes[contours_as_nodes[key_row][j]].table_col = j
		Nodes[contours_as_nodes[key_row][j]].table_row = 0
		Nodes[contours_as_nodes[key_row][j]].text_value = Nodes[contours_as_nodes[key_row][j]].text_value.upper()

	num_fields = 0
	start_val = key_row + 1

	#now we'll check next row if there is any key (i.e. there could be subcategories)
	text_blobs = 0 
	key_blobs = 0
	for j in range(0,len(contours_as_nodes[key_row+1])):
		if(Nodes[contours_as_nodes[key_row+1][j]].is_key):
			key_blobs+=1
		else : text_blobs+=1
		Nodes[contours_as_nodes[key_row][j]].table_number = table_count

	if(key_blobs>=text_blobs):
		for j in range(0,len(contours_as_nodes[key_row+1])):
			Nodes[contours_as_nodes[key_row+1][j]].is_key=True
		start_val += 1
	y2 = Nodes[contours_as_nodes[start_val][0]].y1
	while(not detect_line(img, Nodes[contours_as_nodes[start_val][1]].x1,  y1, y2)):
		y1 = y2
		start_val += 1
		y2 = Nodes[contours_as_nodes[start_val][0]].y1

	num_fields = len(contours_as_nodes[start_val])
	
	table_val_stop = start_val
	table_end  = table_val_stop
	table_row_count = 0
	#now we gonna make sure no value inside the table is a key (we'll spare first column tho)
	for i in range(start_val, len(contours_as_nodes)):
		table_row_count+=1
		if(abs(len(contours_as_nodes[i])-num_fields)>1):
			table_val_stop = i-1
			table_count += 1
			break
		Nodes[contours_as_nodes[i][0]].table_col = 0
		Nodes[contours_as_nodes[i][0]].table_row = table_row_count
		Nodes[contours_as_nodes[i][0]].table_number = table_count

		for j in range(1,len(contours_as_nodes[i])):
			Nodes[contours_as_nodes[i][j]].is_key=False
			Nodes[contours_as_nodes[i][j]].table_col = j
			Nodes[contours_as_nodes[i][j]].table_row = table_row_count
			Nodes[contours_as_nodes[i][j]].table_number = table_count
				
	#now we gotta search if there is a total field that can be used
	#we need keys value for this thing
	#matching for column has to be done using coordinates

	flag = True
	cnt = 0
	for i in range(table_val_stop + 1, min(table_val_stop+5,len(contours_as_nodes))):
		col = 0
		cnt += 1
		for j in range(0, len(contours_as_nodes[i])):
			if('total' in Nodes[contours_as_nodes[i][j]].text_value.lower() and Nodes[contours_as_nodes[i][j]].is_key):
				# map values based on x coordinates
				table_end = i
				col = j
				Nodes[contours_as_nodes[i][j]].table_number = table_count-1
				# Nodes[contours_as_nodes[i][j]].table_col = col
				# Nodes[contours_as_nodes[i][j]].table_row = Nodes[contours_as_nodes[table_val_stop][k]].table_row + cnt

				break
		if(table_end == i):
			for j in range(col, len(contours_as_nodes[i])):
				b1 = Nodes[contours_as_nodes[i][j]]
				for k in range(0, len(contours_as_nodes[table_val_stop])):
					b2 = Nodes[contours_as_nodes[table_val_stop][k]]
					if(x_overlapping(b1.x1, b1.x2, b1.y1, b1.y2, b2.x1, b2.x2, b2.y1, b2.y2) > 0):
						Nodes[contours_as_nodes[i][j]].table_col = Nodes[contours_as_nodes[table_val_stop][k]].table_col
						Nodes[contours_as_nodes[i][j]].table_row = Nodes[contours_as_nodes[table_val_stop][k]].table_row + cnt
						break

			for j in range(table_end-1,table_val_stop,-1):
				cnt-=1
				for k in range(0, len(contours_as_nodes[j])):
					Nodes[contours_as_nodes[j][k]].table_row = Nodes[contours_as_nodes[table_val_stop][k]].table_row + cnt
					Nodes[contours_as_nodes[j][k]].table_number = Nodes[contours_as_nodes[table_val_stop][k]].table_number
					b1 = Nodes[contours_as_nodes[j][k]]
					for l in range(0,len(contours_as_nodes[table_val_stop])):
						b2 = Nodes[contours_as_nodes[table_val_stop][l]]
						if(x_overlapping(b1.x1, b1.x2, b1.y1, b1.y2, b2.x1, b2.x2, b2.y1, b2.y2) > 0):
							Nodes[contours_as_nodes[j][k]].table_col = Nodes[contours_as_nodes[table_val_stop][l]].table_col
							break		
			break				

	print("Print Vals")
	print(key_row, table_val_stop, start_val) 
	table_extract = [ [""]*(num_fields+5) ]
	for i in range(0, table_end - key_row +3):
		table_extract.append([""]*num_fields)
	for i in range(key_row, table_end+1):
		for j in range(0, len(contours_as_nodes[i])):
			# print(Nodes[contours_as_nodes[i][j]].text_value, Nodes[contours_as_nodes[i][j]].table_row, Nodes[contours_as_nodes[i][j]].table_col)
			table_extract[Nodes[contours_as_nodes[i][j]].table_row][Nodes[contours_as_nodes[i][j]].table_col] = Nodes[contours_as_nodes[i][j]].text_value
			if(Nodes[contours_as_nodes[i][j]].is_key):
				table_extract[Nodes[contours_as_nodes[i][j]].table_row][Nodes[contours_as_nodes[i][j]
                                                                  ].table_col] = table_extract[Nodes[contours_as_nodes[i][j]].table_row][Nodes[contours_as_nodes[i][j]].table_col].upper()
	print(table_extract)
	import csv

	for keyfield in key_fields:
		row =  node_to_row[keyfield]
		for i in range(0,len(contours_as_nodes[row]) ):
			if contours_as_nodes[row][i] == keyfield: 
				column = i
				break
		root = contours_as_nodes[row][column]
		parent = contours_as_nodes[row][column]
		dfs(img,row,column,contours_as_nodes,Nodes,True,True,parent,root)
			#img = make_edges(img,key,i,contours_as_nodes,graph,node_map,key_fields,Nodes)
	#assign_columns(img,column_contours,Nodes)
	#for i in Nodes:
		#print(i.column)
	#make_columns(img,contours_as_nodes,node_map,graph,key_fields,Nodes,node_to_row)

	for i in Nodes:
		if i.table_number != -1:
			if(Nodes[i.down].left != -1 and Nodes[Nodes[i.down].left].is_key):
				i.down = -1

	key_match = find_label(synonyms, key_fields, Nodes)
	print(key_match)
	for i in key_match:
		print(labels[i], Nodes[int(key_match[i])].text_value)
	data = extract(labels, key_match, Nodes)
	with open('output.csv', 'w', newline="") as csv_file:  
		writer = csv.writer(csv_file)
		for key, value in data.items():
			writer.writerow([key.upper(), value])

	with open('output.csv', 'a+', newline="") as csv_file:  
		writer = csv.writer(csv_file)
		for i in range(0,2):
			writer.writerow('')


	with open("output.csv", "a+", newline="") as f:
		writer = csv.writer(f)
		writer.writerows(table_extract)


	# print(ppp)
	cv2.imwrite("Invoice Extractor/output/graph.jpg",img )


def find_label(synonyms, detected_fields, Nodes):
	#key_match is a dict with key= label no. and value = node number that matches that key
	key_match = {}
	prepositions = ['the', 'of', 'a', 'in', 'an', 'is', 'on']
	for i in detected_fields:
		# separate key from value if in same node
		words = Nodes[i].text_value.lower()
		words = words.split(' ')
		node_words = []

		for j in words:
			if j not in prepositions:
				node_words.append(j)

		for label in synonyms:
			words = synonyms[label]
			for p in words:	
				p=p.lower()
				words = p.split(' ')
				synonym_words = []
				word_count = 0
				match_count = 0
				for j in words:
					if j not in prepositions and len(j)>=2:
						word_count += 1
						for k in node_words:
							if(k == j or (len(k) > 2 and levenshtein_ratio_and_distance(k, j) > 0.8)):
								match_count += 1
					percent = 0
					if(word_count>0):percent = (match_count/word_count)
					if Nodes[i].match_percent < percent:
						Nodes[i].match_percent = percent
						if(percent>0.7):
							key_match[label] = i
	return key_match


def extract_non_table(labels, keymatch, Nodes, cur_node, label, vis):
	if cur_node == -1:
	    return ""
	if vis[cur_node]:
		return ""
	vis[cur_node] = True
	a=""
	if cur_node not in vis:
		a = Nodes[cur_node].text_value + \
		    extract_non_table(labels, keymatch, Nodes,
		                      Nodes[cur_node].down, label, vis)
	return a


def get_key(val, key_match):
    for key, value in key_match.items():
        # print(val, value)
        if val == value:
            return key
    return "-1"

def extract(labels, key_match, Nodes):
	vis = np.zeros((len(Nodes)), dtype=bool)
	data = {}
	for i in range(0, len(Nodes)):
		if Nodes[i].is_key and Nodes[i].table_number==-1:
			# print(str(Nodes[i]))
			label = get_key(str(i),key_match)
			if label == "-1":
				label = Nodes[i].text_value
				# print ("-1")
			else :
				label = labels[label]
				# print(label)
			# data[label] = ""
			a = ""
			a = extract_non_table(labels, key_match, Nodes,
			                      Nodes[i].right, label, vis)
			a += extract_non_table(labels, key_match, Nodes,
			                       Nodes[i].down, label, vis)
			if(':' in label):
				kk, vv = label.split(':',1)
				data[kk] = vv
				continue
			if(len(a)>0):
				data[label]=a
	return data

import matplotlib.pyplot as plt
def main():
    """
    Fonction principale pour le traitement d'image de facture.
    """
    image_path = 'Invoice Extractor/assets/Facture.png'  
    image = cv2.imread(image_path)

    if image is None:
        print("Erreur: Impossible de charger l'image.")
        return

    print("Traitement de l'image...")

    # Conversion en niveaux de gris
    gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Réduction du bruit
    blurred_image = cv2.GaussianBlur(gray_image, (5, 5), 0)

    # Détection des contours
    edges = cv2.Canny(blurred_image, 50, 150)

    # Détection des lignes
    lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=50, minLineLength=50, maxLineGap=10)

    if lines is not None:
        print(f"{len(lines)} lignes détectées.")
        for line in lines:
            x1, y1, x2, y2 = line[0]
            cv2.line(image, (x1, y1), (x2, y2), (0, 255, 0), 2)

    # Détection des contours
    contours, _ = cv2.findContours(edges, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    if contours:
        print(f"{len(contours)} zones de texte détectées.")
        cv2.drawContours(image, contours, -1, (0, 0, 255), 2)

    print("Traitement terminé avec succès.")


if __name__ == "__main__":
    main()