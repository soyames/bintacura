// BINTACURA Translation System
// Automatically translates page content based on user's selected language

// Debug logging
console.log('🌍 BINTACURA Translation System Loading...');

const translations = {
    en: {
        // Navigation & Menu
        "Tableau de bord": "Dashboard",
        "Mon Profil": "My Profile",
        "Paramètres": "Settings",
        "Déconnexion": "Logout",
        "Mes Rendez-vous": "My Appointments",
        "Mes Prescriptions": "My Prescriptions",
        "Dossier Médical": "Medical Records",
        "Mon Portefeuille": "My Wallet",
        "Rendez-vous": "Appointments",
        "Prescriptions": "Prescriptions",
        "Patients": "Patients",
        "Consultations": "Consultations",
        "Horaires": "Schedule",
        "Services": "Services",
        "Analytiques": "Analytics",
        "Rapports": "Reports",
        "Accueil": "Home",
        "Menu": "Menu",
        "Navigation": "Navigation",
        "Retour au tableau de bord": "Back to Dashboard",
        "Voir tout": "View All",
        "Notifications": "Notifications",
        
        // Dashboard
        "Bienvenue": "Welcome",
        "Aperçu": "Overview",
        "Statistiques": "Statistics",
        "Activités Récentes": "Recent Activities",
        "Prochains Rendez-vous": "Upcoming Appointments",
        "Aujourd'hui": "Today",
        "Cette semaine": "This Week",
        "Ce mois": "This Month",
        "Résumé": "Summary",
        "Vue d'ensemble": "Overview",
        "Dernières activités": "Recent Activities",
        "Activité récente": "Recent Activity",
        
        // Appointments
        "Nouveau Rendez-vous": "New Appointment",
        "Prendre Rendez-vous": "Book Appointment",
        "Prendre un rendez-vous": "Book an Appointment",
        "Réserver": "Book",
        "Annuler": "Cancel",
        "Annuler le rendez-vous": "Cancel Appointment",
        "Confirmer": "Confirm",
        "Confirmer le rendez-vous": "Confirm Appointment",
        "Reprogrammer": "Reschedule",
        "Reprogrammer le rendez-vous": "Reschedule Appointment",
        "En attente": "Pending",
        "Confirmé": "Confirmed",
        "Complété": "Completed",
        "Terminé": "Completed",
        "Annulé": "Cancelled",
        "Date": "Date",
        "Heure": "Time",
        "Médecin": "Doctor",
        "Patient": "Patient",
        "Raison": "Reason",
        "Motif": "Reason",
        "Statut": "Status",
        "Actions": "Actions",
        "Détails du rendez-vous": "Appointment Details",
        "Type de consultation": "Consultation Type",
        "Durée": "Duration",
        "Lieu": "Location",
        
        // Profile & Settings
        "Informations Personnelles": "Personal Information",
        "Informations personnelles": "Personal information",
        "Nom Complet": "Full Name",
        "Nom complet": "Full name",
        "Nom": "Name",
        "Prénom": "First Name",
        "Nom de famille": "Last Name",
        "Email": "Email",
        "Adresse e-mail": "Email Address",
        "Téléphone": "Phone",
        "Numéro de téléphone": "Phone Number",
        "Adresse": "Address",
        "Ville": "City",
        "Code postal": "Postal Code",
        "Pays": "Country",
        "Date de Naissance": "Date of Birth",
        "Date de naissance": "Date of birth",
        "Âge": "Age",
        "Genre": "Gender",
        "Sexe": "Sex",
        "Homme": "Male",
        "Femme": "Female",
        "Autre": "Other",
        "Enregistrer": "Save",
        "Sauvegarder": "Save",
        "Modifier": "Edit",
        "Éditer": "Edit",
        "Langue": "Language",
        "Français": "French",
        "Anglais": "English",
        "Préférences": "Preferences",
        "Sécurité": "Security",
        "Confidentialité": "Privacy",
        "Mot de passe": "Password",
        "Changer le mot de passe": "Change Password",
        "Ancien mot de passe": "Old Password",
        "Nouveau mot de passe": "New Password",
        "Confirmer le mot de passe": "Confirm Password",
        
        // Medical Terms
        "Diagnostic": "Diagnosis",
        "Diagnostics": "Diagnoses",
        "Traitement": "Treatment",
        "Traitements": "Treatments",
        "Médicaments": "Medications",
        "Médicament": "Medication",
        "Allergies": "Allergies",
        "Allergie": "Allergy",
        "Antécédents": "Medical History",
        "Antécédents médicaux": "Medical History",
        "Historique médical": "Medical History",
        "Symptômes": "Symptoms",
        "Symptôme": "Symptom",
        "Notes": "Notes",
        "Note": "Note",
        "Ordonnance": "Prescription",
        "Ordonnances": "Prescriptions",
        "Posologie": "Dosage",
        "Dosage": "Dosage",
        "Dose": "Dose",
        "Fréquence": "Frequency",
        "Instructions": "Instructions",
        "Contre-indications": "Contraindications",
        "Effets secondaires": "Side Effects",
        "Résultats": "Results",
        "Analyses": "Tests",
        "Examen": "Examination",
        "Examens": "Examinations",
        "Laboratoire": "Laboratory",
        "Radiologie": "Radiology",
        
        // Financial
        "Solde": "Balance",
        "Solde actuel": "Current Balance",
        "Transactions": "Transactions",
        "Transaction": "Transaction",
        "Paiement": "Payment",
        "Paiements": "Payments",
        "Montant": "Amount",
        "Recharger": "Top Up",
        "Recharge": "Top Up",
        "Historique": "History",
        "Historique des transactions": "Transaction History",
        "Facture": "Invoice",
        "Factures": "Invoices",
        "Facturation": "Billing",
        "Payé": "Paid",
        "Impayé": "Unpaid",
        "En attente de paiement": "Pending Payment",
        "Gratuit": "Free",
        "Coût": "Cost",
        "Frais": "Fees",
        "Total": "Total",
        "Sous-total": "Subtotal",
        "Taxe": "Tax",
        "Taxes": "Taxes",
        "Remboursement": "Refund",
        "Carte bancaire": "Credit Card",
        "Espèces": "Cash",
        "Virement": "Transfer",
        
        // Pharmacy
        "Pharmacie": "Pharmacy",
        "Pharmacies": "Pharmacies",
        "Médicament": "Medication",
        "Médicaments": "Medications",
        "Stock": "Stock",
        "En stock": "In Stock",
        "Inventaire": "Inventory",
        "Commandes": "Orders",
        "Commande": "Order",
        "Commander": "Order",
        "Ventes": "Sales",
        "Vente": "Sale",
        "Fournisseurs": "Suppliers",
        "Fournisseur": "Supplier",
        "Prix": "Price",
        "Prix unitaire": "Unit Price",
        "Quantité": "Quantity",
        "Disponible": "Available",
        "Non disponible": "Unavailable",
        "Rupture de stock": "Out of Stock",
        "Réapprovisionner": "Restock",
        "Catalogue": "Catalog",
        "Référence": "Reference",
        "Code barre": "Barcode",
        "Expiration": "Expiration",
        "Date d'expiration": "Expiration Date",
        "Périmé": "Expired",
        
        // Hospital
        "Hôpital": "Hospital",
        "Hôpitaux": "Hospitals",
        "Département": "Department",
        "Départements": "Departments",
        "Service": "Ward",
        "Personnel": "Staff",
        "Médecins": "Doctors",
        "Infirmiers": "Nurses",
        "Infirmière": "Nurse",
        "Lits": "Beds",
        "Lit": "Bed",
        "Admissions": "Admissions",
        "Admission": "Admission",
        "Sortie": "Discharge",
        "Urgences": "Emergency",
        "Salle d'urgence": "Emergency Room",
        "Chirurgie": "Surgery",
        "Opération": "Operation",
        "Bloc opératoire": "Operating Room",
        "Soins intensifs": "Intensive Care",
        "Réanimation": "ICU",
        "Hospitalisation": "Hospitalization",
        "Ambulatoire": "Outpatient",
        "Consultation externe": "Outpatient Consultation",
        
        // Insurance
        "Assurance": "Insurance",
        "Assurance maladie": "Health Insurance",
        "Police": "Policy",
        "Police d'assurance": "Insurance Policy",
        "Réclamation": "Claim",
        "Réclamations": "Claims",
        "Demande": "Request",
        "Membres": "Members",
        "Membre": "Member",
        "Adhérent": "Subscriber",
        "Couverture": "Coverage",
        "Garantie": "Guarantee",
        "Prime": "Premium",
        "Cotisation": "Contribution",
        "Bénéficiaire": "Beneficiary",
        "Bénéficiaires": "Beneficiaries",
        "Remboursement": "Reimbursement",
        "Plafond": "Limit",
        "Franchise": "Deductible",
        
        // Forms & Actions
        "Rechercher": "Search",
        "Recherche": "Search",
        "Filtrer": "Filter",
        "Filtre": "Filter",
        "Filtres": "Filters",
        "Trier": "Sort",
        "Trier par": "Sort by",
        "Exporter": "Export",
        "Importer": "Import",
        "Imprimer": "Print",
        "Télécharger": "Download",
        "Téléverser": "Upload",
        "Charger": "Load",
        "Soumettre": "Submit",
        "Envoyer": "Send",
        "Valider": "Validate",
        "Validation": "Validation",
        "Refuser": "Reject",
        "Approuver": "Approve",
        "Approbation": "Approval",
        "Supprimer": "Delete",
        "Effacer": "Delete",
        "Ajouter": "Add",
        "Créer": "Create",
        "Nouveau": "New",
        "Mettre à jour": "Update",
        "Mise à jour": "Update",
        "Actualiser": "Refresh",
        "Partager": "Share",
        "Copier": "Copy",
        "Coller": "Paste",
        "Couper": "Cut",
        
        // Time & Dates
        "Lundi": "Monday",
        "Mardi": "Tuesday",
        "Mercredi": "Wednesday",
        "Jeudi": "Thursday",
        "Vendredi": "Friday",
        "Samedi": "Saturday",
        "Dimanche": "Sunday",
        "Janvier": "January",
        "Février": "February",
        "Mars": "March",
        "Avril": "April",
        "Mai": "May",
        "Juin": "June",
        "Juillet": "July",
        "Août": "August",
        "Septembre": "September",
        "Octobre": "October",
        "Novembre": "November",
        "Décembre": "December",
        "Matin": "Morning",
        "Après-midi": "Afternoon",
        "Soir": "Evening",
        "Nuit": "Night",
        "Heure": "Hour",
        "Minute": "Minute",
        "Seconde": "Second",
        "Jour": "Day",
        "Jours": "Days",
        "Semaine": "Week",
        "Semaines": "Weeks",
        "Mois": "Month",
        "Année": "Year",
        "Années": "Years",
        "Hier": "Yesterday",
        "Demain": "Tomorrow",
        
        // Messages & Status
        "Succès": "Success",
        "Réussi": "Successful",
        "Erreur": "Error",
        "Échec": "Failed",
        "Attention": "Warning",
        "Avertissement": "Warning",
        "Information": "Information",
        "Info": "Info",
        "Êtes-vous sûr?": "Are you sure?",
        "Êtes-vous sûr ?": "Are you sure?",
        "Confirmez-vous ?": "Do you confirm?",
        "Opération réussie": "Operation successful",
        "Succès !": "Success!",
        "Une erreur s'est produite": "An error occurred",
        "Erreur !": "Error!",
        "Chargement...": "Loading...",
        "Chargement en cours...": "Loading...",
        "Veuillez patienter...": "Please wait...",
        "Aucun résultat": "No results",
        "Aucune donnée disponible": "No data available",
        "Aucune information": "No information",
        "Aucun": "None",
        "Aucune": "None",
        "Vide": "Empty",
        "Indisponible": "Unavailable",
        
        // Navigation Actions
        "Retour": "Back",
        "Suivant": "Next",
        "Précédent": "Previous",
        "Premier": "First",
        "Dernier": "Last",
        "Terminer": "Finish",
        "Continuer": "Continue",
        "Fermer": "Close",
        "Quitter": "Exit",
        "Annuler": "Cancel",
        "Ouvrir": "Open",
        "Page suivante": "Next Page",
        "Page précédente": "Previous Page",
        
        // Common Phrases
        "Voir plus": "See more",
        "Voir moins": "See less",
        "Voir tout": "View All",
        "Afficher plus": "Show more",
        "Masquer": "Hide",
        "Détails": "Details",
        "Plus de détails": "More Details",
        "Description": "Description",
        "Commentaire": "Comment",
        "Commentaires": "Comments",
        "Message": "Message",
        "Messages": "Messages",
        "Titre": "Title",
        "Objet": "Subject",
        "Contenu": "Content",
        "Type": "Type",
        "Catégorie": "Category",
        "Catégories": "Categories",
        "Récent": "Recent",
        "Récents": "Recent",
        "Ancien": "Old",
        "Anciens": "Old",
        "Actif": "Active",
        "Actifs": "Active",
        "Inactif": "Inactive",
        "Inactifs": "Inactive",
        "Tous": "All",
        "Toutes": "All",
        "Sélectionner": "Select",
        "Sélectionner tout": "Select All",
        "Désélectionner": "Deselect",
        "Choisir": "Choose",
        "Option": "Option",
        "Options": "Options",
        "Oui": "Yes",
        "Non": "No",
        "Peut-être": "Maybe",
        "Obligatoire": "Required",
        "Optionnel": "Optional",
        "Facultatif": "Optional",
        
        // User & Profile
        "Utilisateur": "User",
        "Utilisateurs": "Users",
        "Compte": "Account",
        "Mon compte": "My Account",
        "Profil": "Profile",
        "Photo de profil": "Profile Picture",
        "Avatar": "Avatar",
        "Connexion": "Login",
        "Se connecter": "Sign In",
        "Inscription": "Registration",
        "S'inscrire": "Sign Up",
        "Identifiant": "Username",
        "Identifiants": "Credentials",
        "Se souvenir de moi": "Remember me",
        "Mot de passe oublié ?": "Forgot password?",
        "Mot de passe oublié": "Forgot password",
        "Réinitialiser": "Reset",
        
        // Contact & Communication
        "Contact": "Contact",
        "Contacter": "Contact",
        "Téléphone": "Phone",
        "Appeler": "Call",
        "Envoyer un message": "Send Message",
        "Envoyer un email": "Send Email",
        "Chat": "Chat",
        "Discussion": "Discussion",
        "Conversation": "Conversation",
        "Répondre": "Reply",
        "Transférer": "Forward",
        
        // Numbers & Quantities
        "Premier": "First",
        "Deuxième": "Second",
        "Troisième": "Third",
        "Quatrième": "Fourth",
        "Cinquième": "Fifth",
        "Dernier": "Last",
        "Un": "One",
        "Deux": "Two",
        "Trois": "Three",
        "Quatre": "Four",
        "Cinq": "Five",
        "Plus": "More",
        "Moins": "Less",
        "Beaucoup": "Many",
        "Peu": "Few",
        "Plusieurs": "Several",
        
        // Forum & Community
        "Forum": "Forum",
        "Partagez avec la communauté": "Share with the community",
        "Questions, conseils, retours d'expérience…": "Questions, advice, experiences…",
        "Partagez votre expérience ou posez une question…": "Share your experience or ask a question…",
        "Photo": "Photo",
        "Publier": "Post",
        "Publication…": "Posting…",
        "Chargement des messages…": "Loading posts…",
        "Impossible de charger les messages. Veuillez réessayer plus tard.": "Unable to load posts. Please try again later.",
        "Aucun message pour le moment. Soyez le premier à publier !": "No posts yet. Be the first to post!",
        "En ligne": "Online",
        "Chargement...": "Loading...",
        "À propos du forum": "About the forum",
        "Cet espace vous permet d'échanger avec d'autres utilisateurs de BINTACURA : poser des questions, partager vos expériences et vous soutenir mutuellement.": "This space allows you to exchange with other BINTACURA users: ask questions, share your experiences and support each other.",
        "Conseils santé": "Health Tips",
        "Expériences patients": "Patient Experiences",
        "Questions générales": "General Questions",
        "Règles de bienveillance": "Community Guidelines",
        "Respectez la confidentialité et la vie privée.": "Respect confidentiality and privacy.",
        "Restez courtois, même en cas de désaccord.": "Stay courteous, even in case of disagreement.",
        "Cet espace ne remplace pas l'avis d'un professionnel de santé.": "This space does not replace the advice of a healthcare professional.",
        "À l'instant": "Just now",
        "Il y a": "ago",
        "min": "min",
        "Écrivez un commentaire...": "Write a comment...",
        "Commenter": "Comment",
        "Aucun commentaire": "No comments",
        "Répondre": "Reply",
        "Votre réponse...": "Your reply...",
        "Envoyer": "Send",
        "Aucun utilisateur en ligne": "No users online",
        "Une erreur s'est produite lors de la publication. Veuillez réessayer.": "An error occurred while posting. Please try again.",
        
        // Patient Settings
        "Paramètres du patient": "Patient Settings",
        "Compte et Profil": "Account & Profile",
        "Notifications et Alertes": "Notifications & Alerts",
        "Confidentialité et Sécurité": "Privacy & Security",
        "Préférences d'Interface": "Interface Preferences",
        "Dossier Médical": "Medical Record",
        "Autoriser le partage du dossier médical": "Allow medical record sharing",
        "Permissions de consultation du dossier": "Medical record access permissions",
        "Toujours demander confirmation": "Always ask for confirmation",
        "Permettre l'accès uniquement aux médecins certifiés": "Allow access only to certified doctors",
        "Permettre l'accès aux pharmaciens": "Allow access to pharmacists",
        "Partager avec les assurances": "Share with insurance companies",
        "Notifications par Email": "Email Notifications",
        "Recevoir les rappels de rendez-vous": "Receive appointment reminders",
        "Nouvelles prescriptions": "New prescriptions",
        "Résultats d'analyses disponibles": "Test results available",
        "Messages de mes médecins": "Messages from my doctors",
        "Promotions et actualités": "Promotions and news",
        "Notifications Push": "Push Notifications",
        "Recevoir des notifications push": "Receive push notifications",
        "Notifications SMS": "SMS Notifications",
        "Recevoir des notifications par SMS": "Receive SMS notifications",
        "Authentification à deux facteurs (2FA)": "Two-Factor Authentication (2FA)",
        "Activer la 2FA": "Enable 2FA",
        "Sessions Actives": "Active Sessions",
        "Voir les appareils connectés": "View connected devices",
        "Gérer les sessions": "Manage sessions",
        "Thème": "Theme",
        "Clair": "Light",
        "Sombre": "Dark",
        "Automatique": "Auto",
        "Taille du texte": "Text Size",
        "Petit": "Small",
        "Moyen": "Medium",
        "Grand": "Large",
        "Affichage compact": "Compact View",
        "Désactiver": "Disable",
        "Activer": "Enable",
        "Préférences sauvegardées avec succès": "Preferences saved successfully",
        "Gérer les autorisations": "Manage Permissions",
    }
};

