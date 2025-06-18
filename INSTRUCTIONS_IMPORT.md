# Instructions d'utilisation du système RH-Bot

## Import des données CSV

### 1. Structure du modèle utilisateur étendu

Le modèle `CustomUser` a été étendu avec les champs suivants basés sur le CSV RH :

**Informations personnelles :**
- `employee_id` : ID unique employé (ex: E001)
- `departement` : Département (IT, Marketing, Finance, RH, Ventes, Recherche, Direction)
- `poste` : Intitulé du poste
- `is_manager` : Booléen indiquant si la personne est manager
- `responsable` : ID du responsable hiérarchique
- `date_embauche` : Date d'embauche

**Congés :**
- `conges_droit_annuel` : Nombre de jours de congés annuels accordés
- `conges_utilises` : Nombre de jours de congés utilisés
- `conges_planifies` : Nombre de jours de congés planifiés
- `conges_restants` : Nombre de jours de congés restants

**Congés maladie :**
- `conges_maladie_droit` : Nombre de jours de congés maladie accordés
- `conges_maladie_utilises` : Nombre de jours de congés maladie utilisés
- `conges_maladie_restants` : Nombre de jours de congés maladie restants

**Rémunération :**
- `salaire` : Salaire annuel en euros
- `eligible_prime` : Éligibilité aux primes
- `date_prochaine_evaluation` : Date de la prochaine évaluation

**Avantages :**
- `regime_sante` : Type de régime santé (Standard, Premium, Exécutif)

### 2. Commande d'importation

Pour importer les données du fichier CSV :

```bash
python manage.py import_hr_data
```

Options disponibles :
- `--file` : Chemin vers le fichier CSV (défaut: hr_dataset_fr_new.csv)
- `--password` : Mot de passe par défaut pour tous les utilisateurs (défaut: test)

Exemple avec options :
```bash
python manage.py import_hr_data --file mon_fichier.csv --password motdepasse123
```

### 3. Format du fichier CSV attendu

Le fichier CSV doit contenir les colonnes suivantes :
- `id` : ID employé unique
- `nom` : Nom complet de l'employé
- `email` : Adresse email
- `departement` : Département
- `Manager` : "Oui" ou "Non" pour indiquer si c'est un manager
- `poste` : Intitulé du poste
- `responsable` : ID du responsable
- `date_embauche` : Date d'embauche (format DD/MM/YYYY)
- `conges.droit_annuel` : Jours de congés annuels
- `conges.utilises` : Jours de congés utilisés
- `conges.planifies` : Jours de congés planifiés
- `conges.restants` : Jours de congés restants
- `conges_maladie.droit` : Jours de congés maladie accordés
- `conges_maladie.utilises` : Jours de congés maladie utilisés
- `conges_maladie.restants` : Jours de congés maladie restants
- `remuneration.salaire` : Salaire annuel
- `remuneration.eligible_prime` : Éligibilité aux primes (VRAI/FAUX)
- `remuneration.date_prochaine_evaluation` : Date prochaine évaluation
- `avantages.regime_sante` : Régime de santé

## Nouvelles fonctionnalités du Chat

### 1. Réponses personnalisées

Le système de chat a été amélioré pour prendre en compte les informations spécifiques de l'utilisateur connecté :

**Informations incluses automatiquement :**
- Nom et prénom
- Département et poste
- Informations sur les congés (restants, utilisés, planifiés)
- Salaire et éligibilité aux primes
- Date de prochaine évaluation
- Informations sur le manager
- Régime de santé

### 2. Exemples de questions personnalisées

**Congés :**
- "Combien de congés me reste-t-il ?"
- "Quand est ma prochaine évaluation ?"

**Informations hiérarchiques :**
- "Qui est mon manager ?"
- "Combien de personnes travaillent dans mon département ?"

**Rémunération :**
- "Quel est mon salaire ?"
- "Suis-je éligible aux primes ?"

**Congés maladie :**
- "Combien de jours de congés maladie me reste-t-il ?"

### 3. Réponses contextuelles

Le système fournit des réponses adaptées selon :
- Le département de l'utilisateur
- Son statut (manager ou non)
- Ses informations personnelles RH
- Son historique de congés

## Formulaire d'inscription étendu

Le formulaire d'inscription a été mis à jour pour inclure tous les nouveaux champs :

**Section Informations de base :**
- Username, Email, Prénom, Nom
- Date de naissance, Sexe

**Section Informations professionnelles :**
- ID Employé, Département, Poste
- Date d'embauche, Salaire, Régime de santé

**Section Sécurité :**
- Mot de passe et confirmation

## Migration des données

Les migrations ont été créées automatiquement pour ajouter tous les nouveaux champs au modèle utilisateur existant.

Pour appliquer les migrations :
```bash
python manage.py makemigrations
python manage.py migrate
```

## Authentification par défaut

Tous les utilisateurs importés depuis le CSV ont le mot de passe par défaut "test" (modifiable via la commande d'importation).

## Support technique

En cas de problème avec l'importation :
1. Vérifiez que le fichier CSV est au bon format
2. Vérifiez l'encodage du fichier (le système supporte UTF-8, Latin-1, CP1252, ISO-8859-1)
3. Consultez les logs d'erreur dans la console pour identifier les lignes problématiques 