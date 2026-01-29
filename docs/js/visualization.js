// État global de l'application
let globalData = null;
let tooltipPinned = false;

// Dimensions du graphique
const CHART_WIDTH = 1200;
const CHART_HEIGHT = 400;
const MARGIN = { top: 20, right: 30, bottom: 50, left: 70 };

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
 * Agrège les données de tous les codes par mois
 * @param {Array} codes - Liste des codes avec leurs commits
 * @returns {Array} Données agrégées par mois [{date, add, del, month}]
 */
function aggregateByMonth(codes) {
    const monthlyData = {};

    codes.forEach(code => {
        code.commits.forEach(commit => {
            const date = new Date(commit.ts);
            // Créer une clé pour le mois (YYYY-MM)
            const monthKey = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`;

            if (!monthlyData[monthKey]) {
                // Premier jour du mois pour la date
                monthlyData[monthKey] = {
                    date: new Date(date.getFullYear(), date.getMonth(), 1).getTime(),
                    add: 0,
                    del: 0,
                    monthKey: monthKey
                };
            }

            monthlyData[monthKey].add += commit.add;
            monthlyData[monthKey].del += commit.del;
        });
    });

    // Convertir en tableau et trier par date
    return Object.values(monthlyData).sort((a, b) => a.date - b.date);
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

        // Afficher le graphique
        document.getElementById('chart-container').style.display = 'block';
        renderChart(globalData);

        // Ajouter listener pour fermer le tooltip en cliquant ailleurs
        document.addEventListener('click', function(event) {
            const tooltip = document.getElementById('tooltip');
            if (tooltipPinned && !tooltip.contains(event.target) && !event.target.closest('.bar')) {
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
 * Rend l'histogramme mensuel
 */
function renderChart(data) {
    const container = document.getElementById('chart-container');
    container.innerHTML = '';

    // Agréger les données par mois
    const monthlyData = aggregateByMonth(data.codes);

    if (monthlyData.length === 0) {
        container.innerHTML = '<p>Aucune donnée disponible</p>';
        return;
    }

    const innerWidth = CHART_WIDTH - MARGIN.left - MARGIN.right;
    const innerHeight = CHART_HEIGHT - MARGIN.top - MARGIN.bottom;

    // Créer le SVG
    const svg = d3.create('svg')
        .attr('class', 'chart-svg')
        .attr('viewBox', `0 0 ${CHART_WIDTH} ${CHART_HEIGHT}`)
        .attr('preserveAspectRatio', 'xMidYMid meet');

    const g = svg.append('g')
        .attr('transform', `translate(${MARGIN.left},${MARGIN.top})`);

    // Échelle X (temps)
    const xScale = d3.scaleBand()
        .domain(monthlyData.map(d => d.date))
        .range([0, innerWidth])
        .padding(0.1);

    // Échelle Y (symétrique pour add/del)
    const maxValue = Math.max(
        d3.max(monthlyData, d => d.add),
        d3.max(monthlyData, d => d.del)
    );

    const yScale = d3.scaleLinear()
        .domain([-maxValue, maxValue])
        .range([innerHeight, 0])
        .nice();

    // Axe X
    const xAxis = d3.axisBottom(xScale)
        .tickValues(xScale.domain().filter((d, i) => {
            // Afficher un tick tous les 12 mois environ
            const totalTicks = Math.min(20, monthlyData.length);
            const step = Math.ceil(monthlyData.length / totalTicks);
            return i % step === 0;
        }))
        .tickFormat(d => {
            const date = new Date(d);
            return date.toLocaleDateString('fr-FR', { year: 'numeric', month: 'short' });
        });

    g.append('g')
        .attr('class', 'x-axis')
        .attr('transform', `translate(0,${innerHeight / 2})`)
        .call(xAxis)
        .selectAll('text')
        .attr('transform', 'rotate(-45)')
        .style('text-anchor', 'end')
        .attr('dx', '-0.5em')
        .attr('dy', '0.5em');

    // Axe Y
    const yAxis = d3.axisLeft(yScale)
        .tickFormat(d => d3.format('.2s')(Math.abs(d)));

    g.append('g')
        .attr('class', 'y-axis')
        .call(yAxis);

    // Ligne de base (y = 0)
    g.append('line')
        .attr('class', 'baseline')
        .attr('x1', 0)
        .attr('x2', innerWidth)
        .attr('y1', yScale(0))
        .attr('y2', yScale(0))
        .attr('stroke', '#d0d7de')
        .attr('stroke-width', 1);

    // Barres des additions (vers le haut)
    g.selectAll('.bar-add')
        .data(monthlyData)
        .enter()
        .append('rect')
        .attr('class', 'bar bar-add')
        .attr('x', d => xScale(d.date))
        .attr('y', d => yScale(d.add))
        .attr('width', xScale.bandwidth())
        .attr('height', d => yScale(0) - yScale(d.add))
        .attr('fill', '#2ea043')
        .attr('fill-opacity', 0.7)
        .style('cursor', 'pointer')
        .on('mouseenter', function(event, d) {
            if (!tooltipPinned) {
                d3.select(this).attr('fill-opacity', 1);
                showTooltip(event, d);
            }
        })
        .on('mouseleave', function() {
            if (!tooltipPinned) {
                d3.select(this).attr('fill-opacity', 0.7);
                hideTooltip();
            }
        })
        .on('click', function(event, d) {
            event.stopPropagation();
            resetBarOpacity();
            d3.select(this).attr('fill-opacity', 1);
            tooltipPinned = true;
            showTooltip(event, d);
        });

    // Barres des délétions (vers le bas)
    g.selectAll('.bar-del')
        .data(monthlyData)
        .enter()
        .append('rect')
        .attr('class', 'bar bar-del')
        .attr('x', d => xScale(d.date))
        .attr('y', yScale(0))
        .attr('width', xScale.bandwidth())
        .attr('height', d => yScale(-d.del) - yScale(0))
        .attr('fill', '#cf222e')
        .attr('fill-opacity', 0.7)
        .style('cursor', 'pointer')
        .on('mouseenter', function(event, d) {
            if (!tooltipPinned) {
                d3.select(this).attr('fill-opacity', 1);
                showTooltip(event, d);
            }
        })
        .on('mouseleave', function() {
            if (!tooltipPinned) {
                d3.select(this).attr('fill-opacity', 0.7);
                hideTooltip();
            }
        })
        .on('click', function(event, d) {
            event.stopPropagation();
            resetBarOpacity();
            d3.select(this).attr('fill-opacity', 1);
            tooltipPinned = true;
            showTooltip(event, d);
        });

    // Label axe Y
    svg.append('text')
        .attr('class', 'axis-label')
        .attr('transform', 'rotate(-90)')
        .attr('x', -CHART_HEIGHT / 2)
        .attr('y', 15)
        .attr('text-anchor', 'middle')
        .attr('fill', '#57606a')
        .attr('font-size', '12px')
        .text('Lignes modifiées');

    container.appendChild(svg.node());
}

/**
 * Réinitialise l'opacité de toutes les barres
 */
function resetBarOpacity() {
    d3.selectAll('.bar').attr('fill-opacity', 0.7);
}

/**
 * Affiche le tooltip
 */
function showTooltip(event, monthData) {
    const tooltip = document.getElementById('tooltip');

    const date = new Date(monthData.date);
    const dateStr = date.toLocaleDateString('fr-FR', {
        year: 'numeric',
        month: 'long'
    });

    const net = monthData.add - monthData.del;
    const netStr = net >= 0 ? `+${net.toLocaleString('fr-FR')}` : net.toLocaleString('fr-FR');
    const netClass = net >= 0 ? 'tooltip-add' : 'tooltip-del';

    tooltip.innerHTML = `
        <div class="tooltip-title">${dateStr}</div>
        <div class="tooltip-stats">
            <span class="tooltip-add">+${monthData.add.toLocaleString('fr-FR')}</span>
            <span class="tooltip-del">-${monthData.del.toLocaleString('fr-FR')}</span>
        </div>
        <div class="tooltip-net">
            Net: <span class="${netClass}">${netStr}</span>
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
    resetBarOpacity();
}

// Initialiser l'application au chargement de la page
document.addEventListener('DOMContentLoaded', init);
