from os import listdir, mkdir
from os.path import isfile, join, splitext
from pdf2image import convert_from_path

# Chemin de poppler (remplacez-le par le chemin correct sur votre système)
poppler_path = "/opt/homebrew/bin"  # macOS avec Homebrew

# Chemins des répertoires
dir_path = "assets/"
destination = "assets/"
# Lister uniquement les fichiers PDF
pdfs = [f for f in listdir(dir_path) if isfile(join(dir_path, f)) and f.lower().endswith('.pdf')]
print(pdfs)

for pdf in pdfs:
    file = join(dir_path, pdf)
    dir_name = splitext(pdf)[0]
    target = join(destination, dir_name)
    
    # Créer le dossier de destination
    mkdir(target)
    
    # Convertir le PDF en images
    pages = convert_from_path(file, poppler_path=poppler_path)  # Spécifiez le chemin de poppler
    
    # Sauvegarder les images
    for j, page in enumerate(pages, start=1):
        page.save(join(target, f"{j}.jpg"), "JPEG")
        print(f"Page {j} sauvegardée dans {target}.")