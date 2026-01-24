# Plan de développement - Visualisation des codes législatifs français

## Vue d'ensemble du projet

Créer une page web statique interactive qui visualise l'évolution des codes législatifs français à partir des dépôts Git disponibles sur https://git.tricoteuses.fr/codes, avec déploiement sur GitHub Pages.

## 0. Découvertes de l'exploration initiale

### 0.1 Plateforme et API
- **Plateforme** : Forgejo (fork de Gitea) - compatible avec l'API Gitea v1
- **API disponible** : `https://git.tricoteuses.fr/api/v1/`
- **Nombre total de dépôts** : **112 codes législatifs** (pas 75 comme estimé initialement)
- **Organisation** : `codes` - tous les dépôts sont sous `/api/v1/orgs/codes/repos`

### 0.2 Exemple analysé : Code civil
- **Nombre de commits** : 498
- **Plage temporelle** : 1970-01-01 à 2029-01-01
  - Note : Les dates sont symboliques (pas les vraies dates historiques)
  - Les anciens textes non trouvés sont datés de 1970
  - Les lois récentes utilisent des dates futures pour l'entrée en vigueur
- **Structure** : Organisé en livres (livre_ier, livre_ii, etc.)
- **Format** : Fichiers Markdown (.md) par article

### 0.3 Format des commits
**Messages de commit typiques** :
```
LOI n° 2024-317 du 8 avril 2024 portant mesures pour bâtir la société du bien vieillir

Lien: https://git.tricoteuses.fr/dila/textes_juridiques/src/branch/main/JORF/TEXT/...
Nature: LOI
Identifiant: JORFTEXT000049040245
NOR: IOMV2236472L
```

**Statistiques disponibles via l'API** :
```json
"stats": {
    "total": 31,
    "additions": 18,
    "deletions": 13
}
```

### 0.4 URLs des commits
**Format vérifié et fonctionnel** :
- Commit : `https://git.tricoteuses.fr/codes/{repo}/commit/{hash}`
- Code à cette version : `https://git.tricoteuses.fr/codes/{repo}/src/commit/{hash}`

### 0.5 Implications pour l'implémentation
✅ **Avantages** :
- **Pas besoin de cloner les dépôts** - tout peut se faire via l'API REST
- **Statistiques de diff déjà calculées** - gain de temps majeur
- **API bien documentée** - compatible Gitea
- **Métadonnées riches** - liens vers textes juridiques, identifiants NOR, etc.

⚠️ **Considérations** :
- **112 dépôts × ~500 commits/dépôt** = ~56,000 commits potentiels
- **Rate limiting** : À vérifier - probablement limité à quelques requêtes/seconde
- **Pagination** : L'API Forgejo utilise des pages (limit/offset)
- **Volume de données** : Le JSON final pourrait être conséquent (plusieurs Mo)

## 1. Architecture générale

### 1.1 Structure du projet
```
legiquanti/
├── data/
│   ├── raw/              # Données brutes des dépôts git
│   └── processed/        # Données traitées (JSON)
├── scripts/
│   ├── fetch_repos.py    # Script pour récupérer la liste des dépôts
│   ├── extract_data.py   # Script pour extraire l'historique et les diffs
│   └── process_data.py   # Script pour traiter et agréger les données
├── docs/                 # Dossier pour GitHub Pages
│   ├── index.html
│   ├── css/
│   │   └── styles.css
│   ├── js/
│   │   ├── main.js
│   │   └── visualization.js
│   └── data/
│       └── codes_data.json
├── README.md
└── PLAN.md
```

### 1.2 Flux de données

