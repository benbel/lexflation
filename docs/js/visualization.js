// État global de l'application
let globalData = null;
let scaleMode = 'per-code'; // 'per-code' ou 'common'
let tooltipPinned = false;

// Dimensions des graphiques
const CHART_WIDTH = 800;
const CHART_HEIGHT = 120;
const MARGIN = { top: 5, right: 5, bottom: 5, left: 5 };

/**
 * Charge les données depuis le fichier JSON
 */
async function loadData() {
    try {
        const response = await fetch('data/codes_data.json');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Erreur lors du chargement des données:', error);
        throw error;
    }
}

/**
 * Calcule le score de modifications total pour un code (somme des valeurs absolues)
 */
function calculateModificationScore(code) {
    return code.commits.reduce((sum, commit) => sum + commit.add + commit.del, 0);
}

/**
 * Initialise l'application
 */
async function init() {
    try {
        // Charger les données
        globalData = await loadData();

        // Masquer le loading
        document.getElementById('loading').style.display = 'none';

        // Afficher les contrôles
        document.getElementById('controls').style.display = 'flex';

        // Afficher les graphiques
        document.getElementById('charts-container').style.display = 'flex';
        renderAllCharts(globalData);

        // Ajouter listener pour fermer le tooltip en cliquant ailleurs
        document.addEventListener('click', function(event) {
            const tooltip = document.getElementById('tooltip');
            if (tooltipPinned && !tooltip.contains(event.target) && !event.target.closest('.point')) {
                hideTooltip();
            }
        });

    } catch (error) {
        document.getElementById('loading').style.display = 'none';
        document.getElementById('error').style.display = 'block';
        console.error(error);
    }
}

/**
 * Crée les échelles communes pour tous les graphiques
 */
function createCommonScales(metadata) {
    const xScale = d3.scaleTime()
        .domain([metadata.earliest_commit, metadata.latest_commit])
        .range([MARGIN.left, CHART_WIDTH - MARGIN.right]);

    const maxValue = Math.max(metadata.max_additions, metadata.max_deletions);
    const yScale = d3.scaleLinear()
        .domain([-maxValue, maxValue])
        .range([CHART_HEIGHT - MARGIN.bottom, MARGIN.top]);

    return { xScale, yScale };
}

/**
 * Crée les échelles spécifiques pour un code
 */
function createCodeScales(code, metadata) {
    const xScale = d3.scaleTime()
        .domain([metadata.earliest_commit, metadata.latest_commit])
        .range([MARGIN.left, CHART_WIDTH - MARGIN.right]);

    const maxAdd = Math.max(...code.commits.map(c => c.add));
    const maxDel = Math.max(...code.commits.map(c => c.del));
    const maxValue = Math.max(maxAdd, maxDel, 1);

    const yScale = d3.scaleLinear()
        .domain([-maxValue, maxValue])
        .range([CHART_HEIGHT - MARGIN.bottom, MARGIN.top]);

    return { xScale, yScale };
}

/**
 * Rend tous les graphiques
 */
function renderAllCharts(data) {
    const container = document.getElementById('charts-container');
    container.innerHTML = ''; // Vider le conteneur

    // Trier les codes par score de modifications (décroissant)
    const sortedCodes = [...data.codes]
        .filter(code => code.commits.length > 0)
        .sort((a, b) => calculateModificationScore(b) - calculateModificationScore(a));

    const commonScales = createCommonScales(data.metadata);

    sortedCodes.forEach(code => {
        const scales = scaleMode === 'common'
            ? commonScales
            : createCodeScales(code, data.metadata);

        const chartCard = createChartCard(code, scales.xScale, scales.yScale);
        container.appendChild(chartCard);
    });
}

/**
 * Crée une carte de graphique pour un code
 */
function createChartCard(code, xScale, yScale) {
    const card = document.createElement('div');
    card.className = 'chart-card';

    const header = document.createElement('div');
    header.className = 'chart-header';

    const title = document.createElement('div');
    title.className = 'chart-title';
    title.textContent = code.name;
    title.title = code.name;

    header.appendChild(title);
    card.appendChild(header);

    const svg = createChart(code, xScale, yScale);
    card.appendChild(svg);

    return card;
}

/**
 * Crée le graphique SVG pour un code
 */
function createChart(code, xScale, yScale) {
    const svg = d3.create('svg')
        .attr('class', 'chart-svg')
        .attr('viewBox', `0 0 ${CHART_WIDTH} ${CHART_HEIGHT}`)
        .attr('preserveAspectRatio', 'xMidYMid meet');

    renderBrutMode(svg, code.commits, code, xScale, yScale);

    return svg.node();
}

/**
 * Rend le graphique en mode brut (additions + deletions séparées)
 */
