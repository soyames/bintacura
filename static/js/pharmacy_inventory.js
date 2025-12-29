window.openAddMedicationModal = function() {
    console.log('openAddMedicationModal called');
    const modal = document.getElementById('addMedicationModal');
    console.log('Modal element:', modal);
    console.log('Modal classes before:', modal.className);
    modal.classList.add('show');
    console.log('Modal classes after:', modal.className);
    console.log('Modal display style:', window.getComputedStyle(modal).display);
};

window.closeAddMedicationModal = function() {
    console.log('closeAddMedicationModal called');
    const modal = document.getElementById('addMedicationModal');
    modal.classList.remove('show');
    document.getElementById('newMedicationForm').reset();
    document.getElementById('existingMedicationForm').reset();
};

window.switchTab = function(tab) {
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');

    tabBtns.forEach(btn => btn.classList.remove('active'));
    tabContents.forEach(content => content.classList.remove('active'));

    if (tab === 'new') {
        tabBtns[0].classList.add('active');
        document.getElementById('newMedicationForm').classList.add('active');
    } else {
        tabBtns[1].classList.add('active');
        document.getElementById('existingMedicationForm').classList.add('active');
    }
};

window.loadMedicationDetails = function(medicationId) {
    if (!medicationId) {
        document.getElementById('medicationDetails').innerHTML = '';
        const form = document.getElementById('existingMedicationForm');
        if (form) {
            form.querySelector('[name="manufacturer"]').value = '';
        }
        return;
    }

    const medications = window.allMedications || [];
    const medication = medications.find(m => m.id == medicationId);

    if (medication) {
        const detailsHtml = `
            <div class="info-box" style="background: #f0fdf4; border-left: 4px solid #10b981; padding: 15px; margin: 15px 0; border-radius: 8px;">
                <p style="margin: 5px 0;"><strong>Nom:</strong> ${medication.name}</p>
                <p style="margin: 5px 0;"><strong>Nom générique:</strong> ${medication.generic_name || 'N/A'}</p>
                <p style="margin: 5px 0;"><strong>Catégorie:</strong> ${medication.category || 'N/A'}</p>
                <p style="margin: 5px 0;"><strong>Description:</strong> ${medication.description || 'N/A'}</p>
                ${medication.manufacturer ? `<p style="margin: 5px 0;"><strong>Fabricant:</strong> ${medication.manufacturer}</p>` : ''}
                ${medication.requires_prescription !== undefined ? `<p style="margin: 5px 0;"><strong>Ordonnance requise:</strong> ${medication.requires_prescription ? 'Oui' : 'Non'}</p>` : ''}
            </div>
        `;
        document.getElementById('medicationDetails').innerHTML = detailsHtml;

        const form = document.getElementById('existingMedicationForm');
        if (form && medication.manufacturer) {
            const manufacturerInput = form.querySelector('[name="manufacturer"]');
            if (manufacturerInput) {
                manufacturerInput.value = medication.manufacturer;
            }
        }
    }
};