```
┌─────────────────────────────────────────────────────────┐
│  git.tricoteuses.fr (Forgejo)                           │
│  ┌──────────────┐                                       │
│  │ 112 codes    │ ← API: /orgs/codes/repos              │
│  │ législatifs  │                                       │
│  └──────┬───────┘                                       │
│         │                                                │
│         ├─→ code_civil (498 commits) ──┐                │
│         ├─→ code_penal  (XXX commits) ──┼─ API: /repos/ │
│         ├─→ code_de_commerce ...     ──┤   {repo}/commits│
│         └─→ ... (109 autres)         ──┘                │
└─────────────────────────────────────────────────────────┘
                          │
                          ↓
           ┌──────────────────────────┐
           │  fetch_codes_data.py     │
           │  (Script Python)         │
           │                          │
           │  • Pagination API        │
           │  • Rate limiting         │
           │  • Retry sur erreur      │
           │  • Calcul min/max        │
           └──────────┬───────────────┘
                      │
                      ↓
           ┌──────────────────────────┐
           │  docs/data/              │
           │  codes_data.json         │
           │  (~2-3 Mo gzippé)        │
           └──────────┬───────────────┘
                      │
                      ↓
           ┌──────────────────────────┐
           │  docs/index.html         │
           │  + D3.js                 │
           │                          │
           │  • Charge le JSON        │
           │  • Calcule échelles      │
           │  • Render 112 graphiques │
           │  • Tooltips interactifs  │
           └──────────┬───────────────┘
                      │
                      ↓
           ┌──────────────────────────┐
           │  GitHub Pages            │
           │  https://{user}.github.io│
           │  /legiquanti/            │
           └──────────────────────────┘
```

**Étapes simplifiées** :
1. **API → Python** : Collecte via l'API Forgejo
2. **Python → JSON** : Transformation et agrégation
3. **JSON → D3.js** : Visualisation interactive
4. **GitHub Pages** : Hébergement statique

## 2. Acquisition et traitement des données

### 2.1 Récupération de la liste des dépôts
**Objectif** : Obtenir la liste complète des 112 codes disponibles

**Méthode retenue : API Forgejo** ✅
```python
GET https://git.tricoteuses.fr/api/v1/orgs/codes/repos?limit=50&page=1
```

**Paramètres de pagination** :
- `limit` : Nombre de résultats par page (max 50)
- `page` : Numéro de page (commence à 1)
- Itérer jusqu'à obtenir tous les dépôts

**Données extraites de l'API** :
```json
{
  "name": "code_civil",                    // slug du dépôt
  "full_name": "codes/code_civil",
  "description": "Code civil",             // nom affiché
  "html_url": "https://...",               // URL web
  "clone_url": "https://...git"            // URL git (si besoin)
}
```

### 2.2 Extraction des commits via l'API
**Pour chaque dépôt** :

**Méthode retenue : API Forgejo (pas de clonage nécessaire)** ✅

```python
GET https://git.tricoteuses.fr/api/v1/repos/codes/{repo_name}/commits?limit=100&page=1
```

**Paramètres** :
- `limit` : Nombre de commits par page (max 100)
- `page` : Numéro de page
- `sha` : branche (par défaut : branche principale)

**Données extraites pour chaque commit** :
```json
{
  "sha": "528fadfa1a7b1783...",           // Hash complet
  "created": "2026-01-01T00:00:00Z",      // Date du commit
  "html_url": "https://...",               // URL du commit
  "commit": {
    "message": "LOI n° 2024-42...",       // Message complet
    "author": {
      "name": "République française",
      "date": "2026-01-01T00:00:00Z"
    }
  },
  "stats": {
    "total": 31,
    "additions": 18,                      // ✅ Déjà calculé !
    "deletions": 13                       // ✅ Déjà calculé !
  }
}
```

**Construction des URLs** :
- URL du commit : Fournie par `html_url`
- URL du code : `https://git.tricoteuses.fr/codes/{repo_name}/src/commit/{sha}`

### 2.3 Structure de données JSON optimisée

**Version complète** (pour le développement) :
```json
{
  "metadata": {
    "generated_at": "2026-01-24T10:00:00Z",
    "earliest_commit": "1970-01-01T00:00:00Z",
    "latest_commit": "2029-01-01T00:00:00Z",
    "total_codes": 112,
    "total_commits": 56000,
    "max_additions": 5000,
    "max_deletions": 3000
  },
  "codes": [
    {
      "name": "Code civil",
      "slug": "code_civil",
      "repo_url": "https://git.tricoteuses.fr/codes/code_civil",
      "total_commits": 498,
      "commits": [
        {
          "sha": "528fadfa1a7b...",
          "date": "2026-01-01T00:00:00Z",
          "ts": 1735689600000,              // timestamp pour performance
          "msg": "LOI n° 2024-42 du 26 janvier 2024...",
          "add": 18,                        // additions (format court)
          "del": 13,                        // deletions (format court)
          "url": "https://git.tricoteuses.fr/codes/code_civil/commit/528fadfa..."
        }
      ]
    }
  ]
}
```

