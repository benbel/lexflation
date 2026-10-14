# Lexflation

Mesure la taille du droit codifié français : pour chaque année, le nombre de lignes ajoutées moins
le nombre de lignes supprimées dans les 111 codes non vides publiés en dépôts git par
[git.tricoteuses.fr](https://git.tricoteuses.fr/codes). La page publiée montre ce solde cumulé
année après année, et le détail par code au survol.

## Lancer

```bash
./run.sh                               # tests, collecte des données, page : docs/index.html
python3 scripts/fetch_codes_data.py    # collecte seule : docs/data/codes_data.json (environ 15 min)
python3 scripts/generate_chart.py      # page seule, à partir du JSON déjà collecté
```

## Organisation

| Fichier | Rôle |
|---|---|
| `run.sh` | sans argument : lance les tests, collecte les données, génère la page |
| `scripts/fetch_codes_data.py` | sans argument : lit l'API Forgejo, écrit `docs/data/codes_data.json` |
| `scripts/generate_chart.py` | sans argument : lit le JSON, écrit `docs/index.html` |
| `tests/` | tests unitaires de la collecte, sur données fabriquées |
| `.github/workflows/deploy.yml` | le 1er de chaque mois, à chaque push sur `main` et à la demande : `run.sh` puis publication sur GitHub Pages |

## Règles fermes

- **Les données et la page ne sont pas versionnées.** `docs/index.html` et `docs/data/` sont
  reconstruits par `run.sh`, en local comme dans la CI, et publiés depuis la CI.
- **Une collecte incomplète arrête tout.** Si une page de l'API échoue après trois tentatives,
  le script s'arrête et la page publiée reste celle du mois précédent.
- **Un dépôt vide est écarté et nommé.** Forgejo répond 409 à la liste des commits d'un dépôt vide
  (`code_de_procedure_civile_1807` depuis juillet 2026) ; c'est ce qui a fait échouer les mises à
  jour d'août et de septembre 2026.

## Tests

```bash
python3 -m unittest discover -s tests
```

Ils couvrent l'extraction des commits, l'agrégation, la pagination de l'API et le tri des dépôts
vides.
