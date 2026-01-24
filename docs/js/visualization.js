// État global de l'application
let globalData = null;
let displayMode = 'brut'; // 'brut' ou 'net'

// Dimensions des graphiques
const CHART_WIDTH = 280;
const CHART_HEIGHT = 180;
const MARGIN = { top: 10, right: 10, bottom: 30, left: 40 };

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
 * Initialise l'application
 */
async function init() {
    try {
        // Charger les données
        globalData = await loadData();

        // Masquer le loading
        document.getElementById('loading').style.display = 'none';

        // Afficher les statistiques
        displayStats(globalData.metadata);

        // Afficher les contrôles
        document.getElementById('controls').style.display = 'flex';

        // Afficher les graphiques
        document.getElementById('charts-container').style.display = 'grid';
        renderAllCharts(globalData);

    } catch (error) {
        document.getElementById('loading').style.display = 'none';
        document.getElementById('error').style.display = 'block';
        console.error(error);
    }
}

/**
 * Affiche les statistiques globales
 */
function displayStats(metadata) {
    document.getElementById('total-codes').textContent = metadata.total_codes;
    document.getElementById('total-commits').textContent = metadata.total_commits.toLocaleString('fr-FR');

    const earliest = new Date(metadata.earliest_commit);
    const latest = new Date(metadata.latest_commit);
    document.getElementById('date-range').textContent =
        `${earliest.getFullYear()} - ${latest.getFullYear()}`;

    const generatedDate = new Date(metadata.generated_at);
    document.getElementById('last-update').textContent =
        generatedDate.toLocaleDateString('fr-FR');

    document.getElementById('stats').style.display = 'grid';
}

/**
 * Crée les échelles communes pour tous les graphiques
 */
function createScales(metadata) {
    const xScale = d3.scaleTime()
        .domain([metadata.earliest_commit, metadata.latest_commit])
        .range([MARGIN.left, CHART_WIDTH - MARGIN.right]);

    let yScale;
    if (displayMode === 'brut') {
        // Mode brut : échelle séparée pour additions et deletions
        const maxValue = Math.max(metadata.max_additions, metadata.max_deletions);
        yScale = d3.scaleLinear()
            .domain([-maxValue, maxValue])
            .range([CHART_HEIGHT - MARGIN.bottom, MARGIN.top]);
    } else {
        // Mode net : échelle basée sur le solde max
        const maxNet = Math.max(
            metadata.max_additions,
            metadata.max_deletions
        );
        yScale = d3.scaleLinear()
            .domain([-maxNet, maxNet])
            .range([CHART_HEIGHT - MARGIN.bottom, MARGIN.top]);
    }

    return { xScale, yScale };
}

/**
 * Transforme les données selon le mode d'affichage
 */
function transformCommitData(commits) {
    if (displayMode === 'net') {
        return commits.map(c => ({
            ...c,
            net: c.add - c.del
        }));
    }
    return commits;
}

/**
 * Rend tous les graphiques
 */
function renderAllCharts(data) {
    const container = document.getElementById('charts-container');
    container.innerHTML = ''; // Vider le conteneur

    const { xScale, yScale } = createScales(data.metadata);

    data.codes.forEach(code => {
        if (code.commits.length === 0) return;

        const chartCard = createChartCard(code, xScale, yScale);
        container.appendChild(chartCard);
    });
}

/**
 * Crée une carte de graphique pour un code
 */
function createChartCard(code, xScale, yScale) {
    const card = document.createElement('div');
    card.className = 'chart-card';

    const title = document.createElement('div');
    title.className = 'chart-title';
    title.textContent = code.name;
    title.title = code.name; // Tooltip pour le nom complet

    const subtitle = document.createElement('div');
    subtitle.className = 'chart-subtitle';
    subtitle.textContent = `${code.total_commits} modification${code.total_commits > 1 ? 's' : ''}`;

    card.appendChild(title);
    card.appendChild(subtitle);

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

    const commits = transformCommitData(code.commits);

    if (displayMode === 'brut') {
        renderBrutMode(svg, commits, code, xScale, yScale);
    } else {
        renderNetMode(svg, commits, code, xScale, yScale);
    }

    // Ajouter les axes
    addAxes(svg, xScale, yScale);

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
    addInteractivePoints(svg, commits, code, xScale, yScale, 'brut');
}

/**
 * Rend le graphique en mode net (solde uniquement)
 */