**Version optimisée** (pour la production) :
- Noms de champs raccourcis (`add` au lieu de `additions`)
- Pas d'URL du code (peut être reconstruit côté client)
- Message tronqué si >100 caractères
- Gzip automatique par GitHub Pages (réduction ~70%)

**Estimation de taille** :
- 112 codes × 500 commits/code × ~150 bytes/commit ≈ **8.4 Mo non compressé**
- Avec gzip : **~2-3 Mo** (acceptable pour une page web)

### 2.4 Calcul des échelles communes
**Échelle temporelle (axe X)** :
- Min : date du commit le plus ancien parmi TOUS les codes
- Max : date du commit le plus récent (ou aujourd'hui)

**Échelle des deltas (axe Y)** :
- Min : valeur minimale de deletions (en négatif) parmi TOUS les commits
- Max : valeur maximale de additions parmi TOUS les commits
- Symétrique ou asymétrique selon les données

## 3. Visualisation web

### 3.1 Technologies
- **HTML5** : Structure de la page
- **CSS3** : Mise en forme et grille responsive
- **Vanilla JavaScript** ou **D3.js** :
  - D3.js recommandé pour les échelles, axes et manipulation de données
  - Canvas ou SVG pour le rendu des graphiques
  - Choix : **SVG** pour meilleure interactivité et accessibilité

### 3.2 Layout - Small Multiples
```
┌────────────────────────────────────────────┐
│           Titre de la page                 │
│  Visualisation des codes législatifs       │
├────────┬────────┬────────┬────────┐
│ Code 1 │ Code 2 │ Code 3 │ Code 4 │
├────────┼────────┼────────┼────────┤
│ Code 5 │ Code 6 │ Code 7 │ Code 8 │
├────────┼────────┼────────┼────────┤
│  ...   │  ...   │  ...   │  ...   │
└────────┴────────┴────────┴────────┘
```

**Grille CSS** :
```css
.charts-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  max-width: 1400px; /* Pour limiter à ~4 colonnes sur grand écran */
  gap: 20px;
}
```

### 3.3 Graphique individuel (area chart)

**Structure de chaque graphique** :
```
┌─────────────────────────────┐
│    Nom du Code             │
├─────────────────────────────┤
│         +                   │
│        ╱╲  vert (additions)│
│   ────┼──────────────> t   │
│       │╲╱  rouge (deletions)│
│         -                   │
└─────────────────────────────┘
```

**Composants SVG** :
1. **Titre** : Nom du code en haut
2. **Axes** :
   - Axe X : temps (quelques ticks avec années)
   - Axe Y : nombre de lignes modifiées
   - Ligne zéro bien visible
3. **Areas** :
   - Zone verte au-dessus de 0 (additions) avec `fill: #2ea043` (vert GitHub)
   - Zone rouge en-dessous de 0 (deletions) avec `fill: #cf222e` (rouge GitHub)
4. **Points interactifs** : Cercles invisibles ou petits pour le hover
5. **Tooltip** : Rectangle flottant qui suit la souris

### 3.4 Interactivité - Tooltip

**Déclenchement** :
- `mousemove` sur la zone du graphique
- Utiliser une recherche binaire ou Voronoi pour trouver le commit le plus proche

**Contenu du tooltip** :
```
┌────────────────────────────────┐
│ Nom de la loi/décret          │
│ Date : 15 janvier 2020         │
│ Modifications : +150 -45       │
│ 🔗 Voir le commit              │
│ 🔗 Voir le code à cette date   │
└────────────────────────────────┘
```

**Style** :
```css
.tooltip {
  position: absolute;
  background: white;
  border: 1px solid #ccc;
  border-radius: 4px;
  padding: 10px;
  font-size: 12px;
  pointer-events: none;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}
```

### 3.5 Performance

**Optimisations** :
- Limiter le nombre de points affichés si trop dense (agrégation par semaine/mois)
- Utiliser `requestAnimationFrame` pour les animations de tooltip
- Lazy loading des graphiques si >50 codes (Intersection Observer)
- Compresser le JSON (gzip) - GitHub Pages le sert automatiquement

## 4. Implémentation technique

### 4.1 Phase 1 : Scripts Python de collecte de données

**Dépendances** :
```
requests       # Pour l'API REST
json           # Built-in Python
time           # Pour les délais entre requêtes
```
(Pas besoin de BeautifulSoup ni GitPython !)

**Script unique : `fetch_codes_data.py`**

Étapes du script :

1. **Récupérer la liste des dépôts**
   ```python
   def fetch_all_repos():
       page = 1
       all_repos = []
       while True:
           url = f"https://git.tricoteuses.fr/api/v1/orgs/codes/repos?limit=50&page={page}"
           response = requests.get(url)
           repos = response.json()
           if not repos:
               break
           all_repos.extend(repos)
           page += 1
           time.sleep(0.5)  # Rate limiting
       return all_repos
   ```

2. **Pour chaque dépôt, récupérer tous les commits**
   ```python
   def fetch_repo_commits(repo_name):
       page = 1
       all_commits = []
       while True:
           url = f"https://git.tricoteuses.fr/api/v1/repos/codes/{repo_name}/commits"
           params = {"limit": 100, "page": page}
           response = requests.get(url, params=params)
           commits = response.json()
           if not commits:
               break
           all_commits.extend(commits)
           page += 1
           time.sleep(0.3)  # Rate limiting
       return all_commits
   ```

3. **Transformer les données au format final**
   - Extraire les champs nécessaires
   - Calculer les timestamps
   - Raccourcir les messages si besoin
   - Calculer les min/max globaux

4. **Générer le JSON final**
   - Sauvegarder dans `docs/data/codes_data.json`
   - Option : Créer aussi une version "light" avec moins de données

**Gestion des erreurs** :
- Retry automatique sur erreur réseau (3 tentatives)
- Sauvegarde intermédiaire tous les 10 codes
- Log de progression détaillé
- Gestion des timeouts

### 4.2 Phase 2 : Interface web

**Fichier : `docs/index.html`**
- Structure HTML basique
- Chargement de D3.js depuis CDN
- Conteneur pour la grille de graphiques

**Fichier : `docs/js/visualization.js`**
- Fonction `loadData()` : Charger le JSON
- Fonction `createScales()` : Créer les échelles X et Y communes
- Fonction `renderChart(code, container)` : Rendre un graphique
- Fonction `renderAllCharts()` : Boucle sur tous les codes
- Fonction `setupTooltip()` : Gérer les interactions hover

**Fichier : `docs/css/styles.css`**
- Grille responsive
- Styles des graphiques
- Styles du tooltip
- Mode sombre optionnel

### 4.3 Phase 3 : Déploiement GitHub Pages

**Configuration** :
1. Activer GitHub Pages sur la branche principale
2. Configurer le dossier source : `/docs`
3. Optionnel : Domaine personnalisé

**Workflow automatisé (optionnel)** :
- GitHub Actions pour régénérer les données périodiquement
- Commit automatique du nouveau JSON
- Redéploiement automatique

## 5. Défis et solutions

### 5.1 Volume de données
**Problème** : Si beaucoup de codes avec beaucoup de commits, le JSON peut être très lourd.

**Solutions** :
- Agréger les commits par période (jour/semaine) si >1000 commits par code
- Pagination ou lazy loading des graphiques
- Compression du JSON

### 5.2 Temps de traitement
**Problème** : 112 dépôts × requêtes API peuvent prendre du temps.

**Estimation** :
- 112 repos × 0.5s = ~56s pour lister les dépôts
- 112 repos × 5 pages/repo × 0.3s = ~168s pour tous les commits
- **Total : ~4-5 minutes** pour collecter toutes les données

**Solutions** :
- Parallélisation avec `concurrent.futures` (ThreadPoolExecutor)
- Cache local : sauvegarder les données et ne re-fetch que si nécessaire
- Barre de progression avec `tqdm` pour le feedback utilisateur

### 5.3 Accès aux dépôts
**Problème** : git.tricoteuses.fr pourrait avoir des limites de rate ou bloquer le scraping.

**Solutions** :
- Respecter robots.txt
- Ajouter des délais entre les requêtes
- Utiliser l'API officielle si disponible
- Contacter les mainteneurs si nécessaire

### 5.4 Uniformité des échelles
**Problème** : Certains codes peuvent avoir des modifications beaucoup plus importantes que d'autres.

**Solutions** :
- Échelle logarithmique optionnelle
- Permettre de basculer entre échelle commune et échelle par code
- Normalisation visuelle (couleurs plus/moins intenses)

## 6. Plan d'exécution par étapes

### Étape 1 : Exploration ✅ TERMINÉE
- [x] Explorer manuellement git.tricoteuses.fr/codes
- [x] Identifier la technologie (Forgejo/Gitea)
- [x] Tester l'API - Confirmée fonctionnelle
- [x] Cloner le Code civil pour comprendre la structure
- [x] Vérifier les URLs de commits et de code
- [x] Confirmer que l'API fournit les stats de diff

**Résultats** :
- 112 codes disponibles
- API Forgejo pleinement fonctionnelle
- Exemple : Code civil avec 498 commits
- Pas besoin de cloner les dépôts !

### Étape 2 : Script de collecte (1 jour)
- [ ] Développer `fetch_codes_data.py` unique
- [ ] Implémenter la pagination pour les repos et commits
- [ ] Ajouter le rate limiting et la gestion d'erreurs
- [ ] Tester sur 3-5 codes d'abord
- [ ] Exécuter sur tous les 112 codes
- [ ] Générer le premier `docs/data/codes_data.json`

### Étape 3 : Prototype de visualisation (2-3 jours)
- [ ] Créer la structure HTML de base
- [ ] Implémenter un graphique simple avec D3.js
- [ ] Tester avec les données de 1-2 codes
- [ ] Ajouter les tooltips basiques

### Étape 4 : Small multiples (1-2 jours)
- [ ] Implémenter la grille responsive
- [ ] Générer tous les graphiques
- [ ] Vérifier les échelles communes
- [ ] Optimiser les performances

### Étape 5 : Finalisation (1-2 jours)
- [ ] Améliorer le design
- [ ] Ajouter des informations contextuelles
- [ ] Tests cross-browser
- [ ] Optimisations finales
- [ ] Documentation README

### Étape 6 : Déploiement (1 jour)
- [ ] Configuration GitHub Pages
- [ ] Premier déploiement
- [ ] Tests en production
- [ ] Optionnel : Configuration CI/CD

## 7. Extensions futures possibles

### Court terme
- Filtre par période
- Recherche de code
- Export des données en CSV
- Mode sombre

### Moyen terme
- Statistiques agrégées (codes les plus modifiés, périodes d'activité)
- Comparaison entre codes
- Timeline globale avec tous les codes superposés
- Annotations pour les grandes réformes

### Long terme
- Analyse du contenu des modifications (mots-clés, thématiques)
- Corrélation avec les événements politiques
- API publique pour les données traitées
- Version mobile optimisée

## 8. Ressources et références

### Données
- Source : https://git.tricoteuses.fr/codes
- Plateforme : Forgejo (fork de Gitea)
- Documentation API : https://forgejo.org/docs/latest/user/api-usage/
- API Gitea (compatible) : https://docs.gitea.io/en-us/api-usage/
- Endpoint API : https://git.tricoteuses.fr/api/v1/

### Visualisation
- D3.js : https://d3js.org/
- Small multiples : https://observablehq.com/@d3/gallery#small-multiples
- Area charts : https://d3-graph-gallery.com/area.html

### Couleurs GitHub
- Vert additions : `#2ea043`
- Rouge deletions : `#cf222e`

### Déploiement
- GitHub Pages : https://pages.github.com/
- GitHub Actions : https://docs.github.com/en/actions

---

## 9. Résumé et décisions clés

### ✅ Décisions validées
1. **API REST uniquement** - Pas de clonage Git nécessaire
2. **Forgejo API** fournit déjà les stats de diff (additions/deletions)
3. **D3.js pour la visualisation** - Idéal pour les small multiples
4. **Format JSON compact** avec noms de champs courts
5. **GitHub Pages** pour l'hébergement

### 📊 Chiffres clés
- **112 codes** à visualiser
- **~56,000 commits** estimés au total
- **~2-3 Mo** de données JSON (compressé)
- **~5 minutes** pour la collecte des données
- **Grille 4×28** pour la visualisation

### 🎯 Prochaines actions immédiates
1. Développer le script Python `fetch_codes_data.py`
2. Tester sur un sous-ensemble de codes
3. Générer le JSON complet
4. Créer un prototype HTML/JS avec D3.js
5. Itérer sur le design des graphiques

---

**Date de création** : 2026-01-24
**Date de mise à jour** : 2026-01-24
**Statut** : ✅ Exploration terminée - Prêt pour l'implémentation
**Prochaine étape** : Développer le script de collecte de données
