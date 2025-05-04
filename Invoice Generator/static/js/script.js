document.addEventListener('DOMContentLoaded', () => {
    // Obtenir les références aux éléments DOM
    const form = document.getElementById('invoice-form');
    const description = document.getElementById('description');
    const generateBtn = document.getElementById('generate-btn');
    const spinner = document.getElementById('spinner');
    const previewDiv = document.getElementById('invoice-preview');
    const previewContent = document.getElementById('preview-content');
    const confirmBtn = document.getElementById('confirm-invoice');
    const successMessage = document.getElementById('success-message');
    const downloadLink = document.getElementById('download-link');
    const errorMessage = document.getElementById('error-message');
    const voiceInputBtn = document.getElementById('voice-input-btn');
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    
    if (SpeechRecognition) {
        const recognition = new SpeechRecognition();
        recognition.lang = 'fr-FR';  // Définir la langue en français
        recognition.continuous = false;  // Un seul résultat à la fois
        recognition.interimResults = false;  // Attendre le résultat final
        
        let isListening = false;
        
        // Événement pour le bouton de microphone
        voiceInputBtn.addEventListener('click', () => {
            if (!isListening) {
                // Commencer à écouter
                recognition.start();
                voiceInputBtn.classList.add('btn-danger');
                voiceInputBtn.classList.remove('btn-outline-success');
                voiceInputBtn.innerHTML = '<i class="bi bi-mic-mute-fill"></i>';
                isListening = true;
            } else {
                // Arrêter d'écouter
                recognition.stop();
                voiceInputBtn.classList.add('btn-outline-success');
                voiceInputBtn.classList.remove('btn-danger');
                voiceInputBtn.innerHTML = '<i class="bi bi-mic-fill"></i>';
                isListening = false;
            }
        });

        // Événements de reconnaissance vocale
        recognition.onresult = (event) => {
            const speechResult = event.results[0][0].transcript;
            const currentText = description.value.trim();
            
            if (currentText) {
                description.value = currentText + ' ' + speechResult;
            } else {
                description.value = speechResult;
            }
            
            // Arrêter d'écouter après avoir obtenu un résultat
            recognition.stop();
            voiceInputBtn.classList.add('btn-outline-success');
            voiceInputBtn.classList.remove('btn-danger');
            voiceInputBtn.innerHTML = '<i class="bi bi-mic-fill"></i>';
            isListening = false;
        };
        
        recognition.onerror = (event) => {
            console.error('Erreur de reconnaissance vocale:', event.error);
            // Réinitialiser l'état du bouton
            voiceInputBtn.classList.add('btn-outline-success');
            voiceInputBtn.classList.remove('btn-danger');
            voiceInputBtn.innerHTML = '<i class="bi bi-mic-fill"></i>';
            isListening = false;
            
             // Afficher un message d'erreur
             const errorMsg = document.createElement('div');
             errorMsg.className = 'alert alert-warning mt-2';
             errorMsg.textContent = "Erreur de reconnaissance vocale. Veuillez réessayer.";
             document.getElementById('invoice-form').appendChild(errorMsg);
             
             // Supprimer le message après 3 secondes
             setTimeout(() => {
                 errorMsg.remove();
             }, 3000);
         };
         recognition.onend = () => {
            // Réinitialiser l'état du bouton
            voiceInputBtn.classList.add('btn-outline-success');
            voiceInputBtn.classList.remove('btn-danger');
            voiceInputBtn.innerHTML = '<i class="bi bi-mic-fill"></i>';
            isListening = false;
        };
    } else {
        // La reconnaissance vocale n'est pas supportée
        voiceInputBtn.style.display = 'none';
        const warningMsg = document.createElement('div');
        warningMsg.className = 'alert alert-warning mt-2';
        warningMsg.textContent = "La reconnaissance vocale n'est pas supportée par votre navigateur.";
        document.querySelector('.mb-3').appendChild(warningMsg);
    }

    // Variable pour stocker les données extraites
    let extractedData = null;
    
    // Soumission du formulaire pour analyser la description
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        // Réinitialiser les états précédents
        errorMessage.classList.add('d-none');
        previewDiv.classList.add('d-none');
        successMessage.classList.add('d-none');
        
        // Vérifier que le champ description n'est pas vide
        if (!description.value.trim()) {
            errorMessage.textContent = "Veuillez entrer une description pour la facture";
            errorMessage.classList.remove('d-none');
            return;
        }
        
        // Afficher le spinner de chargement
        generateBtn.disabled = true;
        spinner.classList.remove('d-none');
        
        try {
            // Envoyer la requête au serveur
            const formData = new FormData();
            formData.append('description', description.value.trim());
            
            const response = await fetch('/api/parse', {
                method: 'POST',
                body: formData
            });
            
            const data = await response.json();
            
            if (response.ok) {
                // Vérifier s'il y a des champs manquants
                if (data.missing_fields) {
                    // Afficher le formulaire pour les champs manquants
                    let formHtml = `
                        <div class="alert alert-warning">
                            <strong>Informations manquantes</strong>
                            <p>Veuillez compléter les champs suivants pour générer la facture :</p>
                        </div>
                        <form id="missing-fields-form" class="mt-3">
                    `;
                    
                    data.missing_fields.forEach(field => {
                        let fieldId = field.field.replace(/[\[\].]/g, '_');
                        let inputType = "text";
                        let additionalAttrs = "";
                        
                        // Adapter le type d'input en fonction du champ
                        if (field.field.endsWith('prix_ht')) {
                            inputType = "number";
                            additionalAttrs = "step='0.001' min='0'";
                        } else if (field.field.endsWith('quantite')) {
                            inputType = "number";
                            additionalAttrs = "step='1' min='1'";
                        }
                        
                        formHtml += `
                            <div class="mb-3">
                                <label for="${fieldId}" class="form-label">${field.description} :</label>
                                <input type="${inputType}" class="form-control" id="${fieldId}" 
                                    name="${field.field}" ${additionalAttrs} required>
                            </div>
                        `;
                    });
                    
                    formHtml += `
                            <button type="submit" class="btn btn-success">Compléter et continuer</button>
                        </form>
                    `;
                    
                    previewContent.innerHTML = formHtml;
                    previewDiv.classList.remove('d-none');
                    
                    // Gérer la soumission du formulaire de champs manquants
                    const missingFieldsForm = document.getElementById('missing-fields-form');
                    missingFieldsForm.addEventListener('submit', (e) => {
                        e.preventDefault();
                        
                        // Récupérer les données partielles
                        const partialData = data.partial_data;
                        
                        // Compléter avec les champs manquants
                        const formData = new FormData(missingFieldsForm);
                        
                        for (const [fieldName, value] of formData.entries()) {
                            // Traiter le champ en fonction de son format
                            if (fieldName.startsWith('produits[')) {
                                const match = fieldName.match(/produits\[(\d+)\]\.(\w+)/);
                                if (match) {
                                    const index = parseInt(match[1]);
                                    const subfield = match[2];
                                    
                                    // S'assurer que l'array des produits et l'index existent
                                    if (!partialData.produits) partialData.produits = [];
                                    if (!partialData.produits[index]) partialData.produits[index] = {};
                                    
                                    // Convertir en nombre si nécessaire
                                    if (subfield === 'prix_ht') {
                                        partialData.produits[index][subfield] = parseFloat(value);
                                    } else if (subfield === 'quantite') {
                                        partialData.produits[index][subfield] = parseInt(value);
                                    } else {
                                        partialData.produits[index][subfield] = value;
                                    }
                                }
                            } else {
                                // Champ client
                                if (!partialData.client) partialData.client = {};
                                partialData.client[fieldName] = value;
                            }
                        }
                        
                        // Maintenant, générer l'aperçu avec les données complètes
                        showPreview(partialData);
                    });
                } else {
                    // Stocker les données pour utilisation ultérieure
                    extractedData = data.raw_data;
                    
                    // Montrer directement l'aperçu car toutes les données sont présentes
                    showPreview(data);
                }
            } else {
                // Afficher l'erreur
                errorMessage.textContent = data.error || "Une erreur s'est produite lors de l'analyse";
                errorMessage.classList.remove('d-none');
            }
        } catch (err) {
            errorMessage.textContent = "Erreur de communication avec le serveur";
            errorMessage.classList.remove('d-none');
        } finally {
            // Masquer le spinner
            generateBtn.disabled = false;
            spinner.classList.add('d-none');
        }
    });
    
    // Fonction pour afficher l'aperçu de la facture avec les données
    function showPreview(data) {
        // Calculer les totaux si nécessaire
        let total_ht = 0;
        for (const product of data.produits) {
            if (!product.total) {
                product.total = product.prix_ht * product.quantite;
            }
            total_ht += product.total;
        }
        
        const tva = data.tva || total_ht * 0.19;
        const total_ttc = data.total_ttc || (total_ht + tva + 1);
        
        // Créer l'HTML de l'aperçu
        let html = `
            <div class="client-details">
                <div class="row">
                    <div class="col-md-6">
                        <h5>Client</h5>
                        <p><strong>Nom:</strong> ${data.client.nom}</p>
                        <p><strong>Adresse:</strong> ${data.client.adresse || ''}</p>
                        <p><strong>Matricule fiscal:</strong> ${data.client.matricule_fiscal || ''}</p>
                    </div>
                    <div class="col-md-6">
                        <h5>Détails</h5>
                        <p><strong>Date:</strong> ${new Date().toLocaleDateString()}</p>
                    </div>
                </div>
            </div>
            
            <h5>Produits</h5>
            <div class="table-responsive product-table">
                <table class="table table-striped">
                    <thead>
                        <tr>
                            <th>Produit</th>
                            <th>Prix unitaire (DT)</th>
                            <th>Quantité</th>
                            <th>Total (DT)</th>
                        </tr>
                    </thead>
                    <tbody>
        `;
        
        data.produits.forEach(p => {
            html += `
                <tr>
                    <td>${p.nom}</td>
                    <td>${typeof p.prix_ht === 'number' ? p.prix_ht.toFixed(3) : p.prix_ht}</td>
                    <td>${p.quantite}</td>
                    <td>${typeof p.total === 'number' ? p.total.toFixed(3) : (p.prix_ht * p.quantite).toFixed(3)}</td>
                </tr>
            `;
        });
        
        html += `
                    </tbody>
                </table>
            </div>
            
            <div class="totals">
                <p><strong>Total HT:</strong> ${total_ht.toFixed(3)} DT</p>
                <p><strong>TVA (19%):</strong> ${tva.toFixed(3)} DT</p>
                <p><strong>Timbre fiscal:</strong> 1.000 DT</p>
                <p class="total-ttc"><strong>Total TTC:</strong> ${total_ttc.toFixed(3)} DT</p>
            </div>
            
            <div class="text-center mt-3">
                <button id="confirm-invoice" class="btn btn-primary">Générer la facture PDF</button>
            </div>
        `;
        
        // Mettre à jour les données extraites complètes pour la génération du PDF
        extractedData = data.raw_data || data;
        
        // Afficher l'aperçu
        previewContent.innerHTML = html;
        previewDiv.classList.remove('d-none');
        
        // Réattacher l'événement au nouveau bouton
        document.getElementById('confirm-invoice').addEventListener('click', generatePDF);
    }
    
    // Fonction pour générer le PDF
    function generatePDF() {
        if (!extractedData) {
            errorMessage.textContent = "Données manquantes pour générer la facture";
            errorMessage.classList.remove('d-none');
            return;
        }
        
        const confirmBtn = document.getElementById('confirm-invoice');
        confirmBtn.disabled = true;
        confirmBtn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Génération...';
        
        fetch('/api/generate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(extractedData)
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Afficher le message de succès
                downloadLink.href = data.download_url;
                successMessage.classList.remove('d-none');
            } else {
                errorMessage.textContent = data.error || "Une erreur s'est produite lors de la génération du PDF";
                errorMessage.classList.remove('d-none');
            }
        })
        .catch(err => {
            errorMessage.textContent = "Erreur de communication avec le serveur";
            errorMessage.classList.remove('d-none');
        })
        .finally(() => {
            confirmBtn.disabled = false;
            confirmBtn.textContent = "Générer la facture PDF";
        });
    }
    
    // Si le bouton confirmBtn existe déjà dans le HTML initial
    if (confirmBtn) {
        confirmBtn.addEventListener('click', generatePDF);
    }
});