class BINTACURATranslator {
    constructor() {
        this.currentLanguage = this.detectLanguage();
        this.init();
    }

    detectLanguage() {
        // Check user's preferred language from cookie or HTML lang attribute
        const langCookie = this.getCookie('django_language');
        if (langCookie) return langCookie;
        
        // Check if there's a language code in request context (Django sets this)
        const requestLang = document.documentElement.getAttribute('data-language');
        if (requestLang) return requestLang;
        
        const htmlLang = document.documentElement.lang;
        if (htmlLang && htmlLang !== 'fr' && htmlLang !== 'en') {
            // If HTML lang is neither fr nor en, default to fr
            return 'fr';
        }
        
        return htmlLang || 'fr'; // Default to French
    }

    getCookie(name) {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) return parts.pop().split(';').shift();
        return null;
    }

    init() {
        // Wait for DOM to be ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.translatePage());
        } else {
            this.translatePage();
        }

        // Listen for language changes
        this.observeLanguageChanges();
    }

    translatePage() {
        console.log('🔄 translatePage called. Current language:', this.currentLanguage);
        
        if (this.currentLanguage === 'fr') {
            console.log('ℹ️ Language is French (default), no translation needed');
            return; // No translation needed for French (default)
        }

        const lang = this.currentLanguage;
        if (!translations[lang]) {
            console.warn(`⚠️ Translations not available for language: ${lang}`);
            return;
        }

        console.log(`🔄 Translating page to ${lang}...`);
        this.translateElements(translations[lang]);
        console.log('✅ Page translation complete');
    }

    translateElements(translationDict) {
        // Translate text nodes
        const walker = document.createTreeWalker(
            document.body,
            NodeFilter.SHOW_TEXT,
            {
                acceptNode: (node) => {
                    // Skip script and style tags
                    if (node.parentElement.tagName === 'SCRIPT' || 
                        node.parentElement.tagName === 'STYLE') {
                        return NodeFilter.FILTER_REJECT;
                    }
                    // Only translate if text is not just whitespace
                    if (node.textContent.trim()) {
                        return NodeFilter.FILTER_ACCEPT;
                    }
                    return NodeFilter.FILTER_REJECT;
                }
            }
        );

        const nodesToTranslate = [];
        let node;
        while (node = walker.nextNode()) {
            nodesToTranslate.push(node);
        }

        nodesToTranslate.forEach(textNode => {
            const originalText = textNode.textContent.trim();
            if (translationDict[originalText]) {
                // Preserve whitespace around the text
                const leadingSpace = textNode.textContent.match(/^\s*/)[0];
                const trailingSpace = textNode.textContent.match(/\s*$/)[0];
                textNode.textContent = leadingSpace + translationDict[originalText] + trailingSpace;
            }
        });

        // Translate placeholder attributes
        document.querySelectorAll('[placeholder]').forEach(element => {
            const placeholder = element.getAttribute('placeholder');
            if (translationDict[placeholder]) {
                element.setAttribute('placeholder', translationDict[placeholder]);
            }
        });

        // Translate title attributes
        document.querySelectorAll('[title]').forEach(element => {
            const title = element.getAttribute('title');
            if (translationDict[title]) {
                element.setAttribute('title', translationDict[title]);
            }
        });

        // Translate aria-label attributes
        document.querySelectorAll('[aria-label]').forEach(element => {
            const ariaLabel = element.getAttribute('aria-label');
            if (translationDict[ariaLabel]) {
                element.setAttribute('aria-label', translationDict[ariaLabel]);
            }
        });

        // Update HTML lang attribute
        document.documentElement.lang = this.currentLanguage;
    }

    observeLanguageChanges() {
        // Listen for language switcher changes
        const languageSelect = document.getElementById('language-select');
        if (languageSelect) {
            languageSelect.addEventListener('change', (e) => {
                this.currentLanguage = e.target.value;
                // Page will reload after language change, so translation happens on next load
            });
        }

        // Also listen for cookie changes (in case language is changed elsewhere)
        const originalCookie = document.cookie;
        setInterval(() => {
            if (document.cookie !== originalCookie) {
                const newLang = this.detectLanguage();
                if (newLang !== this.currentLanguage) {
                    this.currentLanguage = newLang;
                    this.translatePage();
                }
            }
        }, 1000);
    }
}

// Initialize translator when script loads
if (typeof window !== 'undefined') {
    console.log('🌍 Initializing BINTACURA Translator...');
    window.BINTACURATranslator = new BINTACURATranslator();
    console.log('✅ BINTACURA Translator initialized. Current language:', window.BINTACURATranslator.currentLanguage);
}