window.onclick = function(event) {
    const modal = document.getElementById('addMedicationModal');
    if (event.target === modal) {
        window.closeAddMedicationModal();
    }
};

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// Product action functions
window.viewProduct = async function(id) {
    try {
        const response = await fetch(`/api/v1/pharmacy/inventory/${id}/`, {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            },
            credentials: 'same-origin'
        });
        const data = await response.json();

        if (data.success && data.item) {
            const item = data.item;
            const modal = `
                <div style="position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.6); z-index: 9999; display: flex; align-items: center; justify-content: center; padding: 20px;" onclick="this.remove()">
                    <div style="background: white; padding: 30px; border-radius: 16px; max-width: 700px; width: 100%; max-height: 90vh; overflow-y: auto;" onclick="event.stopPropagation()">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px;">
                            <h2 style="margin: 0; color: #10b981;">📦 ${item.medication?.name || 'Détails du Produit'}</h2>
                            <button onclick="this.parentElement.parentElement.parentElement.remove()" style="background: none; border: none; font-size: 28px; cursor: pointer; color: #6b7280;">&times;</button>
                        </div>

                        <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px;">
                            <div>
                                <div style="font-size: 12px; color: #6b7280; margin-bottom: 4px;">Nom Générique</div>
                                <div style="font-weight: 600;">${item.medication?.generic_name || 'N/A'}</div>
                            </div>
                            <div>
                                <div style="font-size: 12px; color: #6b7280; margin-bottom: 4px;">Catégorie</div>
                                <div style="font-weight: 600;">${item.medication?.category || 'N/A'}</div>
                            </div>
                            <div>
                                <div style="font-size: 12px; color: #6b7280; margin-bottom: 4px;">Numéro de Lot</div>
                                <div style="font-weight: 600;">${item.batch_number || 'N/A'}</div>
                            </div>
                            <div>
                                <div style="font-size: 12px; color: #6b7280; margin-bottom: 4px;">Quantité en Stock</div>
                                <div style="font-weight: 600; color: #10b981; font-size: 18px;">${item.quantity_in_stock} unités</div>
                            </div>
                            <div>
                                <div style="font-size: 12px; color: #6b7280; margin-bottom: 4px;">Prix Unitaire</div>
                                <div style="font-weight: 600;">${item.unit_price} FCFA</div>
                            </div>
                            <div>
                                <div style="font-size: 12px; color: #6b7280; margin-bottom: 4px;">Prix de Vente</div>
                                <div style="font-weight: 600;">${item.selling_price} FCFA</div>
                            </div>
                            <div>
                                <div style="font-size: 12px; color: #6b7280; margin-bottom: 4px;">Valeur Totale</div>
                                <div style="font-weight: 700; color: #059669; font-size: 18px;">${(item.quantity_in_stock * item.unit_price).toLocaleString()} FCFA</div>
                            </div>
                            <div>
                                <div style="font-size: 12px; color: #6b7280; margin-bottom: 4px;">Seuil de Réapprovisionnement</div>
                                <div style="font-weight: 600;">${item.reorder_level || 'N/A'}</div>
                            </div>
                            <div>
                                <div style="font-size: 12px; color: #6b7280; margin-bottom: 4px;">Fabricant</div>
                                <div style="font-weight: 600;">${item.manufacturer || 'N/A'}</div>
                            </div>
                            <div>
                                <div style="font-size: 12px; color: #6b7280; margin-bottom: 4px;">Emplacement</div>
                                <div style="font-weight: 600;">${item.storage_location || 'N/A'}</div>
                            </div>
                            <div>
                                <div style="font-size: 12px; color: #6b7280; margin-bottom: 4px;">Date d'Expiration</div>
                                <div style="font-weight: 600;">${item.expiry_date || 'N/A'}</div>
                            </div>
                            <div>
                                <div style="font-size: 12px; color: #6b7280; margin-bottom: 4px;">Disponibilité Publique</div>
                                <div style="font-weight: 600;">${item.is_publicly_available ? '✓ Oui' : '✗ Non'}</div>
                            </div>
                        </div>

                        <div style="margin-top: 24px; display: flex; gap: 12px;">
                            <button onclick="this.parentElement.parentElement.parentElement.remove(); window.editProduct('${id}');" style="flex: 1; padding: 12px; background: #3b82f6; color: white; border: none; border-radius: 8px; font-weight: 600; cursor: pointer;">
                                ✏️ Modifier
                            </button>
                            <button onclick="this.parentElement.parentElement.parentElement.remove(); window.restockProduct('${id}');" style="flex: 1; padding: 12px; background: #10b981; color: white; border: none; border-radius: 8px; font-weight: 600; cursor: pointer;">
                                📦 Réapprovisionner
                            </button>
                        </div>
                    </div>
                </div>
            `;
            document.body.insertAdjacentHTML('beforeend', modal);
        }
    } catch (error) {
        console.error('Error viewing product:', error);
        alert('Erreur lors du chargement des détails du produit');
    }
};

