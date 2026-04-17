#!/usr/bin/env python3
"""
Script de téléchargement et traitement des données INSEE
Jobtolib - Annuaire des Entreprises France

Télécharge les données de l'API INSEE (recherche-entreprises.api.gouv.fr)
Filtre les entreprises actives, nettoie et compresse en JSON.gz
Split par lettre initiale du nom pour chargement rapide.
"""

import json
import gzip
import os
import time
from pathlib import Path
from collections import defaultdict
import requests
from typing import Optional, Dict, List

# ========== CONFIGURATION ==========
API_BASE_URL = "https://recherche-entreprises.api.gouv.fr/search"
OUTPUT_DIR = "data"
PER_PAGE = 100  # Max par requête
MAX_PAGES = 100  # Limiter pour Option B (~10k entreprises max par recherche)
DELAY_BETWEEN_REQUESTS = 0.5  # Délai respectueux envers l'API (secondes)

# ========== CLASSES ==========
class EntrepriseDownloader:
    def __init__(self, output_dir: str = OUTPUT_DIR):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.all_entreprises = []
        self.index_data = defaultdict(list)
        
    def log(self, message: str, flush: bool = False):
        """Afficher un message avec timestamp"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {message}", flush=flush)
    
    def fetch_page(self, page: int, search_term: str = "") -> Dict:
        """Récupère une page de résultats de l'API INSEE"""
        params = {
            "per_page": PER_PAGE,
            "page": page,
            "etat_administratif": "A"  # Seulement entreprises ACTIVES
        }
        
        if search_term:
            params["q"] = search_term
        
        try:
            response = requests.get(API_BASE_URL, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self.log(f"❌ Erreur requête page {page}: {e}")
            return {"results": [], "total_results": 0}
    
    def clean_entreprise(self, e: Dict) -> Optional[Dict]:
        """Nettoie et extrait les données essentielles"""
        try:
            siege = e.get("siege", {})
            
            # Vérifier les données minimales
            if not e.get("siren") or not e.get("nom_raison_sociale"):
                return None
            
            # Déterminer le secteur
            secteur = e.get("libelle_activite_principale", "")
            naf_code = e.get("activite_principale", "")
            
            return {
                "siren": e.get("siren", ""),
                "nom": e.get("nom_raison_sociale", ""),
                "nom_complet": e.get("nom_complet", ""),
                "secteur": secteur,
                "naf": naf_code,
                "ville": siege.get("libelle_commune", ""),
                "cp": siege.get("code_postal", ""),
                "dept": siege.get("code_postal", "")[:2] if siege.get("code_postal") else "",
                "adresse": siege.get("adresse", ""),
                "tranche_effectif": e.get("tranche_effectif_salarie", ""),
                "date_creation": e.get("date_creation", ""),
            }
        except Exception as e:
            self.log(f"⚠️ Erreur parsing entreprise: {e}")
            return None
    
    def fetch_page_with_params(self, page: int, **kwargs) -> Dict:
        """Récupère une page de résultats avec paramètres personnalisés"""
        params = {
            "per_page": PER_PAGE,
            "page": page,
            "etat_administratif": "A"  # Seulement entreprises ACTIVES
        }
        params.update(kwargs)
        
        try:
            response = requests.get(API_BASE_URL, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self.log(f"❌ Erreur requête page {page}: {e}")
            return {"results": [], "total_results": 0}
    
    def download_all(self):
        """Télécharge toutes les entreprises actives par secteur"""
        self.log("🚀 Début du téléchargement des entreprises (Option B)")
        self.log("📊 Configuration: Téléchargement par secteur d'activité")
        
        # Secteurs NAF à télécharger (clés principales)
        secteurs = [
            ('J', 'Informatique/Télécoms'),
            ('M', 'Conseil/Ingénierie'),
            ('K', 'Finance/Immobilier'),
            ('G', 'Commerce/Transport'),
            ('N', 'Services aux entreprises'),
            ('C', 'Industrie'),
            ('F', 'Construction'),
            ('P', 'Enseignement'),
            ('Q', 'Santé/Action sociale'),
            ('H', 'Hébergement/Restauration'),
            ('I', 'Transports'),
            ('L', 'Administration'),
            ('R', 'Arts/Culture'),
            ('S', 'Services divers'),
        ]
        
        for secteur_code, secteur_name in secteurs:
            self.log(f"\n📂 Secteur {secteur_code} - {secteur_name}")
            
            page = 1
            has_more = True
            secteur_count = 0
            
            while has_more and page <= MAX_PAGES:
                self.log(f"   📄 Page {page}...")
                
                # Requête avec secteur
                data = self.fetch_page_with_params(
                    page, 
                    section_activite_principale=secteur_code
                )
                results = data.get("results", [])
                
                if not results:
                    self.log(f"      (vide)")
                    break
                
                # Nettoyer et ajouter
                cleaned_count = 0
                for entreprise in results:
                    cleaned = self.clean_entreprise(entreprise)
                    if cleaned:
                        self.all_entreprises.append(cleaned)
                        cleaned_count += 1
                        secteur_count += 1
                
                self.log(f"      ✓ {cleaned_count}/{len(results)} entreprises nettoyées")
                
                # Vérifier s'il y a d'autres pages
                has_more = len(results) == PER_PAGE and page < MAX_PAGES
                page += 1
                
                # Respecter l'API avec un délai
                time.sleep(DELAY_BETWEEN_REQUESTS)
            
            self.log(f"   ✅ {secteur_count} entreprises du secteur {secteur_code}")
        
        self.log(f"\n✅ Téléchargement terminé: {len(self.all_entreprises)} entreprises nettoyées")
        return len(self.all_entreprises)
    
    def save_split_by_letter(self):
        """Sauvegarde les données splitées par lettre initiale en .json.gz"""
        self.log("💾 Sauvegarde split par lettre initiale...")
        
        # Grouper