function renderBrutMode(svg, commits, code, xScale, yScale) {
    // Préparer les données pour les areas
    const additionsData = commits.map(c => ({
        date: c.ts,
        value: c.add
    }));

    const deletionsData = commits.map(c => ({
        date: c.ts,
        value: -c.del
    }));

    // Area pour les additions (vert)
    const areaAdd = d3.area()
        .x(d => xScale(d.date))
        .y0(yScale(0))
        .y1(d => yScale(d.value))
        .curve(d3.curveStepAfter);

    svg.append('path')
        .datum(additionsData)
        .attr('fill', '#2ea043')
        .attr('fill-opacity', 0.3)
        .attr('stroke', '#2ea043')
        .attr('stroke-width', 1)
        .attr('d', areaAdd);

    // Area pour les deletions (rouge)
    const areaDel = d3.area()
        .x(d => xScale(d.date))
        .y0(yScale(0))
        .y1(d => yScale(d.value))
        .curve(d3.curveStepAfter);

    svg.append('path')
        .datum(deletionsData)
        .attr('fill', '#cf222e')
        .attr('fill-opacity', 0.3)
        .attr('stroke', '#cf222e')
        .attr('stroke-width', 1)
        .attr('d', areaDel);

    // Points interactifs
    addInteractivePoints(svg, commits, code, xScale, yScale);
}

/**
 * Ajoute les points interactifs pour le tooltip
 */
function addInteractivePoints(svg, commits, code, xScale, yScale) {
    const points = svg.selectAll('.point')
        .data(commits)
        .enter()
        .append('circle')
        .attr('class', 'point')
        .attr('cx', d => xScale(d.ts))
        .attr('cy', d => yScale(d.add > d.del ? d.add : -d.del))
        .attr('r', 4)
        .attr('fill', 'transparent')
        .attr('stroke', 'transparent')
        .style('cursor', 'pointer')
        .on('mouseenter', function(event, d) {
            if (!tooltipPinned) {
                d3.select(this)
                    .attr('fill', '#0969da')
                    .attr('r', 5);
                showTooltip(event, d, code);
            }
        })
        .on('mouseleave', function() {
            if (!tooltipPinned) {
                d3.select(this)
                    .attr('fill', 'transparent')
                    .attr('r', 4);
                hideTooltip();
            }
        })
        .on('click', function(event, d) {
            event.stopPropagation();

            // Réinitialiser tous les points
            svg.selectAll('.point')
                .attr('fill', 'transparent')
                .attr('r', 4);

            // Activer ce point
            d3.select(this)
                .attr('fill', '#0969da')
                .attr('r', 5);

            tooltipPinned = true;
            showTooltip(event, d, code);
        });
}

/**
 * Affiche le tooltip
 */
function showTooltip(event, commit, code) {
    const tooltip = document.getElementById('tooltip');

    const date = new Date(commit.ts);
    const dateStr = date.toLocaleDateString('fr-FR', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    });

    const statsHTML = `
        <div class="tooltip-stats">
            <span class="tooltip-add">+${commit.add}</span>
            <span class="tooltip-del">-${commit.del}</span>
        </div>
    `;

    // Construire l'URL Légifrance à partir du slug
    const legifranceUrl = `https://www.legifrance.gouv.fr/codes/texte_lc/${code.slug.toUpperCase()}`;

    tooltip.innerHTML = `
        <div class="tooltip-title">${commit.msg}</div>
        <div class="tooltip-date">${dateStr}</div>
        ${statsHTML}
        <div class="tooltip-links">
            <a href="${commit.url}" target="_blank">Voir sur git.tricoteuses.fr</a>
            <a href="${legifranceUrl}" target="_blank">Voir sur Légifrance</a>
        </div>
    `;

    tooltip.style.display = 'block';

    // Positionner le tooltip
    const x = event.pageX + 10;
    const y = event.pageY + 10;

    tooltip.style.left = x + 'px';
    tooltip.style.top = y + 'px';
}

/**
 * Masque le tooltip
 */
function hideTooltip() {
    const tooltip = document.getElementById('tooltip');
    tooltip.style.display = 'none';
    tooltipPinned = false;

    // Réinitialiser tous les points
    d3.selectAll('.point')
        .attr('fill', 'transparent')
        .attr('r', 4);
}

/**
 * Bascule entre l'échelle commune et l'échelle par code
 */
function toggleScale() {
    scaleMode = scaleMode === 'per-code' ? 'common' : 'per-code';

    // Mettre à jour le bouton
    const button = document.getElementById('toggle-scale');
    button.textContent = scaleMode === 'per-code' ? 'Échelle par code' : 'Échelle commune';
    button.title = scaleMode === 'per-code'
        ? 'Forcer une échelle commune pour tous les graphiques'
        : 'Utiliser une échelle calculée par code';

    // Re-rendre tous les graphiques
    if (globalData) {
        renderAllCharts(globalData);
    }
}

// Initialiser l'application au chargement de la page
document.addEventListener('DOMContentLoaded', init);
