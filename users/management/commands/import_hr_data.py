from django.core.management.base import BaseCommand
from django.contrib.auth.hashers import make_password
from users.models import CustomUser
import csv
import os
from datetime import datetime

class Command(BaseCommand):
    help = 'Importe les données RH depuis le fichier CSV'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            default='hr_dataset_fr_new.csv',
            help='Chemin vers le fichier CSV à importer'
        )
        parser.add_argument(
            '--password',
            type=str,
            default='test',
            help='Mot de passe par défaut pour tous les utilisateurs'
        )

    def parse_date(self, date_string):
        """Parse une date au format DD/MM/YYYY"""
        if not date_string or date_string.strip() == '':
            return None
        try:
            return datetime.strptime(date_string.strip(), '%d/%m/%Y').date()
        except ValueError:
            self.stdout.write(
                self.style.WARNING(f"Erreur de format de date: {date_string}")
            )
            return None

    def parse_float(self, value):
        """Parse un float avec gestion des erreurs"""
        if not value or value.strip() == '':
            return 0.0
        try:
            return float(value.replace(',', '.'))
        except ValueError:
            self.stdout.write(
                self.style.WARNING(f"Erreur de format numérique: {value}")
            )
            return 0.0

    def parse_boolean(self, value):
        """Parse un booléen depuis le CSV"""
        if not value:
            return False
        value = value.strip().upper()
        return value in ['OUI', 'VRAI', 'TRUE', '1', 'YES']

    def handle(self, *args, **options):
        csv_file_path = options['file']
        default_password = options['password']
        
        if not os.path.exists(csv_file_path):
            self.stdout.write(
                self.style.ERROR(f"Erreur: Le fichier {csv_file_path} n'existe pas")
            )
            return
        
        created_count = 0
        updated_count = 0
        error_count = 0
        
        self.stdout.write("Début de l'importation des données CSV...")
        
        # Try different encodings
        encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
        csvfile = None
        used_encoding = None
        
        for encoding in encodings:
            try:
                csvfile = open(csv_file_path, 'r', encoding=encoding)
                csvfile.read(100)  # Test read
                csvfile.seek(0)  # Reset position
                used_encoding = encoding
                break
            except UnicodeDecodeError:
                if csvfile:
                    csvfile.close()
                continue
        
        if csvfile is None:
            self.stdout.write(
                self.style.ERROR("Impossible de lire le fichier CSV avec les encodages testés")
            )
            return
            
        self.stdout.write(f"Fichier ouvert avec l'encodage: {used_encoding}")
        
        try:
            # Détection automatique du délimiteur
            sample = csvfile.read(1024)
            csvfile.seek(0)
            delimiter = ';' if ';' in sample else ','
            
            reader = csv.DictReader(csvfile, delimiter=delimiter)
            
            for row_num, row in enumerate(reader, start=2):
                try:
                    # Extraction et nettoyage des données
                    employee_id = row.get('id', '').strip()
                    if not employee_id:
                        self.stdout.write(
                            self.style.WARNING(f"Ligne {row_num}: ID employé manquant, ignorée")
                        )
                        continue
                    
                    # Parsing du nom complet
                    nom_complet = row.get('nom', '').strip()
                    if ' ' in nom_complet:
                        parts = nom_complet.split(' ', 1)
                        first_name = parts[0]
                        last_name = parts[1]
                    else:
                        first_name = nom_complet
                        last_name = ''
                    
                    email = row.get('email', '').strip()
                    if not email:
                        email = f"{employee_id.lower()}@company.com"
                    
                    # Vérification si l'utilisateur existe déjà
                    user, created = CustomUser.objects.get_or_create(
                        employee_id=employee_id,
                        defaults={
                            'username': employee_id,
                            'email': email,
                            'first_name': first_name,
                            'last_name': last_name,
                            'password': make_password(default_password),
                        }
                    )
                    
                    # Mise à jour des champs
                    user.email = email
                    user.first_name = first_name
                    user.last_name = last_name
                    user.departement = row.get('departement', '').strip()
                    user.is_manager = self.parse_boolean(row.get('Manager', ''))
                    user.poste = row.get('poste', '').strip()
                    user.responsable = row.get('responsable', '').strip()
                    user.date_embauche = self.parse_date(row.get('date_embauche', ''))
                    
                    # Congés
                    user.conges_droit_annuel = self.parse_float(row.get('conges.droit_annuel', '25'))
                    user.conges_utilises = self.parse_float(row.get('conges.utilises', '0'))
                    user.conges_planifies = self.parse_float(row.get('conges.planifies', '0'))
                    user.conges_restants = self.parse_float(row.get('conges.restants', '25'))
                    
                    # Congés maladie
                    user.conges_maladie_droit = self.parse_float(row.get('conges_maladie.droit', '10'))
                    user.conges_maladie_utilises = self.parse_float(row.get('conges_maladie.utilises', '0'))
                    user.conges_maladie_restants = self.parse_float(row.get('conges_maladie.restants', '10'))
                    
                    # Rémunération
                    user.salaire = self.parse_float(row.get('remuneration.salaire', '0'))
                    user.eligible_prime = self.parse_boolean(row.get('remuneration.eligible_prime', 'VRAI'))
                    user.date_prochaine_evaluation = self.parse_date(row.get('remuneration.date_prochaine_evaluation', ''))
                    
                    # Avantages
                    regime = row.get('avantages.regime_sante', 'Standard').strip()
                    if regime in dict(CustomUser.REGIME_SANTE_CHOICES):
                        user.regime_sante = regime
                    else:
                        user.regime_sante = 'Standard'
                    
                    user.save()
                    
                    if created:
                        created_count += 1
                        self.stdout.write(
                            self.style.SUCCESS(f"✓ Utilisateur créé: {employee_id} - {first_name} {last_name}")
                        )
                    else:
                        updated_count += 1
                        self.stdout.write(
                            self.style.SUCCESS(f"⟳ Utilisateur mis à jour: {employee_id} - {first_name} {last_name}")
                        )
                        
                except Exception as e:
                    error_count += 1
                    self.stdout.write(
                        self.style.ERROR(f"✗ Erreur ligne {row_num} (ID: {employee_id}): {str(e)}")
                    )
                    continue
        finally:
            if csvfile:
                csvfile.close()
        
        self.stdout.write(self.style.SUCCESS(f"\n=== RÉSUMÉ DE L'IMPORTATION ==="))
        self.stdout.write(self.style.SUCCESS(f"Utilisateurs créés: {created_count}"))
        self.stdout.write(self.style.SUCCESS(f"Utilisateurs mis à jour: {updated_count}"))
        if error_count > 0:
            self.stdout.write(self.style.ERROR(f"Erreurs: {error_count}"))
        self.stdout.write(self.style.SUCCESS(f"Total traité: {created_count + updated_count + error_count}")) 