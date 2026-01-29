#!/usr/bin/env python3
"""
Génère un histogramme en Block Elements (caractères Unicode) à partir des données des codes législatifs.
Agrège les additions/délétions par année, affiche le delta net.
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
        net = yearly[year]['add'] - yearly[year]['del']

        result.append({
            'year': year,
            'add': yearly[year]['add'],
            'del': yearly[year]['del'],
            'net': net,
            'commits': total_commits,
            'codes': codes_list
        })

    return result


def format_number(n: int) -> str:
    """Formate un nombre avec séparateur de milliers"""
    return f"{n:,}".replace(',', ' ')


def generate_html(yearly_data: list, metadata: dict) -> str:
    """Génère le fichier HTML avec le graphe en block elements"""

    if not yearly_data:
        return '<html><body>Aucune donnée</body></html>'

    # Calculer les max pour l'échelle (basé sur le delta net)
    max_positive = max((d['net'] for d in yearly_data if d['net'] > 0), default=0)
    max_negative = min((d['net'] for d in yearly_data if d['net'] < 0), default=0)
    max_abs = max(abs(max_positive), abs(max_negative))

    bar_height = 10  # Nombre de lignes par demi-graphe

    # Totaux
    total_add = sum(d['add'] for d in yearly_data)
    total_del = sum(d['del'] for d in yearly_data)
    total_net = total_add - total_del

    # Générer le CSS
    # Couleurs inversées: rouge pour +, vert pour -
    css = '''
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: monospace; font-size: 14px; line-height: 1; color: #222; background: #fff; padding: 20px; }
.chart { display: flex; align-items: flex-start; }
.y-axis { display: flex; flex-direction: column; text-align: right; padding-right: 0.5ch; font-size: 11px; color: #666; width: 12ch; }
.y-label { height: 1.2em; display: flex; align-items: center; justify-content: flex-end; }
.columns { display: flex; align-items: flex-start; }
.col { display: flex; flex-direction: column; width: 2ch; position: relative; }
.col:hover { background: #eee; }
.cell { height: 1.2em; text-align: center; line-height: 1.2em; }
.pos { color: #cf222e; }
.neg { color: #2ea043; }
.axis { height: 1.2em; border-bottom: 1px solid #222; }
.year-row { display: flex; margin-left: 12ch; }
.year-cell { width: 2ch; text-align: center; font-size: 10px; color: #666; }
.info-area { margin-top: 1em; font-size: 12px; color: #666; min-height: 1.5em; }
.info { display: none; position: absolute; left: 0; bottom: -3em; white-space: nowrap; background: #fff; z-index: 10; padding: 2px 0; }
.col:hover .info { display: block; }
.title { margin-bottom: 1em; }
.footer { margin-top: 2em; font-size: 12px; color: #666; }
a { color: #666; }
'''

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
    html_parts.append('<div class="title">Évolution des codes législatifs français (delta net par an)</div>')

    # Chart container
    html_parts.append('<div class="chart">')

    # Y-axis labels
    html_parts.append('<div class="y-axis">')
    for i in range(bar_height):
        val = int(max_abs * (bar_height - i) / bar_height)
        if i == 0:
            label = f"+{format_number(val)}"
        elif i == bar_height - 1:
            label = f"+{format_number(int(max_abs / bar_height))}"
        else:
            label = ""
        html_parts.append(f'<div class="y-label">{label}</div>')
    # Axis line (0)
    html_parts.append('<div class="y-label axis">0</div>')
    for i in range(bar_height):
        val = int(max_abs * (i + 1) / bar_height)
        if i == 0:
            label = f"-{format_number(int(max_abs / bar_height))}"
        elif i == bar_height - 1:
            label = f"-{format_number(val)}"
        else:
            label = ""
        html_parts.append(f'<div class="y-label">{label}</div>')
    html_parts.append('</div>')

    # Columns
    html_parts.append('<div class="columns">')
    for year_data in yearly_data:
        net = year_data['net']

        # Calculate bar height (au moins 1 si non-zéro)
        if max_abs == 0 or net == 0:
            bar_cells_count = 0
        else:
            bar_cells_count = max(1, round(abs(net) / max_abs * bar_height))

        # Generate column cells
        html_parts.append('<div class="col">')

        # Top half (positive values go up)
        for i in range(bar_height):
            pos = bar_height - 1 - i  # Position from bottom of top section
            if net > 0 and pos < bar_cells_count:
                html_parts.append('<div class="cell pos">█</div>')
            else:
                html_parts.append('<div class="cell"> </div>')

        # Axis line
        html_parts.append('<div class="cell axis"> </div>')

        # Bottom half (negative values go down)
        for i in range(bar_height):
            if net < 0 and i < bar_cells_count:
                html_parts.append('<div class="cell neg">█</div>')
            else:
                html_parts.append('<div class="cell"> </div>')

        # Info popup - liste TOUS les codes
        net_str = f"+{format_number(net)}" if net >= 0 else format_number(net)
        color = "#cf222e" if net >= 0 else "#2ea043"
        # Liste tous les codes modifiés cette année
        all_codes = year_data['codes']
        codes_str = ', '.join([c['name'] for c in all_codes])
        info_html = f'<div class="info" style="color:{color}">{year_data["year"]}: {net_str} lignes | {year_data["commits"]} commits | {escape(codes_str)}</div>'
        html_parts.append(info_html)

        html_parts.append('</div>')  # end col

    html_parts.append('</div>')  # end columns
    html_parts.append('</div>')  # end chart

    # Year labels (every 5 years)
    html_parts.append('<div class="year-row">')
    for year_data in yearly_data:
        year = year_data['year']
        if year % 5 == 0:
            html_parts.append(f'<div class="year-cell">{year}</div>')
        else:
            html_parts.append('<div class="year-cell"></div>')
    html_parts.append('</div>')

    # Info area hint
    html_parts.append('<div class="info-area">(survoler une colonne)</div>')

    # Footer
    net_str = f"+{format_number(total_net)}" if total_net >= 0 else format_number(total_net)
    html_parts.append(f'<div class="footer">')
    html_parts.append(f'Total: {net_str} lignes | ')
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
