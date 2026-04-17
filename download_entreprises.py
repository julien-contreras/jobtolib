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
        
    def log(self, message: str):
        """Afficher un message avec timestamp"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {message}")
    
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
    
    def download_all(self):
        """Télécharge toutes les entreprises actives"""
        self.log("🚀 Début du téléchargement des entreprises (Option B)")
        self.log(f"📊 Configuration: {PER_PAGE} par page, max {MAX_PAGES} pages")
        
        total_fetched = 0
        page = 1
        has_more = True
        
        while has_more and page <= MAX_PAGES:
            self.log(f"📄 Récupération page {page}...")
            
            data = self.fetch_page(page)
            results = data.get("results", [])
            total_results = data.get("total_results", 0)
            
            if not results:
                self.log(f"✅ Fin du téléchargement (page {page} vide)")
                break
            
            # Nettoyer et ajouter
            cleaned_count = 0
            for entreprise in results:
                cleaned = self.clean_entreprise(entreprise)
                if cleaned:
                    self.all_entreprises.append(cleaned)
                    cleaned_count += 1
            
            total_fetched += len(results)
            self.log(f"   ✓ {len(results)} résultats, {cleaned_count} nettoyés (total: {len(self.all_entreprises)})")
            
            # Vérifier s'il y a d'autres pages
            has_more = len(results) == PER_PAGE and page < MAX_PAGES
            page += 1
            
            # Respecter l'API avec un délai
            time.sleep(DELAY_BETWEEN_REQUESTS)
        
        self.log(f"✅ Téléchargement terminé: {len(self.all_entreprises)} entreprises nettoyées")
        return len(self.all_entreprises)
    
    def save_split_by_letter(self):
        """Sauvegarde les données splitées par lettre initiale en .json.gz"""
        self.log("💾 Sauvegarde split par lettre initiale...")
        
        # Grouper par lettre
        by_letter = defaultdict(list)
        for entreprise in self.all_entreprises:
            nom = entreprise.get("nom", "")
            if nom:
                letter = nom[0].upper()
                if letter.isalpha():
                    by_letter[letter].append(entreprise)
                else:
                    by_letter["_OTHER"].append(entreprise)
        
        # Sauvegarder chaque lettre
        files_created = []
        for letter in sorted(by_letter.keys()):
            data = {"letter": letter, "count": len(by_letter[letter]), "entreprises": by_letter[letter]}
            filename = f"{self.output_dir}/{letter}.json.gz"
            
            with gzip.open(filename, 'wt', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=None)
            
            files_created.append((letter, len(by_letter[letter]), os.path.getsize(filename) / 1024))
            self.log(f"   ✓ {letter}.json.gz: {len(by_letter[letter])} entreprises ({os.path.getsize(filename) / 1024:.1f} KB)")
        
        return files_created
    
    def create_index(self):
        """Crée un index pour la recherche rapide"""
        self.log("📑 Création de l'index...")
        
        index = {
            "version": "1.0",
            "date": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_entreprises": len(self.all_entreprises),
            "letters": {}
        }
        
        # Grouper par lettre pour l'index
        by_letter = defaultdict(int)
        for entreprise in self.all_entreprises:
            nom = entreprise.get("nom", "")
            if nom:
                letter = nom[0].upper()
                if letter.isalpha():
                    by_letter[letter] += 1
                else:
                    by_letter["_OTHER"] += 1
        
        index["letters"] = dict(by_letter)
        
        # Sauvegarder l'index
        index_file = f"{self.output_dir}/index.json"
        with open(index_file, 'w', encoding='utf-8') as f:
            json.dump(index, f, ensure_ascii=False, indent=2)
        
        self.log(f"✅ Index créé: {index_file}")
        self.log(f"   Total: {index['total_entreprises']} entreprises")
        return index
    
    def generate_stats(self):
        """Génère des statistiques"""
        self.log("📊 Statistiques finales:")
        
        # Secteurs
        secteurs = defaultdict(int)
        for e in self.all_entreprises:
            secteur = e.get("secteur", "Inconnu")
            secteurs[secteur] += 1
        
        self.log(f"   Nombre total: {len(self.all_entreprises)}")
        self.log(f"   Secteurs uniques: {len(secteurs)}")
        self.log(f"   Top 5 secteurs:")
        for secteur, count in sorted(secteurs.items(), key=lambda x: x[1], reverse=True)[:5]:
            self.log(f"      - {secteur}: {count}")
        
        # Départements
        depts = defaultdict(int)
        for e in self.all_entreprises:
            dept = e.get("dept", "XX")
            if dept:
                depts[dept] += 1
        
        self.log(f"   Départements couverts: {len(depts)}")
        return {"total": len(self.all_entreprises), "secteurs": len(secteurs), "depts": len(depts)}

# ========== MAIN ==========
def main():
    downloader = EntrepriseDownloader(OUTPUT_DIR)
    
    try:
        # 1. Télécharger
        downloader.download_all()
        
        # 2. Sauvegarder split
        downloader.save_split_by_letter()
        
        # 3. Créer index
        downloader.create_index()
        
        # 4. Stats
        downloader.generate_stats()
        
        downloader.log("🎉 Processus complet terminé avec succès!")
        
    except Exception as e:
        downloader.log(f"❌ Erreur fatale: {e}")
        raise

if __name__ == "__main__":
    main()
