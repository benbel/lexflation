# Notes d'exploration - git.tricoteuses.fr/codes

## Informations générales

- **Date d'exploration** : 2026-01-24
- **Nombre de dépôts** : 112 codes législatifs
- **Plateforme** : Forgejo
- **API** : Compatible Gitea v1

## Exemple concret : Code civil

### Statistiques
- **Nombre de commits** : 498
- **Premier commit** : 1970-01-01T00:00:00+00:00
- **Dernier commit** : 2029-01-01T00:00:00+00:00
- **Taille du dépôt** : 3,519 fichiers

### Structure du dépôt
```
code_civil/
├── LICENCE.md
├── README.md (1.6 Mo)
├── titre_preliminaire/
├── livre_ier/
├── livre_ii/
├── livre_iii/
├── livre_iv/
└── livre_v/
```

### Exemple de commit (via API)

**Endpoint** :
```
GET https://git.tricoteuses.fr/api/v1/repos/codes/code_civil/commits?limit=1
```

**Réponse JSON** :
```json
{
  "url": "https://git.tricoteuses.fr/api/v1/repos/codes/code_civil/git/commits/528fadfa1a7b1783b70ff28d3e163d32ba0562b3",
  "sha": "528fadfa1a7b1783b70ff28d3e163d32ba0562b3",
  "created": "2026-01-01T00:00:00Z",
  "html_url": "https://git.tricoteuses.fr/codes/code_civil/commit/528fadfa1a7b1783b70ff28d3e163d32ba0562b3",
  "commit": {
    "author": {
      "name": "République française",
      "email": "republique@tricoteuses.fr",
      "date": "2026-01-01T00:00:00Z"
    },
    "message": "LOI n° 2024-42 du 26 janvier 2024 pour contrôler l'immigration, améliorer l'intégration\n\nLien: https://git.tricoteuses.fr/dila/textes_juridiques/src/branch/main/JORF/TEXT/00/00/49/04/02/JORFTEXT000049040245.md\nNature: LOI\nIdentifiant: JORFTEXT000049040245\nNOR: IOMV2236472L"
  },
  "files": [
    {
      "filename": "livre_ier/titre_ier_bis/chapitre_iii/section_1/paragraphe_5/article_21-24.md",
      "status": "modified"
    }
  ],
  "stats": {
    "total": 31,
    "additions": 18,
    "deletions": 13
  }
}
```

### Informations extraites du message de commit

Format typique :
```
[TYPE] n° [NUMERO] du [DATE] [TITRE_COURT]

Lien: [URL_VERS_TEXTE_JURIDIQUE]
Nature: [LOI|Ordonnance|Décret]
Identifiant: [JORF_ID]
NOR: [NOR_CODE]
```

Exemple :
- **Type** : LOI
- **Numéro** : 2024-42
- **Date** : 26 janvier 2024
- **Titre** : pour contrôler l'immigration, améliorer l'intégration
- **Lien** : Vers le dépôt textes_juridiques
- **Identifiant JORF** : JORFTEXT000049040245
- **Code NOR** : IOMV2236472L

## URLs des commits

### Format vérifié

1. **Page du commit** :
   ```
   https://git.tricoteuses.fr/codes/{repo_name}/commit/{sha}
   ```
   Exemple : https://git.tricoteuses.fr/codes/code_civil/commit/0e5f41ebfc7d4adabda545f254d5f65ba9cbba98

2. **Code à cette version** :
   ```
   https://git.tricoteuses.fr/codes/{repo_name}/src/commit/{sha}
   ```
   Exemple : https://git.tricoteuses.fr/codes/code_civil/src/commit/0e5f41ebfc7d4adabda545f254d5f65ba9cbba98

## Statistiques d'un gros commit

**Commit** : 0e5f41ebfc7d4adabda545f254d5f65ba9cbba98
**Titre** : Ordonnance n° 2025-229 du 12 mars 2025 portant réforme du régime des nullités en droit des sociétés
**Stats** :
- 11 fichiers modifiés
- +433 insertions
- -216 suppressions
- Articles concernés : 1844-10 à 1844-17

## Exemple de commits variés

```bash
# Premiers commits (données historiques manquantes)
66d9cd3|1970-01-01T00:00:00+00:00|Création du dépôt git
0625187|1970-12-31T06:58:44+00:00|!!! Texte non trouvé 1803-03-27 !!!
8c2b340|1970-12-31T07:00:53+00:00|LOI no 94-653 du 29 juillet 1994...

# Commits récents
a67ba0d|2029-01-01T00:00:00+00:00|Ordonnance n° 2025-1091 du 19 novembre 2025...
78085a4|2026-12-31T00:00:00+00:00|LOI n° 2024-317 du 8 avril 2024...
528fadf|2026-01-01T00:00:00+00:00|LOI n° 2024-42 du 26 janvier 2024...
```

## API Forgejo - Endpoints utiles

### Lister les dépôts d'une organisation
```bash
GET /api/v1/orgs/{org}/repos
Paramètres: limit (max 50), page (commence à 1)
```

### Lister les commits d'un dépôt
```bash
GET /api/v1/repos/{owner}/{repo}/commits
Paramètres: limit (max 100), page, sha (branche)
```

### Exemple de requête complète
```bash
curl -s "https://git.tricoteuses.fr/api/v1/repos/codes/code_civil/commits?limit=3" \
  | python3 -m json.tool
```

## Observations importantes

### 1. Dates symboliques
Les dates des commits ne correspondent pas aux dates réelles d'adoption des lois :
- **1970** : Textes historiques ou non trouvés
- **Futur (2025-2029)** : Date d'entrée en vigueur prévue

### 2. Format des fichiers
- Tous les articles sont en **Markdown** (.md)
- Un fichier par article
- Structure hiérarchique (livre/titre/chapitre/section/article)

### 3. Métadonnées riches
Chaque commit contient :
- Lien vers le texte juridique source
- Identifiant JORF
- Code NOR
- Nature du texte (LOI, Ordonnance, Décret)

### 4. Qualité des données
- ✅ Données structurées et cohérentes
- ✅ Statistiques de diff précalculées
- ✅ Messages de commit informatifs
- ⚠️ Dates symboliques (pas historiques)
- ⚠️ Quelques textes "non trouvés"

## Estimation du volume total

```
112 codes × 500 commits/code (moyenne estimée) = 56,000 commits
56,000 commits × 150 bytes/commit (JSON compact) = 8.4 Mo
Avec compression gzip : ~2-3 Mo
```

## Codes d'exemple à tester

Pour le développement, tester d'abord avec ces codes variés :

1. **Code civil** (volumineux, ~500 commits)
2. **Code de commerce** (moyen)
3. **Code électoral** (petit)
4. **Code de la route** (populaire)
5. **Code du cinéma et de l'image animée** (niche)

## Prochaines étapes

1. ✅ Exploration terminée
2. ⏭️ Développer `fetch_codes_data.py`
3. ⏭️ Tester sur 5 codes
4. ⏭️ Exécuter sur tous les codes
5. ⏭️ Créer le prototype de visualisation
