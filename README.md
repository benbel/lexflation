# 📖 Legiquanti - Évolution des codes législatifs français

Visualisation interactive de l'évolution des codes législatifs français basée sur les données de [git.tricoteuses.fr/codes](https://git.tricoteuses.fr/codes).

## 🎯 Objectif

Afficher en "small multiples" (grille 4×N) l'évolution de chaque code législatif français avec :
- **Axe X** : Temps (du plus ancien commit à aujourd'hui)
- **Axe Y** : Delta de texte législatif (additions en vert, délétions en rouge)
- **Interactivité** : Tooltip au survol avec nom de la loi, date, stats, liens vers le commit et le code
- **Toggle Brut/Net** : Afficher les additions/délétions séparément ou le solde net

## 🚀 Déploiement

Le site est automatiquement déployé sur GitHub Pages via GitHub Actions.

### Configuration GitHub Pages

1. Aller dans Settings → Pages
2. Source : GitHub Actions
3. L'URL sera : `https://<username>.github.io/legiquanti/`

## 🛠️ Structure du projet

```
legiquanti/
├── .github/workflows/deploy.yml    # GitHub Action auto
├── scripts/fetch_codes_data.py     # Collecte des données
├── docs/                           # Site web statique
│   ├── index.html
│   ├── css/styles.css
│   ├── js/visualization.js
│   └── data/codes_data.json
├── PLAN.md                         # Plan détaillé
└── NOTES_EXPLORATION.md            # Notes API
```

## 📊 Fonctionnalités

- **Mode Brut** : Additions (vert) et délétions (rouge) séparément
- **Mode Net** : Solde uniquement (+30 -12 → +18)
- **Tooltip interactif** avec liens vers commits et code source
- **Échelles communes** pour faciliter la comparaison

## 🔧 Développement local

```bash
# Générer les données (5 min pour 112 codes)
python3 scripts/fetch_codes_data.py

# Tester localement
cd docs && python3 -m http.server 8000
# → http://localhost:8000
```

## 📡 Source des données

- **112 codes législatifs** depuis [git.tricoteuses.fr/codes](https://git.tricoteuses.fr/codes)
- **API Forgejo** (compatible Gitea v1)
- **~56,000 commits** au total
- **Période** : 1970 - 2029

## 🎨 Technologies

- D3.js v7, HTML5, CSS3, JavaScript
- Python 3 (collecte)
- GitHub Pages + Actions
