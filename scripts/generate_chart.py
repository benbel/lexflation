#!/usr/bin/env python3
"""
Génère un histogramme SVG statique à partir des données des codes législatifs.
Agrège les additions/délétions par mois et produit un fichier HTML autonome.
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


def aggregate_by_month(data: dict) -> list:
    """
    Agrège tous les commits de tous les codes par mois.
    Retourne une liste de dicts avec les totaux et les détails par code.
    """
    monthly = defaultdict(lambda: {
        'add': 0,
        'del': 0,
        'codes': defaultdict(lambda: {'add': 0, 'del': 0, 'commits': []})
    })

    for code in data['codes']:
        code_name = code['name']
        code_slug = code['slug']

        for commit in code['commits']:
            ts = commit['ts']
            dt = datetime.fromtimestamp(ts / 1000)
            month_key = f"{dt.year}-{dt.month:02d}"

            monthly[month_key]['add'] += commit['add']
            monthly[month_key]['del'] += commit['del']
            monthly[month_key]['codes'][code_name]['add'] += commit['add']
            monthly[month_key]['codes'][code_name]['del'] += commit['del']
            monthly[month_key]['codes'][code_name]['commits'].append({
                'url': commit['url'],
                'msg': commit['msg'],
                'add': commit['add'],
                'del': commit['del']
            })
            monthly[month_key]['codes'][code_name]['slug'] = code_slug

    # Convertir en liste triée
    result = []
    for month_key in sorted(monthly.keys()):
        year, month = map(int, month_key.split('-'))

        # Trier les codes par nombre de modifications (desc)
        codes_list = []
        for code_name, code_data in monthly[month_key]['codes'].items():
            codes_list.append({
                'name': code_name,
                'slug': code_data['slug'],
                'add': code_data['add'],
                'del': code_data['del'],
                'commits': code_data['commits']
            })
        codes_list.sort(key=lambda c: c['add'] + c['del'], reverse=True)

        result.append({
            'month_key': month_key,
            'year': year,
            'month': month,
            'add': monthly[month_key]['add'],
            'del': monthly[month_key]['del'],
            'codes': codes_list
        })

    return result


def format_month_name(month: int, year: int) -> str:
    """Formate le nom du mois en français"""
    months_fr = [
        '', 'janvier', 'février', 'mars', 'avril', 'mai', 'juin',
        'juillet', 'août', 'septembre', 'octobre', 'novembre', 'décembre'
    ]
    return f"{months_fr[month]} {year}"


def format_number(n: int) -> str:
    """Formate un nombre avec séparateur de milliers"""
    return f"{n:,}".replace(',', ' ')


def generate_svg_chart(monthly_data: list, width: int = 1200, height: int = 400) -> str:
    """Génère le code SVG de l'histogramme"""

    margin = {'top': 20, 'right': 30, 'bottom': 60, 'left': 80}
    inner_width = width - margin['left'] - margin['right']
    inner_height = height - margin['top'] - margin['bottom']

    if not monthly_data:
        return '<svg><text>Aucune donnée</text></svg>'

    # Calculer les échelles
    max_value = max(
        max(d['add'] for d in monthly_data),
        max(d['del'] for d in monthly_data)
    )

    n_bars = len(monthly_data)
    bar_width = inner_width / n_bars * 0.9
    bar_gap = inner_width / n_bars * 0.1

    def x_pos(i):
        return margin['left'] + i * (bar_width + bar_gap)

    def y_pos(value):
        # 0 est au milieu, positif vers le haut, négatif vers le bas
        mid = margin['top'] + inner_height / 2
        scale = (inner_height / 2) / max_value if max_value > 0 else 1
        return mid - value * scale

    # Construire le SVG
    svg_parts = []
    svg_parts.append(f'<svg class="chart-svg" viewBox="0 0 {width} {height}" preserveAspectRatio="xMidYMid meet">')

    # Ligne de base (y = 0)
    baseline_y = y_pos(0)
    svg_parts.append(f'<line class="baseline" x1="{margin["left"]}" x2="{width - margin["right"]}" y1="{baseline_y}" y2="{baseline_y}"/>')

    # Axe Y - graduations
    for i in range(5):
        value = int(max_value * (i + 1) / 5)
        y_up = y_pos(value)
        y_down = y_pos(-value)

        # Lignes de grille
        svg_parts.append(f'<line class="grid-line" x1="{margin["left"]}" x2="{width - margin["right"]}" y1="{y_up}" y2="{y_up}"/>')
        svg_parts.append(f'<line class="grid-line" x1="{margin["left"]}" x2="{width - margin["right"]}" y1="{y_down}" y2="{y_down}"/>')

        # Labels
        label = format_number(value)
        svg_parts.append(f'<text class="y-label" x="{margin["left"] - 10}" y="{y_up + 4}">{label}</text>')
        svg_parts.append(f'<text class="y-label" x="{margin["left"] - 10}" y="{y_down + 4}">{label}</text>')

    # Label axe Y
    svg_parts.append(f'<text class="axis-title" transform="rotate(-90)" x="{-height/2}" y="20">Lignes modifiées</text>')

    # Barres et tooltips
    for i, month in enumerate(monthly_data):
        x = x_pos(i)

        # Hauteurs des barres
        add_height = (month['add'] / max_value) * (inner_height / 2) if max_value > 0 else 0
        del_height = (month['del'] / max_value) * (inner_height / 2) if max_value > 0 else 0

        # Groupe pour la barre avec tooltip
        svg_parts.append(f'<g class="bar-group" data-month="{month["month_key"]}">')

        # Zone interactive (invisible, couvre toute la hauteur)
        svg_parts.append(f'<rect class="hit-area" x="{x}" y="{margin["top"]}" width="{bar_width}" height="{inner_height}"/>')

        # Barre additions (vers le haut)
        if month['add'] > 0:
            svg_parts.append(f'<rect class="bar bar-add" x="{x}" y="{baseline_y - add_height}" width="{bar_width}" height="{add_height}"/>')

        # Barre délétions (vers le bas)
        if month['del'] > 0:
            svg_parts.append(f'<rect class="bar bar-del" x="{x}" y="{baseline_y}" width="{bar_width}" height="{del_height}"/>')

        # Tooltip
        month_name = format_month_name(month['month'], month['year'])
        net = month['add'] - month['del']
        net_class = 'net-positive' if net >= 0 else 'net-negative'
        net_str = f"+{format_number(net)}" if net >= 0 else format_number(net)

        tooltip_html = f'''<div class="tooltip-content">
            <div class="tooltip-title">{escape(month_name)}</div>
            <div class="tooltip-stats">
                <span class="stat-add">+{format_number(month['add'])}</span>
                <span class="stat-del">-{format_number(month['del'])}</span>
            </div>
            <div class="tooltip-net {net_class}">Net: {net_str}</div>'''

        # Ajouter les liens vers les commits (top 8 max)
        all_commits = []
        for code in month['codes']:
            for commit in code['commits']:
                all_commits.append({
                    'code_name': code['name'],
                    'url': commit['url'],
                    'msg': commit['msg'][:50] + '...' if len(commit['msg']) > 50 else commit['msg'],
                    'add': commit['add'],
                    'del': commit['del']
                })
        # Trier par importance (add + del)
        all_commits.sort(key=lambda c: c['add'] + c['del'], reverse=True)

        if all_commits:
            tooltip_html += '<div class="tooltip-commits">'
            for commit in all_commits[:8]:
                tooltip_html += f'''<div class="tooltip-commit">
                    <a href="{commit['url']}" target="_blank" rel="noopener">{escape(commit['code_name'])}</a>
                    <span class="commit-stats">+{commit['add']}/-{commit['del']}</span>
                </div>'''

            if len(all_commits) > 8:
                tooltip_html += f'<div class="tooltip-more">+{len(all_commits) - 8} autres commits</div>'
            tooltip_html += '</div>'

        tooltip_html += '</div>'

        svg_parts.append(f'<foreignObject class="tooltip-container" x="{x}" y="0" width="320" height="{height}">{tooltip_html}</foreignObject>')
        svg_parts.append('</g>')

    # Axe X - quelques dates repères
    tick_interval = max(1, len(monthly_data) // 15)
    for i, month in enumerate(monthly_data):
        if i % tick_interval == 0:
            x = x_pos(i) + bar_width / 2
            label = f"{month['month']:02d}/{month['year']}"
            svg_parts.append(f'<text class="x-label" x="{x}" y="{height - margin["bottom"] + 20}" transform="rotate(-45 {x} {height - margin["bottom"] + 20})">{label}</text>')

    svg_parts.append('</svg>')

    return '\n'.join(svg_parts)


def generate_html(monthly_data: list, metadata: dict) -> str:
    """Génère le fichier HTML complet"""

    svg_chart = generate_svg_chart(monthly_data)

    # Calculer les statistiques globales
    total_add = sum(m['add'] for m in monthly_data)
    total_del = sum(m['del'] for m in monthly_data)

    html = f'''<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Évolution des codes législatifs français</title>
    <meta name="description" content="Histogramme mensuel de l'évolution des codes législatifs français">
    <style>
/* Reset */
* {{
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}}

:root {{
    --color-bg: #ffffff;
    --color-text: #24292f;
    --color-text-secondary: #57606a;
    --color-border: #d0d7de;
    --color-add: #2ea043;
    --color-del: #cf222e;
    --color-hover: #f6f8fa;
    --font-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
    --font-mono: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Monaco, Consolas, monospace;
}}

body {{
    font-family: var(--font-sans);
    font-size: 14px;
    line-height: 1.5;
    color: var(--color-text);
    background: var(--color-bg);
}}

.container {{
    max-width: 1400px;
    margin: 0 auto;
    padding: 20px;
}}

/* Header */
.header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 16px 20px;
    background: var(--color-hover);
    border: 1px solid var(--color-border);
    border-radius: 8px;
    margin-bottom: 20px;
    flex-wrap: wrap;
    gap: 16px;
}}

.page-title {{
    font-size: 18px;
    font-weight: 600;
}}

.legend {{
    display: flex;
    gap: 20px;
}}

.legend-item {{
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 13px;
    color: var(--color-text-secondary);
}}

.legend-color {{
    width: 16px;
    height: 16px;
    border-radius: 3px;
    border: 1px solid var(--color-border);
}}

.legend-color.add {{ background: var(--color-add); }}
.legend-color.del {{ background: var(--color-del); }}

/* Chart */
.chart-container {{
    background: var(--color-bg);
    border: 1px solid var(--color-border);
    border-radius: 8px;
    padding: 20px;
}}

.chart-svg {{
    width: 100%;
    display: block;
}}

.baseline {{
    stroke: var(--color-border);
    stroke-width: 1;
}}

.grid-line {{
    stroke: var(--color-border);
    stroke-width: 0.5;
    stroke-dasharray: 4 4;
    opacity: 0.5;
}}

.y-label {{
    font-size: 10px;
    fill: var(--color-text-secondary);
    text-anchor: end;
}}

.x-label {{
    font-size: 10px;
    fill: var(--color-text-secondary);
    text-anchor: end;
}}

.axis-title {{
    font-size: 12px;
    fill: var(--color-text-secondary);
    text-anchor: middle;
}}

.bar-add {{
    fill: var(--color-add);
    fill-opacity: 0.7;
}}

.bar-del {{
    fill: var(--color-del);
    fill-opacity: 0.7;
}}

.hit-area {{
    fill: transparent;
    cursor: pointer;
}}

.bar-group:hover .bar-add {{
    fill-opacity: 1;
}}

.bar-group:hover .bar-del {{
    fill-opacity: 1;
}}

/* Tooltip */
.tooltip-container {{
    pointer-events: none;
    overflow: visible;
}}

.tooltip-content {{
    display: none;
    position: absolute;
    left: 100%;
    top: 50px;
    margin-left: 10px;
    background: rgba(255, 255, 255, 0.98);
    border: 1px solid var(--color-border);
    border-radius: 6px;
    padding: 12px;
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
    width: 280px;
    font-size: 12px;
    pointer-events: auto;
}}

.bar-group:hover .tooltip-content {{
    display: block;
}}

.tooltip-title {{
    font-weight: 600;
    font-size: 14px;
    margin-bottom: 8px;
    text-transform: capitalize;
}}

.tooltip-stats {{
    display: flex;
    gap: 16px;
    margin-bottom: 6px;
    font-family: var(--font-mono);
    font-size: 13px;
}}

.stat-add {{
    color: var(--color-add);
    font-weight: 600;
}}

.stat-del {{
    color: var(--color-del);
    font-weight: 600;
}}

.tooltip-net {{
    font-family: var(--font-mono);
    font-size: 12px;
    color: var(--color-text-secondary);
    padding-bottom: 8px;
    border-bottom: 1px solid var(--color-border);
    margin-bottom: 8px;
}}

.net-positive {{
    color: var(--color-add);
}}

.net-negative {{
    color: var(--color-del);
}}

.tooltip-commits {{
    display: flex;
    flex-direction: column;
    gap: 4px;
}}

.tooltip-commit {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 8px;
    font-size: 11px;
}}

.tooltip-commit a {{
    flex: 1;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    color: #0969da;
    text-decoration: none;
}}

.tooltip-commit a:hover {{
    text-decoration: underline;
}}

.commit-stats {{
    font-family: var(--font-mono);
    color: var(--color-text-secondary);
    font-size: 10px;
    white-space: nowrap;
}}

.tooltip-more {{
    font-size: 11px;
    color: var(--color-text-secondary);
    font-style: italic;
    margin-top: 4px;
}}

/* Footer */
.footer {{
    margin-top: 20px;
    padding: 12px 16px;
    background: var(--color-hover);
    border: 1px solid var(--color-border);
    border-radius: 8px;
    font-size: 12px;
    color: var(--color-text-secondary);
}}

.footer-stats {{
    display: flex;
    gap: 20px;
    flex-wrap: wrap;
}}

/* Responsive */
@media (max-width: 768px) {{
    .container {{
        padding: 10px;
    }}

    .header {{
        flex-direction: column;
        align-items: flex-start;
    }}

    .page-title {{
        font-size: 16px;
    }}
}}
    </style>
</head>
<body>
    <main class="container">
        <header class="header">
            <h1 class="page-title">Évolution mensuelle des codes législatifs français</h1>
            <div class="legend">
                <span class="legend-item">
                    <span class="legend-color add"></span>
                    <span>Additions</span>
                </span>
                <span class="legend-item">
                    <span class="legend-color del"></span>
                    <span>Délétions</span>
                </span>
            </div>
        </header>

        <div class="chart-container">
            {svg_chart}
        </div>

        <footer class="footer">
            <div class="footer-stats">
                <span>Total: +{format_number(total_add)} / -{format_number(total_del)} lignes</span>
                <span>{metadata['total_codes']} codes</span>
                <span>{metadata['total_commits']} commits</span>
                <span>Données: <a href="https://git.tricoteuses.fr/codes" target="_blank">git.tricoteuses.fr</a></span>
            </div>
        </footer>
    </main>
</body>
</html>'''

    return html


def main():
    """Fonction principale"""
    print("📊 Génération de l'histogramme SVG...")

    # Chemins
    script_dir = Path(__file__).parent
    data_file = script_dir.parent / 'docs' / 'data' / 'codes_data.json'
    output_file = script_dir.parent / 'docs' / 'index.html'

    # Charger les données
    print(f"📂 Chargement de {data_file}...")
    data = load_data(data_file)
    print(f"   {data['metadata']['total_codes']} codes, {data['metadata']['total_commits']} commits")

    # Agréger par mois
    print("⚙️  Agrégation par mois...")
    monthly_data = aggregate_by_month(data)
    print(f"   {len(monthly_data)} mois de données")

    # Générer le HTML
    print("🎨 Génération du HTML/SVG...")
    html = generate_html(monthly_data, data['metadata'])

    # Sauvegarder
    print(f"💾 Sauvegarde dans {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)

    file_size = output_file.stat().st_size / 1024
    print(f"✅ Fichier généré: {file_size:.1f} Ko")

    print("\n✨ Génération terminée!")


if __name__ == '__main__':
    main()
