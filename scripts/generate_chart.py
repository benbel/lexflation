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
        codes_list.sort(key=lambda c: c['add'] - c['del'], reverse=True)

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

    # Filter out 1970 (artifact from git system start)
    yearly_data = [d for d in yearly_data if d['year'] != 1970]

    if not yearly_data:
        return '<html><body>Aucune donnée</body></html>'

    # Calculate cumulative values for Kagi-style chart
    # Each year starts where the previous year ended
    cumulative = 0
    for d in yearly_data:
        d['cumul_start'] = cumulative
        cumulative += d['net']
        d['cumul_end'] = cumulative

    # Calculate max for scale based on cumulative range
    all_values = []
    for d in yearly_data:
        all_values.append(d['cumul_start'])
        all_values.append(d['cumul_end'])
    max_positive = max(all_values) if all_values else 0
    max_negative = min(all_values) if all_values else 0
    max_abs = max(abs(max_positive), abs(max_negative))

    # Target: ~1440px width (3/4 of 1080p), ~800px height
    # With 56 years: 1440/56 ≈ 25px per column
    bar_height = 800   # 800px height at 1px per cell
    cell_width = 25    # 25px per column
    cell_height = 1    # 1px per cell

    # Totaux
    total_add = sum(d['add'] for d in yearly_data)
    total_del = sum(d['del'] for d in yearly_data)
    total_net = total_add - total_del

    # Générer le CSS avec police web
    css = f'''
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400&display=swap');
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: 'JetBrains Mono', monospace; font-size: 14px; line-height: 1; color: #222; background: #fff; padding: 20px; }}
.header {{ margin-bottom: 1em; }}
.title {{ font-weight: bold; }}
.subtitle {{ font-size: 12px; color: #666; margin-top: 0.3em; }}
.subtitle a {{ color: #666; }}
.main-layout {{ display: flex; gap: 2em; }}
.graph-section {{ flex: 0 0 auto; }}
.info-section {{ flex: 1 1 auto; min-width: 300px; padding-top: 1em; }}
.chart-container {{ position: relative; }}
.columns {{ display: flex; align-items: flex-end; }}
.col {{ display: flex; flex-direction: column; width: {cell_width}px; position: relative; }}
.col:hover {{ opacity: 0.7; }}
.cell {{ height: {cell_height}px; width: {cell_width}px; }}
.pos {{ background-color: #cf222e; }}
.neg {{ background-color: #2ea043; }}
.year-label {{ font-size: 10px; color: #666; text-align: center; height: 1.5em; line-height: 1.5em; }}
.info {{ display: none; }}
.info-header {{ font-weight: bold; margin-bottom: 0.5em; }}
.info-codes {{ font-size: 12px; color: #444; }}
.info-codes div {{ padding: 1px 0; }}
a {{ color: #666; }}
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

    # Header with title and stats
    net_str = f"+{format_number(total_net)}" if total_net >= 0 else format_number(total_net)
    html_parts.append('<div class="header">')
    html_parts.append('<div class="title">Inflation législative</div>')
    html_parts.append(f'<div class="subtitle">Total: {net_str} lignes | {metadata["total_codes"]} codes | {metadata["total_commits"]} modifications | <a href="https://git.tricoteuses.fr/codes">git.tricoteuses.fr</a></div>')
    html_parts.append('</div>')

    # Main layout: graph on left, info on right
    html_parts.append('<div class="main-layout">')

    # Graph section
    html_parts.append('<div class="graph-section">')

    # Chart container
    html_parts.append('<div class="chart-container">')

    # Columns - Kagi-style: each column contains year label at top, bars, year label at bottom
    html_parts.append('<div class="columns">')
    for idx, year_data in enumerate(yearly_data):
        year = year_data['year']
        net = year_data['net']
        cumul_start = year_data['cumul_start']
        cumul_end = year_data['cumul_end']

        # Convert cumulative values to cell positions (0 at bottom, bar_height at top)
        if max_abs == 0:
            start_pos = 0
            end_pos = 0
        else:
            start_pos = cumul_start / max_abs * bar_height
            end_pos = cumul_end / max_abs * bar_height

        # Determine the range to fill (from min to max of start/end)
        fill_min = min(start_pos, end_pos)
        fill_max = max(start_pos, end_pos)

        # Ensure at least 1px height for every year
        if fill_max - fill_min < 1:
            fill_max = fill_min + 1

        # Generate column
        html_parts.append(f'<div class="col" data-year="{year}">')

        # Year label at top (every 5 years)
        if year % 5 == 0:
            html_parts.append(f'<div class="year-label">{year}</div>')
        else:
            html_parts.append('<div class="year-label"></div>')

        # Bar cells (from top to bottom, position bar_height-1 to 0)
        # Use background-color for filled cells
        for i in range(bar_height):
            cell_pos = bar_height - 1 - i  # Position from bottom (0 at bottom)

            # Cell is filled if its center is within the range
            cell_center = cell_pos + 0.5
            if fill_min <= cell_center < fill_max:
                color_class = "pos" if net >= 0 else "neg"
                html_parts.append(f'<div class="cell {color_class}"></div>')
            else:
                html_parts.append('<div class="cell"></div>')

        # Year label at bottom (every 5 years)
        if year % 5 == 0:
            html_parts.append(f'<div class="year-label">{year}</div>')
        else:
            html_parts.append('<div class="year-label"></div>')

        # Info popup - will be displayed in right column
        net_str_year = f"+{format_number(net)}" if net >= 0 else format_number(net)
        color = "#cf222e" if net >= 0 else "#2ea043"

        # Build info with line breaks
        info_lines = []
        info_lines.append(f'<div class="info-header" style="color:{color}">{year}: {net_str_year} lignes ({year_data["commits"]} modifications)</div>')
        info_lines.append('<div class="info-codes">')
        for code in year_data['codes']:
            code_net = code['add'] - code['del']
            code_net_str = f"+{format_number(code_net)}" if code_net >= 0 else format_number(code_net)
            code_color = "#cf222e" if code_net >= 0 else "#2ea043"
            info_lines.append(f'<div><span style="color:{code_color}">{code_net_str}</span> {escape(code["name"])}</div>')
        info_lines.append('</div>')

        info_html = f'<div class="info">{"".join(info_lines)}</div>'
        html_parts.append(info_html)

        html_parts.append('</div>')  # end col

    html_parts.append('</div>')  # end columns

    html_parts.append('</div>')  # end chart-container
    html_parts.append('</div>')  # end graph-section

    # Info section (right side) - container for tooltip display
    html_parts.append('<div class="info-section" id="info-display"></div>')

    html_parts.append('</div>')  # end main-layout

    # JavaScript to display info in right column on hover
    js_code = '''
<script>
document.querySelectorAll('.col').forEach(col => {
    const info = col.querySelector('.info');
    const display = document.getElementById('info-display');
    if (info && display) {
        col.addEventListener('mouseenter', () => {
            display.innerHTML = info.innerHTML;
        });
        col.addEventListener('mouseleave', () => {
            display.innerHTML = '';
        });
    }
});
</script>
'''
    html_parts.append(js_code)

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
