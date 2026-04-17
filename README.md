# 📊 Jobtolib - Annuaire des Entreprises France

Annuaire des entreprises françaises avec mise à jour automatique hebdomadaire.

## 🎯 Objectif

Fournir une **liste complète et à jour** des entreprises françaises actives, accessible en tant que données statiques JSON compressées. Permet aux applications de charger rapidement les données sans dépendre d'une API externe.

## 📦 Données

- **Source** : API INSEE (recherche-entreprises.api.gouv.fr)
- **Scope** : Entreprises actives créées depuis 5 ans (Option B)
- **Format** : JSON compressé (.json.gz)
- **Split** : Par lettre initiale du nom (A-Z + _OTHER)
- **Mise à jour** : Automatique chaque dimanche

### Structure des données

```json
{
  "siren": "380206397",
  "nom": "GOOGLE FRANCE SARL",
  "secteur": "62 - Programmation informatique",
  "naf": "6201Z",
  "ville": "Paris",
  "cp": "75001",
  "dept": "75",
  "adresse": "8 Rue de Londres, 75001 Paris",
  "tranche_effectif": "12",
  "date_creation": "2002-10-31"
}
```

## 🚀 Installation locale

### Prérequis
- Python 3.8+
- pip

### Setup

```bash
# Clone le repo
git clone https://github.com/julien-contreras/jobtolib.git
cd jobtolib

# Install dépendances
pip install -r requirements.txt

# Exécute le script de téléchargement
python download_entreprises.py
```

## 📁 Structure du projet

```
jobtolib/
├── download_entreprises.py      # Script Python principal
├── requirements.txt              # Dépendances Python
├── data/                        # Données générées (gitignore)
│   ├── A.json.gz
│   ├── B.json.gz
│   ├── ...
│   ├── Z.json.gz
│   └── index.json
├── .github/
│   └── workflows/
│       └── update-data.yml      # Workflow GitHub Actions
└── README.md

```

## ⚙️ Configuration GitHub Actions

Le workflow `update-data.yml` exécute automatiquement :
- ✅ Chaque **dimanche à 2h du matin** (UTC)
- ✅ À la demande via "Workflow Dispatch" dans GitHub UI

Pour modifier la fréquence, édite `.github/workflows/update-data.yml` :

```yaml
on:
  schedule:
    - cron: '0 2 * * 0'  # Dimanche 2h UTC
```

[Référence cron](https://crontab.guru/)

## 📊 Statistiques

Voir `data/index.json` pour :
- Total d'entreprises
- Count par lettre
- Date de dernière mise à jour

```bash
cat data/index.json | jq '.'
```

## 💾 Utilisation des données

### Python
```python
import gzip
import json

with gzip.open('data/A.json.gz', 'rt') as f:
    data = json.load(f)
    
for entreprise in data['entreprises']:
    print(entreprise['nom'], entreprise['ville'])
```

### JavaScript
```javascript
async function loadEntreprises(letter) {
  const resp = await fetch(`https://cdn.example.com/data/${letter}.json.gz`);
  const buffer = await resp.arrayBuffer();
  const decompressed = await decompressGzip(buffer);
  return JSON.parse(new TextDecoder().decode(decompressed));
}
```

## 🔧 Troubleshooting

### Erreur "API rate limit"
- Augmente `DELAY_BETWEEN_REQUESTS` dans `download_entreprises.py`
- Réduis `MAX_PAGES`

### Données manquantes
- Vérifie que tu as `per_page: 100` (max de l'API INSEE)
- Les entreprises "inactives" ne sont pas téléchargées (`etat_administratif: A`)

### Fichier trop volumineux
- Réduis `MAX_PAGES` pour télécharger moins de pages
- Ajoute des filtres par secteur ou région

## 📝 Logs

Les logs sont affichés dans la console lors de l'exécution.

Pour GitHub Actions :
1. Va sur : https://github.com/julien-contreras/jobtolib/actions
2. Clique sur le workflow le plus récent
3. Vois les logs complets

## 📄 License

MIT - Données libres d'utilisation

## 👤 Auteur

Julien Contreras - Jobtolib Project

---

**Besoin d'aide ?** Créé une issue : https://github.com/julien-contreras/jobtolib/issues