window.editProduct = async function(id) {
    try {
        const response = await fetch(`/api/v1/pharmacy/inventory/${id}/`, {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            },
            credentials: 'same-origin'
        });
        const data = await response.json();

        if (data.success && data.item) {
            const item = data.item;
            const modal = `
                <div style="position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.6); z-index: 9999; display: flex; align-items: center; justify-content: center; padding: 20px;" onclick="if(event.target === this) this.remove()">
                    <div style="background: white; padding: 30px; border-radius: 16px; max-width: 700px; width: 100%; max-height: 90vh; overflow-y: auto;" onclick="event.stopPropagation()">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px;">
                            <h2 style="margin: 0; color: #3b82f6;">✏️ Modifier le Produit</h2>
                            <button onclick="this.parentElement.parentElement.parentElement.remove()" style="background: none; border: none; font-size: 28px; cursor: pointer; color: #6b7280;">&times;</button>
                        </div>

                        <form id="editProductForm" onsubmit="window.submitEdit(event, '${id}')">
                            <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px;">
                                <div>
                                    <label style="display: block; margin-bottom: 5px; font-weight: 600; font-size: 14px;">Quantité en Stock</label>
                                    <input type="number" id="edit_quantity" value="${item.quantity_in_stock}" required style="width: 100%; padding: 10px; border: 2px solid #e5e7eb; border-radius: 8px;">
                                </div>
                                <div>
                                    <label style="display: block; margin-bottom: 5px; font-weight: 600; font-size: 14px;">Prix Unitaire (FCFA)</label>
                                    <input type="number" id="edit_unit_price" value="${item.unit_price}" required style="width: 100%; padding: 10px; border: 2px solid #e5e7eb; border-radius: 8px;">
                                </div>
                                <div>
                                    <label style="display: block; margin-bottom: 5px; font-weight: 600; font-size: 14px;">Prix de Vente (FCFA)</label>
                                    <input type="number" id="edit_selling_price" value="${item.selling_price}" required style="width: 100%; padding: 10px; border: 2px solid #e5e7eb; border-radius: 8px;">
                                </div>
                                <div>
                                    <label style="display: block; margin-bottom: 5px; font-weight: 600; font-size: 14px;">Seuil de Réapprovisionnement</label>
                                    <input type="number" id="edit_reorder_level" value="${item.reorder_level || 10}" style="width: 100%; padding: 10px; border: 2px solid #e5e7eb; border-radius: 8px;">
                                </div>
                                <div>
                                    <label style="display: block; margin-bottom: 5px; font-weight: 600; font-size: 14px;">Numéro de Lot</label>
                                    <input type="text" id="edit_batch_number" value="${item.batch_number || ''}" style="width: 100%; padding: 10px; border: 2px solid #e5e7eb; border-radius: 8px;">
                                </div>
                                <div>
                                    <label style="display: block; margin-bottom: 5px; font-weight: 600; font-size: 14px;">Date d'Expiration</label>
                                    <input type="date" id="edit_expiry_date" value="${item.expiry_date || ''}" style="width: 100%; padding: 10px; border: 2px solid #e5e7eb; border-radius: 8px;">
                                </div>
                                <div style="grid-column: 1 / -1;">
                                    <label style="display: block; margin-bottom: 5px; font-weight: 600; font-size: 14px;">Emplacement de Stockage</label>
                                    <input type="text" id="edit_storage_location" value="${item.storage_location || ''}" style="width: 100%; padding: 10px; border: 2px solid #e5e7eb; border-radius: 8px;">
                                </div>
                                <div style="grid-column: 1 / -1;">
                                    <label style="display: flex; align-items: center; cursor: pointer;">
                                        <input type="checkbox" id="edit_is_publicly_available" ${item.is_publicly_available ? 'checked' : ''} style="margin-right: 8px; width: 18px; height: 18px; cursor: pointer;">
                                        <span style="font-weight: 600;">Disponible publiquement</span>
                                    </label>
                                </div>
                            </div>

                            <div style="margin-top: 24px; display: flex; gap: 12px;">
                                <button type="button" onclick="this.closest('form').parentElement.parentElement.remove()" style="flex: 1; padding: 12px; border: 2px solid #e5e7eb; background: white; border-radius: 8px; font-weight: 600; cursor: pointer;">Annuler</button>
                                <button type="submit" style="flex: 1; padding: 12px; background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%); color: white; border: none; border-radius: 8px; font-weight: 600; cursor: pointer;">Enregistrer</button>
                            </div>
                        </form>
                    </div>
                </div>
            `;
            document.body.insertAdjacentHTML('beforeend', modal);
        }
    } catch (error) {
        console.error('Error loading product:', error);
        alert('Erreur lors du chargement du produit');
    }
};

