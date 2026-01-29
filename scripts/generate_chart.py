#!/usr/bin/env python3
"""
Génère un histogramme en Block Elements (caractères Unicode) à partir des données des codes législatifs.
Agrège les additions/délétions par année.
Produit: index.html (page autonome, pas de SVG)
"""

import json
from datetime import datetime
from collections import defaultdict
from pathlib import Path
from html import escape


def load_data(data_file: Path) -> dict:
    """Charge les données JSON"""
    with open(data_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def aggregate_by_year(data: dict) -> list:
    """
    Agrège tous les commits de tous les codes par année.
    Retourne une liste de dicts avec les totaux et les détails par code.
    """
    yearly = defaultdict(lambda: {
        'add': 0,
        'del': 0,
        'codes': defaultdict(lambda: {'add': 0, 'del': 0, 'commits': 0})
    })

    for code in data['codes']:
        code_name = code['name']

        for commit in code['commits']:
            ts = commit['ts']
            dt = datetime.fromtimestamp(ts / 1000)
            year = dt.year

            yearly[year]['add'] += commit['add']
            yearly[year]['del'] += commit['del']
            yearly[year]['codes'][code_name]['add'] += commit['add']
            yearly[year]['codes'][code_name]['del'] += commit['del']
            yearly[year]['codes'][code_name]['commits'] += 1

    # Convertir en liste triée
    result = []
    for year in sorted(yearly.keys()):
        # Trier les codes par nombre de modifications (desc)
        codes_list = []
        for code_name, code_data in yearly[year]['codes'].items():
            codes_list.append({
                'name': code_name,
                'add': code_data['add'],
                'del': code_data['del'],
                'commits': code_data['commits']
            })
        codes_list.sort(key=lambda c: c['add'] + c['del'], reverse=True)

        total_commits = sum(c['commits'] for c in codes_list)

        result.append({
            'year': year,
            'add': yearly[year]['add'],
            'del': yearly[year]['del'],
            'commits': total_commits,
            'codes': codes_list
        })

    return result


def format_number(n: int) -> str:
    """Formate un nombre avec séparateur de milliers"""
    return f"{n:,}".replace(',', ' ')


def generate_bar(value: int, max_value: int, height: int = 10, up: bool = True) -> list:
    """
    Génère les lignes d'une barre verticale en block elements.
    Retourne une liste de caractères (un par ligne).
    """
    if max_value == 0:
        return [' '] * height

    # Calculer combien de "blocs" on remplit
    ratio = value / max_value
    filled = ratio * height

    full_blocks = int(filled)
    remainder = filled - full_blocks

    # Caractères de bloc fractionnaires (du plus petit au plus grand)
    # Pour le haut (additions): on remplit de bas en haut
    # Pour le bas (deletions): on remplit de haut en bas
    blocks_top = [' ', '▁', '▂', '▃', '▄', '▅', '▆', '▇', '█']
    blocks_bot = [' ', '▔', '▔', '▀', '▀', '▀', '▀', '▀', '█']

    lines = []
    for i in range(height):
        if up:
            # De haut en bas, les indices vont de height-1 à 0
            # La barre se remplit de bas en haut
            pos = height - 1 - i
            if pos < full_blocks:
                lines.append('█')
            elif pos == full_blocks and remainder > 0:
                idx = int(remainder * 8)
                lines.append(blocks_top[idx])
            else:
                lines.append(' ')
        else:
            # De haut en bas, la barre se remplit de haut en bas
            pos = i
            if pos < full_blocks:
                lines.append('█')
            elif pos == full_blocks and remainder > 0:
                idx = int(remainder * 8)
                lines.append(blocks_bot[idx])
            else:
                lines.append(' ')

    return lines


def generate_html(yearly_data: list, metadata: dict) -> str:
    """Génère le fichier HTML avec le graphe en block elements"""

    if not yearly_data:
        return '<html><body>Aucune donnée</body></html>'

    # Calculer les max pour l'échelle
    max_add = max(d['add'] for d in yearly_data)
    max_del = max(d['del'] for d in yearly_data)
    max_value = max(max_add, max_del)

    bar_height = 12  # Nombre de lignes par demi-graphe

    # Totaux
    total_add = sum(d['add'] for d in yearly_data)
    total_del = sum(d['del'] for d in yearly_data)

    # Générer le CSS
    css = '''
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: monospace; font-size: 14px; line-height: 1; color: #222; background: #fff; padding: 20px; }
.chart { display: inline-block; }
.row { display: flex; height: 1.2em; }
.cell { width: 2ch; text-align: center; }
.bar-col { position: relative; }
.bar-col:hover { background: #f0f0f0; }
.year-label { font-size: 11px; writing-mode: vertical-rl; text-orientation: mixed; transform: rotate(180deg); height: 4em; }
.axis { border-top: 1px solid #222; }
.info-zone { height: 3em; margin-top: 1em; font-size: 13px; }
.info { display: none; }
.bar-col:hover .info { display: block; position: fixed; bottom: 20px; left: 20px; right: 20px; }
.y-axis { text-align: right; padding-right: 1ch; font-size: 11px; color: #666; width: 10ch; }
.title { margin-bottom: 1em; }
.footer { margin-top: 2em; font-size: 12px; color: #666; }
'''

    # Construire les lignes du graphe
    # Structure: pour chaque année, on a une colonne avec les additions en haut et les délétions en bas

    # Générer les barres pour chaque année
    bars_add = []
    bars_del = []
    for year_data in yearly_data:
        bars_add.append(generate_bar(year_data['add'], max_value, bar_height, up=True))
        bars_del.append(generate_bar(year_data['del'], max_value, bar_height, up=False))

    # Labels Y-axis (on met quelques graduations)
    y_labels_add = [''] * bar_height
    y_labels_del = [''] * bar_height
    for i in [0, bar_height // 2, bar_height - 1]:
        val = int(max_value * (bar_height - i) / bar_height)
        y_labels_add[i] = format_number(val)
    for i in [0, bar_height // 2, bar_height - 1]:
        val = int(max_value * (i + 1) / bar_height)
        y_labels_del[i] = format_number(val)

    # Générer le HTML du graphe
    html_parts = []
    html_parts.append('<!DOCTYPE html>')
    html_parts.append('<html lang="fr">')
    html_parts.append('<head>')
    html_parts.append('<meta charset="UTF-8">')
    html_parts.append('<meta name="viewport" content="width=device-width, initial-scale=1.0">')
    html_parts.append('<title>Lexflation</title>')
    html_parts.append(f'<style>{css}</style>')
    html_parts.append('</head>')
    html_parts.append('<body>')
    html_parts.append('<div class="title">Évolution des codes législatifs français (lignes modifiées par an)</div>')
    html_parts.append('<div class="chart">')

    # Partie additions (haut)
    for row_idx in range(bar_height):
        html_parts.append('<div class="row">')
        html_parts.append(f'<div class="y-axis">{y_labels_add[row_idx]}</div>')
        for col_idx, year_data in enumerate(yearly_data):
            char = bars_add[col_idx][row_idx]
            info_html = ''
            if row_idx == 0:
                # Info popup pour cette année
                net = year_data['add'] - year_data['del']
                net_str = f"+{format_number(net)}" if net >= 0 else format_number(net)
                top_codes = year_data['codes'][:5]
                codes_str = ', '.join([f"{c['name']}" for c in top_codes])
                info_html = f'''<div class="info">{year_data['year']}: +{format_number(year_data['add'])} / -{format_number(year_data['del'])} (net: {net_str}) | {year_data['commits']} commits | Top: {escape(codes_str)}</div>'''
            html_parts.append(f'<div class="cell bar-col">{char}{info_html}</div>')
        html_parts.append('</div>')

    # Ligne de base (axe X = 0)
    html_parts.append('<div class="row axis">')
    html_parts.append('<div class="y-axis">0</div>')
    for year_data in yearly_data:
        html_parts.append('<div class="cell bar-col"> </div>')
    html_parts.append('</div>')

    # Partie délétions (bas)
    for row_idx in range(bar_height):
        html_parts.append('<div class="row">')
        html_parts.append(f'<div class="y-axis">{y_labels_del[row_idx]}</div>')
        for col_idx, year_data in enumerate(yearly_data):
            char = bars_del[col_idx][row_idx]
            html_parts.append(f'<div class="cell bar-col">{char}</div>')
        html_parts.append('</div>')

    # Labels années
    html_parts.append('<div class="row">')
    html_parts.append('<div class="y-axis"></div>')
    for year_data in yearly_data:
        year_short = str(year_data['year'])[2:]  # Juste les 2 derniers chiffres
        html_parts.append(f'<div class="cell">{year_short}</div>')
    html_parts.append('</div>')

    html_parts.append('</div>')  # fin chart

    # Zone info (hint)
    html_parts.append('<div class="info-zone">(survoler une colonne pour voir les détails)</div>')

    # Footer
    html_parts.append(f'<div class="footer">')
    html_parts.append(f'Total: +{format_number(total_add)} / -{format_number(total_del)} lignes | ')
    html_parts.append(f'{metadata["total_codes"]} codes | ')
    html_parts.append(f'{metadata["total_commits"]} commits | ')
    html_parts.append(f'<a href="https://git.tricoteuses.fr/codes">git.tricoteuses.fr</a>')
    html_parts.append('</div>')

    html_parts.append('</body>')
    html_parts.append('</html>')

    return '\n'.join(html_parts)


def main():
    """Fonction principale"""
    print("Génération de l'histogramme en Block Elements...")

    script_dir = Path(__file__).parent
    data_file = script_dir.parent / 'docs' / 'data' / 'codes_data.json'
    html_file = script_dir.parent / 'docs' / 'index.html'

    # Charger les données
    print(f"Chargement de {data_file}...")
    data = load_data(data_file)
    print(f"  {data['metadata']['total_codes']} codes, {data['metadata']['total_commits']} commits")

    # Agréger par année
    print("Agrégation par année...")
    yearly_data = aggregate_by_year(data)
    print(f"  {len(yearly_data)} années de données")

    # Générer le HTML
    print("Génération du HTML...")
    html = generate_html(yearly_data, data['metadata'])
    with open(html_file, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"  -> {html_file.name}: {html_file.stat().st_size / 1024:.1f} Ko")

    print("Terminé!")


if __name__ == '__main__':
    main()