function renderNetMode(svg, commits, code, xScale, yScale) {
    // Préparer les données pour l'area
    const netData = commits.map(c => ({
        date: c.ts,
        value: c.net
    }));

    // Area avec couleur conditionnelle
    const area = d3.area()
        .x(d => xScale(d.date))
        .y0(yScale(0))
        .y1(d => yScale(d.value))
        .curve(d3.curveStepAfter);

    // Créer deux paths : un pour les valeurs positives, un pour les négatives
    const positiveData = netData.map(d => ({ ...d, value: Math.max(0, d.value) }));
    const negativeData = netData.map(d => ({ ...d, value: Math.min(0, d.value) }));

    svg.append('path')
        .datum(positiveData)
        .attr('fill', '#2ea043')
        .attr('fill-opacity', 0.3)
        .attr('stroke', '#2ea043')
        .attr('stroke-width', 1)
        .attr('d', area);

    svg.append('path')
        .datum(negativeData)
        .attr('fill', '#cf222e')
        .attr('fill-opacity', 0.3)
        .attr('stroke', '#cf222e')
        .attr('stroke-width', 1)
        .attr('d', area);

    // Points interactifs
    addInteractivePoints(svg, commits, code, xScale, yScale, 'net');
}

/**
 * Ajoute les points interactifs pour le tooltip
 */
function addInteractivePoints(svg, commits, code, xScale, yScale, mode) {
    const points = svg.selectAll('.point')
        .data(commits)
        .enter()
        .append('circle')
        .attr('class', 'point')
        .attr('cx', d => xScale(d.ts))
        .attr('cy', d => {
            if (mode === 'brut') {
                return yScale(d.add > d.del ? d.add : -d.del);
            } else {
                return yScale(d.net);
            }
        })
        .attr('r', 3)
        .attr('fill', 'transparent')
        .attr('stroke', 'transparent')
        .style('cursor', 'pointer')
        .on('mouseenter', function(event, d) {
            d3.select(this)
                .attr('fill', '#0969da')
                .attr('r', 4);
            showTooltip(event, d, code);
        })
        .on('mouseleave', function() {
            d3.select(this)
                .attr('fill', 'transparent')
                .attr('r', 3);
            hideTooltip();
        });
}

/**
 * Ajoute les axes au graphique
 */
function addAxes(svg, xScale, yScale) {
    // Axe X
    const xAxis = d3.axisBottom(xScale)
        .ticks(3)
        .tickFormat(d3.timeFormat('%Y'));

    svg.append('g')
        .attr('class', 'axis')
        .attr('transform', `translate(0,${CHART_HEIGHT - MARGIN.bottom})`)
        .call(xAxis)
        .selectAll('line')
        .attr('class', 'axis-tick');

    // Axe Y
    const yAxis = d3.axisLeft(yScale)
        .ticks(5)
        .tickFormat(d => {
            if (d === 0) return '0';
            return d > 0 ? `+${d}` : d;
        });

    svg.append('g')
        .attr('class', 'axis')
        .attr('transform', `translate(${MARGIN.left},0)`)
        .call(yAxis)
        .selectAll('line')
        .attr('class', 'axis-tick');

    // Ligne zéro
    svg.append('line')
        .attr('class', 'zero-line')
        .attr('x1', MARGIN.left)
        .attr('x2', CHART_WIDTH - MARGIN.right)
        .attr('y1', yScale(0))
        .attr('y2', yScale(0));
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

    let statsHTML = '';
    if (displayMode === 'brut') {
        statsHTML = `
            <div class="tooltip-stats">
                <span class="tooltip-add">+${commit.add}</span>
                <span class="tooltip-del">-${commit.del}</span>
            </div>
        `;
    } else {
        const net = commit.net;
        const sign = net >= 0 ? '+' : '';
        const color = net >= 0 ? 'tooltip-add' : 'tooltip-del';
        statsHTML = `
            <div class="tooltip-stats">
                <span class="${color}">${sign}${net}</span>
            </div>
        `;
    }

    const codeUrl = `https://git.tricoteuses.fr/codes/${code.slug}/src/commit/${commit.sha}`;

    tooltip.innerHTML = `
        <div class="tooltip-title">${commit.msg}</div>
        <div class="tooltip-date">${dateStr}</div>
        ${statsHTML}
        <div class="tooltip-links">
            <a href="${commit.url}" target="_blank">🔗 Voir le commit</a>
            <a href="${codeUrl}" target="_blank">📖 Voir le code à cette date</a>
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
}

/**
 * Bascule entre le mode brut et net
 */
function toggleMode() {
    displayMode = displayMode === 'brut' ? 'net' : 'brut';

    // Mettre à jour le bouton
    const button = document.getElementById('toggle-mode');
    button.textContent = displayMode === 'brut' ? '📊 Mode Net' : '📊 Mode Brut';
    button.title = displayMode === 'brut'
        ? 'Afficher le solde (net)'
        : 'Afficher les additions et délétions séparément';

    // Mettre à jour la légende
    const legendAdd = document.getElementById('legend-add');
    const legendDel = document.getElementById('legend-del');

    if (displayMode === 'brut') {
        legendAdd.textContent = 'Additions';
        legendDel.textContent = 'Délétions';
    } else {
        legendAdd.textContent = 'Solde positif';
        legendDel.textContent = 'Solde négatif';
    }

    // Re-rendre tous les graphiques
    if (globalData) {
        renderAllCharts(globalData);
    }
}

// Initialiser l'application au chargement de la page
document.addEventListener('DOMContentLoaded', init);