window.submitEdit = async function(event, productId) {
    event.preventDefault();

    const formData = {
        quantity_in_stock: document.getElementById('edit_quantity').value,
        unit_price: document.getElementById('edit_unit_price').value,
        selling_price: document.getElementById('edit_selling_price').value,
        reorder_level: document.getElementById('edit_reorder_level').value,
        batch_number: document.getElementById('edit_batch_number').value,
        expiry_date: document.getElementById('edit_expiry_date').value,
        storage_location: document.getElementById('edit_storage_location').value,
        is_publicly_available: document.getElementById('edit_is_publicly_available').checked
    };

    try {
        const response = await fetch(`/api/v1/pharmacy/inventory/${productId}/`, {
            method: 'PATCH',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            credentials: 'same-origin',
            body: JSON.stringify(formData)
        });

        const data = await response.json();

        if (data.success) {
            alert('✓ Produit mis à jour avec succès!');
            document.querySelector('div[style*="position: fixed"]')?.remove();
            location.reload();
        } else {
            alert('Erreur lors de la mise à jour');
        }
    } catch (error) {
        console.error('Error updating product:', error);
        alert('Erreur lors de la mise à jour');
    }
};

window.restockProduct = function(id) {
    const restockModal = `
        <div style="position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.6); z-index: 9999; display: flex; align-items: center; justify-content: center;" onclick="if(event.target === this) this.remove()">
            <div style="background: white; padding: 30px; border-radius: 16px; max-width: 500px; width: 90%;" onclick="event.stopPropagation()">
                <h3 style="margin: 0 0 20px 0; color: #10b981;">📦 Réapprovisionner le Produit</h3>
                <form id="restockForm" onsubmit="window.submitRestock(event, '${id}')">
                    <div style="margin-bottom: 15px;">
                        <label style="display: block; margin-bottom: 5px; font-weight: 600;">Quantité à ajouter *</label>
                        <input type="number" id="restockQty" min="1" required style="width: 100%; padding: 10px; border: 2px solid #e5e7eb; border-radius: 8px;">
                    </div>
                    <div style="margin-bottom: 15px;">
                        <label style="display: block; margin-bottom: 5px; font-weight: 600;">Numéro de lot</label>
                        <input type="text" id="batchNumber" style="width: 100%; padding: 10px; border: 2px solid #e5e7eb; border-radius: 8px;">
                    </div>
                    <div style="margin-bottom: 15px;">
                        <label style="display: block; margin-bottom: 5px; font-weight: 600;">Date d'expiration</label>
                        <input type="date" id="expiryDate" style="width: 100%; padding: 10px; border: 2px solid #e5e7eb; border-radius: 8px;">
                    </div>
                    <div style="margin-bottom: 20px;">
                        <label style="display: block; margin-bottom: 5px; font-weight: 600;">Fournisseur</label>
                        <input type="text" id="supplier" style="width: 100%; padding: 10px; border: 2px solid #e5e7eb; border-radius: 8px;">
                    </div>
                    <div style="display: flex; gap: 10px;">
                        <button type="button" onclick="this.closest('div[style*=fixed]').remove()" style="flex: 1; padding: 12px; border: 2px solid #e5e7eb; background: white; border-radius: 8px; font-weight: 600; cursor: pointer;">Annuler</button>
                        <button type="submit" style="flex: 1; padding: 12px; background: linear-gradient(135deg, #10b981 0%, #059669 100%); color: white; border: none; border-radius: 8px; font-weight: 600; cursor: pointer;">Réapprovisionner</button>
                    </div>
                </form>
            </div>
        </div>
    `;
    document.body.insertAdjacentHTML('beforeend', restockModal);
};

