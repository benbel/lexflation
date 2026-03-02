#!/usr/bin/env python3
"""
Génère un histogramme SVG à partir des données des codes législatifs.
Agrège les additions/délétions par année, affiche le delta net cumulatif.
Produit: index.html (page autonome)
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
    """Génère le fichier HTML avec le graphe en SVG"""

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

    # Chart dimensions - calculated dynamically based on data
    num_years = len(yearly_data)
    target_width = 1400  # Target width in pixels
    bar_height = 800     # Height in pixels
    cell_width = max(10, min(30, target_width // num_years)) if num_years > 0 else 25
    label_height = 20    # Vertical space for year labels above and below chart

    # Year label frequency - adapt based on number of years and column width
    # Show fewer labels when columns are narrow to avoid overlap
    if cell_width < 15:
        year_label_interval = 10
    elif cell_width < 20:
        year_label_interval = 5
    else:
        year_label_interval = 5

    chart_width = num_years * cell_width
    svg_height = label_height + bar_height + label_height

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
g.col:hover {{ opacity: 0.7; cursor: default; }}
.info-header {{ font-weight: bold; margin-bottom: 0.5em; }}
.info-codes {{ font-size: 12px; color: #444; }}
.info-codes div {{ padding: 1px 0; display: flex; }}
.code-delta {{ display: inline-block; min-width: 10ch; text-align: right; margin-right: 0.5em; }}
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
    html_parts.append('<div class="title">Inflation normative</div>')
    html_parts.append(f'<div class="subtitle">Total: {net_str} lignes | {metadata["total_codes"]} codes | {metadata["total_commits"]} modifications | <a href="https://git.tricoteuses.fr/codes">git.tricoteuses.fr</a></div>')
    html_parts.append('</div>')

    # Main layout: graph on left, info on right
    html_parts.append('<div class="main-layout">')
    html_parts.append('<div class="graph-section">')

    # SVG chart — one <rect> per year instead of 800 <div class="cell"> per year
    svg_parts = []
    svg_parts.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{chart_width}" height="{svg_height}" viewBox="0 0 {chart_width} {svg_height}">')

    for idx, year_data in enumerate(yearly_data):
        year = year_data['year']
        net = year_data['net']
        cumul_start = year_data['cumul_start']
        cumul_end = year_data['cumul_end']

        x = idx * cell_width

        # Convert cumulative values to pixel positions (0 at bottom, bar_height at top)
        if max_abs == 0:
            start_pos = 0.0
            end_pos = 0.0
        else:
            start_pos = cumul_start / max_abs * bar_height
            end_pos = cumul_end / max_abs * bar_height

        # Determine the range to fill (from min to max of start/end)
        fill_min = min(start_pos, end_pos)
        fill_max = max(start_pos, end_pos)

        # Ensure at least 1px height for every year
        if fill_max - fill_min < 1:
            fill_max = fill_min + 1

        # SVG y=0 is at top; chart area is offset by label_height
        rect_y = label_height + (bar_height - fill_max)
        rect_h = fill_max - fill_min

        color = "#cf222e" if net >= 0 else "#2ea043"

        # Build info HTML (same content as before, stored in data-info; read by JS on hover)
        net_str_year = f"+{format_number(net)}" if net >= 0 else format_number(net)
        info_lines = []
        info_lines.append(f'<div class="info-header" style="color:{color}">{year}: {net_str_year} lignes ({year_data["commits"]} modifications)</div>')
        info_lines.append('<div class="info-codes">')
        for code in year_data['codes']:
            code_net = code['add'] - code['del']
            code_net_str = f"+{format_number(code_net)}" if code_net >= 0 else format_number(code_net)
            code_color = "#cf222e" if code_net >= 0 else "#2ea043"
            info_lines.append(f'<div><span class="code-delta" style="color:{code_color}">{code_net_str}</span><span>{escape(code["name"])}</span></div>')
        info_lines.append('</div>')
        info_html = ''.join(info_lines)

        svg_parts.append(f'<g class="col" data-year="{year}" data-info="{escape(info_html)}">')

        # Transparent rect covering the full column height ensures hover works in empty areas
        svg_parts.append(f'<rect x="{x}" y="{label_height}" width="{cell_width}" height="{bar_height}" fill="transparent"/>')

        # The bar
        svg_parts.append(f'<rect x="{x}" y="{rect_y:.4f}" width="{cell_width}" height="{rect_h:.4f}" fill="{color}"/>')

        # Year labels at top and bottom
        if year % year_label_interval == 0:
            text_x = x + cell_width / 2
            svg_parts.append(f'<text x="{text_x:.1f}" y="{label_height - 5}" text-anchor="middle" font-size="10" font-family="JetBrains Mono, monospace" fill="#666">{year}</text>')
            svg_parts.append(f'<text x="{text_x:.1f}" y="{label_height + bar_height + 14}" text-anchor="middle" font-size="10" font-family="JetBrains Mono, monospace" fill="#666">{year}</text>')

        svg_parts.append('</g>')

    svg_parts.append('</svg>')
    html_parts.append('\n'.join(svg_parts))

    html_parts.append('</div>')  # end graph-section

    # Info section (right side) - container for tooltip display
    html_parts.append('<div class="info-section" id="info-display"></div>')

    html_parts.append('</div>')  # end main-layout

    # JavaScript to display info in right column on hover
    js_code = '''
<script>
document.querySelectorAll('g.col').forEach(col => {
    const display = document.getElementById('info-display');
    if (display) {
        col.addEventListener('mouseenter', () => {
            display.innerHTML = col.dataset.info;
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
    print("Génération de l'histogramme SVG...")

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