window.submitRestock = async function(event, productId) {
    event.preventDefault();

    const formData = {
        quantity: document.getElementById('restockQty').value,
        batch_number: document.getElementById('batchNumber').value,
        expiry_date: document.getElementById('expiryDate').value,
        supplier: document.getElementById('supplier').value
    };

    try {
        const response = await fetch(`/api/v1/pharmacy/inventory/${productId}/restock/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            credentials: 'same-origin',
            body: JSON.stringify(formData)
        });

        const data = await response.json();

        if (data.success) {
            alert(`✓ ${data.message}\nNouvelle quantité: ${data.new_quantity} unités`);
            document.querySelector('div[style*="position: fixed"]')?.remove();
            location.reload();
        } else {
            alert(data.error || 'Erreur lors du réapprovisionnement');
        }
    } catch (error) {
        console.error('Error restocking:', error);
        alert('Erreur lors du réapprovisionnement');
    }
};

// Excel export function
window.exportInventoryExcel = function() {
    window.location.href = '/api/v1/pharmacy/inventory/export_inventory/';
};

// Tab switching functionality
window.switchView = function(view) {
    const tabs = document.querySelectorAll('.tab-button');
    tabs.forEach(tab => {
        if (tab.dataset.tab === view) {
            tab.classList.add('active');
        } else {
            tab.classList.remove('active');
        }
    });

    const gridView = document.getElementById('gridView');
    const tableView = document.getElementById('tableView');
    const toolbar = document.querySelector('.inventory-toolbar');

    if (gridView) gridView.style.display = 'none';
    if (tableView) tableView.style.display = 'none';

    switch(view) {
        case 'overview':
            const currentViewMode = document.getElementById('viewMode')?.value || 'grid';
            if (currentViewMode === 'grid') {
                if (gridView) gridView.style.display = 'grid';
            } else {
                if (tableView) tableView.style.display = 'block';
            }
            if (toolbar) toolbar.style.display = 'block';
            break;

        case 'stock':
            if (gridView) gridView.style.display = 'grid';
            if (toolbar) toolbar.style.display = 'block';
            showStockStatusView();
            break;

        case 'expiry':
            if (tableView) tableView.style.display = 'block';
            if (toolbar) toolbar.style.display = 'none';
            showExpiryView();
            break;

        case 'movements':
            if (tableView) tableView.style.display = 'block';
            if (toolbar) toolbar.style.display = 'none';
            showMovementsView();
            break;

        case 'analytics':
            if (gridView) gridView.style.display = 'grid';
            if (toolbar) toolbar.style.display = 'none';
            showAnalyticsView();
            break;
    }
};

function showStockStatusView() {
    const gridView = document.getElementById('gridView');
    const allProducts = document.querySelectorAll('.product-card, .table-modern tbody tr');
    allProducts.forEach(product => {
        product.style.display = '';
    });

    gridView.innerHTML = `
        <div style="grid-column: 1 / -1; display: flex; flex-direction: column; gap: 24px;">
            <div style="background: white; padding: 24px; border-radius: 16px; box-shadow: 0 2px 8px rgba(0,0,0,0.08);">
                <h3 style="margin: 0 0 20px 0; font-size: 20px; color: #10b981;">📊 État des Stocks</h3>

                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 16px; margin-bottom: 24px;">
                    <div onclick="filterStockByLevel('in')" style="background: linear-gradient(135deg, rgba(16, 185, 129, 0.1) 0%, rgba(5, 150, 105, 0.1) 100%); padding: 20px; border-radius: 12px; border-left: 4px solid #10b981; cursor: pointer; transition: all 0.3s;">
                        <div style="font-size: 32px; font-weight: 700; color: #10b981;">En Stock</div>
                        <div style="font-size: 12px; color: #10b981; margin-top: 8px;">✓ Stock Suffisant</div>
                    </div>

                    <div onclick="filterStockByLevel('low')" style="background: linear-gradient(135deg, rgba(251, 191, 36, 0.1) 0%, rgba(245, 158, 11, 0.1) 100%); padding: 20px; border-radius: 12px; border-left: 4px solid #fbbf24; cursor: pointer; transition: all 0.3s;">
                        <div style="font-size: 32px; font-weight: 700; color: #f59e0b;">Stock Faible</div>
                        <div style="font-size: 12px; color: #f59e0b; margin-top: 8px;">⚠ Réapprovisionner</div>
                    </div>

                    <div onclick="filterStockByLevel('out')" style="background: linear-gradient(135deg, rgba(239, 68, 68, 0.1) 0%, rgba(220, 38, 38, 0.1) 100%); padding: 20px; border-radius: 12px; border-left: 4px solid #ef4444; cursor: pointer; transition: all 0.3s;">
                        <div style="font-size: 32px; font-weight: 700; color: #ef4444;">Rupture</div>
                        <div style="font-size: 12px; color: #ef4444; margin-top: 8px;">⛔ Action Urgente</div>
                    </div>
                </div>

                <button onclick="switchView('overview')" style="padding: 12px 24px; background: #10b981; color: white; border: none; border-radius: 8px; font-weight: 600; cursor: pointer;">
                    Retour à la Vue Principale
                </button>
            </div>
        </div>
    `;
}

function filterStockByLevel(level) {
    window.switchView('overview');
    document.getElementById('stockFilter').value = level;
    document.getElementById('stockFilter').dispatchEvent(new Event('change'));
}

function showExpiryView() {
    const tableView = document.getElementById('tableView');
    tableView.innerHTML = `
        <div style="background: white; padding: 24px; border-radius: 16px; box-shadow: 0 2px 8px rgba(0,0,0,0.08);">
            <h3 style="margin: 0 0 20px 0; font-size: 20px; color: #10b981;">📅 Dates d'Expiration</h3>
            <p>Chargement des données d'expiration...</p>
            <button onclick="switchView('overview')" style="padding: 12px 24px; background: #10b981; color: white; border: none; border-radius: 8px; font-weight: 600; cursor: pointer; margin-top: 20px;">
                Retour à la Vue Principale
            </button>
        </div>
    `;
}

function showMovementsView() {
    const tableView = document.getElementById('tableView');
    tableView.innerHTML = `
        <div style="background: white; padding: 24px; border-radius: 16px; box-shadow: 0 2px 8px rgba(0,0,0,0.08);">
            <h3 style="margin: 0 0 20px 0; font-size: 20px; color: #10b981;">📦 Mouvements de Stock</h3>
            <p>Chargement des mouvements de stock...</p>
            <button onclick="switchView('overview')" style="padding: 12px 24px; background: #10b981; color: white; border: none; border-radius: 8px; font-weight: 600; cursor: pointer; margin-top: 20px;">
                Retour à la Vue Principale
            </button>
        </div>
    `;
}

function showAnalyticsView() {
    const gridView = document.getElementById('gridView');
    gridView.innerHTML = `
        <div style="grid-column: 1 / -1; display: flex; flex-direction: column; gap: 24px;">
            <div style="background: white; padding: 24px; border-radius: 16px; box-shadow: 0 2px 8px rgba(0,0,0,0.08);">
                <h3 style="margin: 0 0 20px 0; font-size: 20px; color: #10b981;">📈 Analyses & Statistiques</h3>
                <p>Chargement des analyses...</p>
                <button onclick="switchView('overview')" style="padding: 12px 24px; background: #10b981; color: white; border: none; border-radius: 8px; font-weight: 600; cursor: pointer; margin-top: 20px;">
                    Retour à la Vue Principale
                </button>
            </div>
        </div>
    `;
}

// View mode switcher
window.changeViewMode = function(mode) {
    const gridView = document.getElementById('gridView');
    const tableView = document.getElementById('tableView');

    if (mode === 'grid') {
        gridView.style.display = 'grid';
        tableView.style.display = 'none';
    } else {
        gridView.style.display = 'none';
        tableView.style.display = 'block';
    }
};

document.addEventListener('DOMContentLoaded', function() {
    const searchInput = document.getElementById('searchInput');
    const stockFilter = document.getElementById('stockFilter');
    const tableRows = document.querySelectorAll('tbody tr');

    function filterTable() {
        const searchTerm = searchInput.value.toLowerCase();
        const stockStatus = stockFilter.value;

        tableRows.forEach(row => {
            const name = row.dataset.name;
            const status = row.dataset.status;

            const matchesSearch = name.includes(searchTerm);
            const matchesStock = !stockStatus || status === stockStatus;

            row.style.display = matchesSearch && matchesStock ? '' : 'none';
        });
    }

    if (searchInput) {
        searchInput.addEventListener('input', filterTable);
    }

    if (stockFilter) {
        stockFilter.addEventListener('change', filterTable);
    }

    const newMedicationForm = document.getElementById('newMedicationForm');
    if (newMedicationForm) {
        newMedicationForm.addEventListener('submit', async function(e) {
            e.preventDefault();

            const formData = new FormData(this);
            const data = {
                action: 'add_medication',
                name: formData.get('name'),
                generic_name: formData.get('generic_name'),
                brand_name: formData.get('brand_name'),
                category: formData.get('category'),
                description: formData.get('description'),
                manufacturer: formData.get('manufacturer'),
                dosage_form: formData.get('dosage_form'),
                strength: formData.get('strength'),
                side_effects: formData.get('side_effects'),
                contraindications: formData.get('contraindications'),
                requires_prescription: formData.get('requires_prescription') === 'on',
                is_controlled_substance: formData.get('is_controlled_substance') === 'on',
                batch_number: formData.get('batch_number'),
                quantity_in_stock: parseInt(formData.get('quantity_in_stock')) || 0,
                unit_price: parseInt(formData.get('unit_price')) || 0,
                selling_price: parseInt(formData.get('selling_price')) || 0,
                manufacturing_date: formData.get('manufacturing_date'),
                expiry_date: formData.get('expiry_date'),
                reorder_level: parseInt(formData.get('reorder_level')) || 10,
                storage_location: formData.get('storage_location'),
                requires_refrigeration: formData.get('requires_refrigeration') === 'on',
                is_publicly_available: formData.get('is_publicly_available') === 'on'
            };

            try {
                const response = await fetch('/pharmacy/inventory/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCookie('csrftoken')
                    },
                    body: JSON.stringify(data)
                });

                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }

                const result = await response.json();

                if (result.success) {
                    alert('✓ Médicament ajouté avec succès!');
                    window.closeAddMedicationModal();
                    window.location.reload();
                } else {
                    alert('Erreur: ' + (result.error || result.message || 'Erreur inconnue'));
                }
            } catch (error) {
                console.error('Error adding medication:', error);
                alert('Erreur lors de l\'ajout du médicament: ' + (error.message || 'Erreur inconnue'));
            }
        });
    }

    const existingMedicationForm = document.getElementById('existingMedicationForm');
    if (existingMedicationForm) {
        existingMedicationForm.addEventListener('submit', async function(e) {
            e.preventDefault();

            const formData = new FormData(this);
            const data = {
                action: 'add_to_inventory',
                medication_id: formData.get('medication_id'),
                batch_number: formData.get('batch_number'),
                quantity_in_stock: parseInt(formData.get('quantity_in_stock')) || 0,
                unit_price: parseInt(formData.get('unit_price')) || 0,
                selling_price: parseInt(formData.get('selling_price')) || 0,
                manufacturer: formData.get('manufacturer'),
                manufacturing_date: formData.get('manufacturing_date'),
                expiry_date: formData.get('expiry_date'),
                reorder_level: parseInt(formData.get('reorder_level')) || 10,
                storage_location: formData.get('storage_location'),
                requires_refrigeration: formData.get('requires_refrigeration') === 'on',
                is_publicly_available: formData.get('is_publicly_available') === 'on'
            };

            try {
                const response = await fetch('/pharmacy/inventory/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCookie('csrftoken')
                    },
                    body: JSON.stringify(data)
                });

                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }

                const result = await response.json();

                if (result.success) {
                    alert('✓ Médicament ajouté à l\'inventaire avec succès!');
                    window.closeAddMedicationModal();
                    window.location.reload();
                } else {
                    alert('Erreur: ' + (result.error || result.message || 'Erreur inconnue'));
                }
            } catch (error) {
                console.error('Error adding to inventory:', error);
                alert('Erreur lors de l\'ajout à l\'inventaire: ' + (error.message || 'Erreur inconnue'));
            }
        });
    }
});
