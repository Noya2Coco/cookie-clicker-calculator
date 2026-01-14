let currentMode = 'interactive';
let currentSimulationData = null;
let refreshTimeout = null;

// Show toast notification
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    document.body.appendChild(toast);

    setTimeout(() => {
        toast.style.animation = 'slideOut 0.3s ease-out';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// Debounce function for performance
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

function switchMode(mode, btnEl) {
    currentMode = mode;

    // Update active class on buttons (ensure consistent equal-width layout)
    const buttons = Array.from(document.querySelectorAll('.mode-btn'));
    buttons.forEach(b => b.classList.toggle('active', b === btnEl));

    // Slide the indicator: with equal-width buttons the slide is 50% and we translate it
    const container = document.querySelector('.mode-selector');
    const slide = container ? container.querySelector('.mode-slide') : null;
    if (slide && btnEl) {
        const index = buttons.indexOf(btnEl);
        // translateX(0%) = left slot, translateX(100%) = right slot (we use the CSS inset)
        slide.style.transform = index <= 0 ? 'translateX(0%)' : 'translateX(100%)';
    }

    // Show/hide content
    if (mode === 'interactive') {
        document.getElementById('interactive-mode').classList.remove('hidden');
        document.getElementById('simulation-mode').classList.add('hidden');
        loadUpgrades();
    } else {
        document.getElementById('interactive-mode').classList.add('hidden');
        document.getElementById('simulation-mode').classList.remove('hidden');
        loadSimulationHistory();
    }
}

// Position the mode-bg under the currently active button on load / resize
function initModeBg() {
    const container = document.querySelector('.mode-selector');
    if (!container) return;
    const buttons = Array.from(container.querySelectorAll('.mode-btn'));
    const activeIndex = buttons.findIndex(b => b.classList.contains('active'));
    const slide = container.querySelector('.mode-slide');
    if (!slide || buttons.length === 0) return;
    // Ensure the slide uses the CSS half-width and a small inset (handled in CSS)
    // Position by translating to the correct slot (0 or 100%)
    const idx = (activeIndex <= 0) ? 0 : 1;
    slide.style.transform = idx === 0 ? 'translateX(0%)' : 'translateX(100%)';
}

window.addEventListener('DOMContentLoaded', () => {
    initModeBg();
    window.addEventListener('resize', () => initModeBg());
});

function formatNumber(num, decimals = null) {
    if (num === null || num === undefined || isNaN(Number(num))) return '-';
    const n = Number(num);
    let fixed;
    if (decimals !== null) {
        fixed = n.toFixed(decimals);
    } else {
        // preserve integer if whole number, otherwise keep up to 1 decimal
        fixed = (Math.floor(n) === n) ? n.toString() : n.toFixed(1);
    }

    const parts = fixed.split('.');
    let intPart = parts[0];
    const fracPart = parts[1] || '';

    // thousands separator as dot (keeps previous look), decimal separator as comma
    intPart = intPart.replace(/\B(?=(\d{3})+(?!\d))/g, ".");

    // Trim trailing zeros from fractional part
    let trimmedFrac = fracPart.replace(/0+$/g, '');

    return trimmedFrac ? `${intPart},${trimmedFrac}` : intPart;
}

function formatTime(minutes) {
    const hours = Math.floor(minutes / 60);
    const mins = Math.floor(minutes % 60);
    return `${hours}h ${mins}m`;
}

// Ensure Plotly charts match the page (light background, dark text)
function normalizeLayoutForLight(layout) {
    if (!layout) layout = {};
    // base background
    if (layout.paper_bgcolor === undefined) layout.paper_bgcolor = '#ffffff';
    if (layout.plot_bgcolor === undefined) layout.plot_bgcolor = '#ffffff';

    // font
    layout.font = layout.font || {};
    if (layout.font.color === undefined) layout.font.color = '#1e293b';

    // legend
    layout.legend = layout.legend || {};
    layout.legend.font = layout.legend.font || {};
    if (layout.legend.font.color === undefined) layout.legend.font.color = '#1e293b';

    // axes defaults
    const defaultAxis = {
        color: '#1e293b',
        tickcolor: '#1e293b',
        gridcolor: '#e6eef6',
        zerolinecolor: '#cbd5e1'
    };

    function applyAxis(axis) {
        if (!axis) return Object.assign({}, defaultAxis);
        for (const k in defaultAxis) {
            if (axis[k] === undefined) axis[k] = defaultAxis[k];
        }
        return axis;
    }

    layout.xaxis = applyAxis(layout.xaxis);
    layout.yaxis = applyAxis(layout.yaxis);

    // colorbar / colorbar ticks
    if (layout.colorbar) {
        layout.colorbar.tickfont = layout.colorbar.tickfont || {};
        if (layout.colorbar.tickfont.color === undefined) layout.colorbar.tickfont.color = '#1e293b';
    }

    return layout;
}

// Fit text inside stat-value elements by shrinking font-size until it fits
function adjustStatSizes() {
    const elements = document.querySelectorAll('.stat-value');
    elements.forEach(el => {
        const style = window.getComputedStyle(el);
        const maxPx = Math.max(24, parseInt(style.fontSize || '24', 10));
        let fs = Math.max(24, maxPx);
        el.style.whiteSpace = 'nowrap';
        el.style.overflow = 'hidden';
        el.style.display = 'inline-block';
        el.style.fontSize = fs + 'px';

        while (el.scrollWidth > el.clientWidth && fs > 10) {
            fs -= 1;
            el.style.fontSize = fs + 'px';
        }
    });
}

async function loadUpgrades() {
    try {
        const response = await fetch('/api/upgrades');
        const data = await response.json();

        // Update stats (keep decimals for CPS, show 2 decimals)
        document.getElementById('current-cps').textContent = formatNumber(data.total_cps, 1);
        
        if (data.best_upgrade) {
            document.getElementById('best-upgrade-name').textContent = data.best_upgrade.name;
            document.getElementById('best-upgrade-time').textContent = formatTime(data.best_upgrade.time);
        } else {
            document.getElementById('best-upgrade-name').textContent = '-';
            document.getElementById('best-upgrade-time').textContent = '-';
        }

        // Update table
        const tbody = document.getElementById('upgrades-tbody');
        tbody.innerHTML = '';

        data.upgrades.forEach(upgrade => {
            const row = document.createElement('tr');
            if (upgrade.is_best) {
                row.classList.add('best-upgrade');
            }
            // Add data attribute for smooth scrolling
            row.setAttribute('data-upgrade-name', upgrade.name);

            row.innerHTML = `
                <td>${upgrade.name}${upgrade.is_best ? ' ⭐' : ''}</td>
                <td>${upgrade.level}</td>
                <td>${formatNumber(upgrade.current_price)}</td>
                <td>${formatNumber(upgrade.cps, 1)}</td>
                <td title="Raw: ${upgrade.raw_efficiency ? upgrade.raw_efficiency.toExponential(2) : (upgrade.value ? upgrade.value.toExponential(2) : '-')}">
                    ${typeof upgrade.efficiency === 'number' ? formatNumber(upgrade.efficiency * 100, 2) + '%' : '-'}
                </td>
                <td>${upgrade.time_to_reach ? formatTime(upgrade.time_to_reach) : '-'}</td>
                <td>
                    <button class="purchase-btn" onclick="purchaseUpgrade('${upgrade.name}')">Buy</button>
                    <button class="purchase-btn downgrade" onclick="decreaseUpgrade('${upgrade.name}')">Downgrade</button>
                </td>
            `;

            tbody.appendChild(row);
        });

        // Aggregate some extra stats from the upgrades list
        const totalUpgrades = data.upgrades.reduce((s, u) => s + (u.level || 0), 0);
        const totalSpentEstimate = data.upgrades.reduce((s, u) => {
            const base = (u.price !== undefined) ? u.price : (u.base_price !== undefined ? u.base_price : (u.current_price !== undefined ? u.current_price : 0));
            return s + (base * (u.level || 0));
        }, 0);

        // Populate new stat cards (if present)
        const elTotalUpgrades = document.getElementById('total-upgrades');
        if (elTotalUpgrades) elTotalUpgrades.textContent = formatNumber(totalUpgrades, 0);

        const elTotalSpent = document.getElementById('total-spent');
        if (elTotalSpent) elTotalSpent.textContent = formatNumber(totalSpentEstimate, 0);

        // Adjust stat sizes so numbers don't overflow their cards
        adjustStatSizes();

        // Refresh chart
        refreshChart();

    } catch (error) {
        console.error('Error loading upgrades:', error);
        showToast('❌ Failed to load upgrades', 'error');
    }
}

async function purchaseUpgrade(name) {
    try {
        // Check if this is the current best upgrade before purchasing
        const bestUpgradeName = document.getElementById('best-upgrade-name').textContent;
        const wasBestUpgrade = (bestUpgradeName === name);
        
        const response = await fetch(`/api/upgrade/${name}`, { method: 'POST' });
        const data = await response.json();

        if (data.success) {
            showToast(`✅ ${name} purchased! (Lvl ${data.upgrade.level})`, 'success');
            
            // Reload upgrades
            await loadUpgrades();
            
            // If we purchased the best upgrade, scroll to the new best upgrade
            if (wasBestUpgrade) {
                // Wait a bit for DOM to update
                setTimeout(() => {
                    const newBestRow = document.querySelector('.best-upgrade');
                    if (newBestRow) {
                        newBestRow.scrollIntoView({ 
                            behavior: 'smooth', 
                            block: 'center'
                        });
                    }
                }, 100);
            }
        } else {
            showToast('❌ ' + (data.error || 'Purchase failed'), 'error');
        }
    } catch (error) {
        console.error('Error purchasing upgrade:', error);
        showToast('❌ Purchase failed', 'error');
    }
}

async function decreaseUpgrade(name) {
    try {
        const response = await fetch(`/api/upgrade/${name}/decrease`, { method: 'POST' });
        const data = await response.json();

        if (data.success) {
            showToast(`↩️ ${name} downgraded. (Lvl ${data.upgrade.level})`, 'info');
            loadUpgrades();
        } else {
            showToast('❌ ' + (data.error || 'Downgrade failed'), 'error');
        }
    } catch (error) {
        console.error('Error downgrading upgrade:', error);
        showToast('❌ Downgrade failed', 'error');
    }
}

async function refreshChart() {
    try {
        const response = await fetch('/api/charts/current');
        const chartJson = await response.json();
        const chartData = JSON.parse(chartJson);

        // normalize layout to page theme before rendering
        const normalizedLayout = normalizeLayoutForLight(chartData.layout);
        Plotly.newPlot('current-chart', chartData.data, normalizedLayout);
    } catch (error) {
        console.error('Error loading chart:', error);
    }
}

async function runSimulation() {
    const purchases = parseInt(document.getElementById('purchase-count').value);
    
    // Validation
    if (isNaN(purchases) || purchases < 1 || purchases > 10000) {
        showToast('⚠️ Please enter a valid number between 1 and 10000', 'error');
        return;
    }

    showToast('🚀 Starting simulation...', 'info');

    // Show progress
    document.getElementById('simulation-progress').classList.remove('hidden');
    document.getElementById('simulation-results').classList.add('hidden');
    document.getElementById('progress-fill').style.width = '0%';
    document.getElementById('progress-fill').textContent = '0%';

    try {
        // Simulate progress
        let progress = 0;
        const progressInterval = setInterval(() => {
            progress += 5;
            if (progress >= 95) {
                clearInterval(progressInterval);
            }
            document.getElementById('progress-fill').style.width = progress + '%';
            document.getElementById('progress-fill').textContent = progress + '%';
        }, 100);

        const response = await fetch('/api/simulate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ purchases })
        });

        const data = await response.json();
        
        clearInterval(progressInterval);
        
        if (!data.success && data.error) {
            throw new Error(data.error);
        }
        
        currentSimulationData = data;

        document.getElementById('progress-fill').style.width = '100%';
        document.getElementById('progress-fill').textContent = '100%';

        setTimeout(() => {
            document.getElementById('simulation-progress').classList.add('hidden');
            displaySimulationResults(data);
            loadSimulationHistory();
            showToast('✅ Simulation completed!', 'success');
        }, 500);

    } catch (error) {
        console.error('Error running simulation:', error);
        document.getElementById('simulation-progress').classList.add('hidden');
        showToast('❌ Simulation failed: ' + error.message, 'error');
    }
}

async function displaySimulationResults(data) {
    document.getElementById('simulation-results').classList.remove('hidden');

    // Update stats
    document.getElementById('sim-purchases').textContent = formatNumber(data.total_purchases);
    document.getElementById('sim-cps').textContent = formatNumber(data.final_cps, 1);
    document.getElementById('sim-time').textContent = formatTime(data.total_time);
    document.getElementById('sim-cookies').textContent = formatNumber(data.total_cookies);

    // Load charts
    try {
        const response = await fetch('/api/simulation-charts', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });

        const charts = await response.json();

        const chart1 = JSON.parse(charts.chart1);
        Plotly.newPlot('sim-chart1', chart1.data, normalizeLayoutForLight(chart1.layout));

        const chart2 = JSON.parse(charts.chart2);
        Plotly.newPlot('sim-chart2', chart2.data, normalizeLayoutForLight(chart2.layout));

        if (charts.chart3) {
            const chart3 = JSON.parse(charts.chart3);
            Plotly.newPlot('sim-chart3', chart3.data, chart3.layout);
        }

        const chart4 = JSON.parse(charts.chart4);
        Plotly.newPlot('sim-chart4', chart4.data, normalizeLayoutForLight(chart4.layout));

    } catch (error) {
        console.error('Error loading simulation charts:', error);
    }

    loadSimulationHistory();
}

async function exportData(format) {
    showToast(`📥 Downloading ${format.toUpperCase()} export...`, 'info');
    window.location.href = `/api/export/${format}`;
}

function exportSimulation() {
    if (!currentSimulationData) {
        showToast('⚠️ No simulation data to export', 'error');
        return;
    }

    const dataStr = JSON.stringify(currentSimulationData, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(dataBlob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `simulation_${currentSimulationData.timestamp}.json`;
    link.click();
    showToast('✅ Simulation exported!', 'success');
}

function onResetConfirm() {
    if (!confirm('This will set ALL upgrade levels to 0. This action is irreversible. Continue?')) {
        return;
    }
    resetUpgrades();
}

async function resetUpgrades() {
    try {
        // Create backup before reset
        const bresp = await fetch('/api/backup', { method: 'POST' });
        const bdata = await bresp.json();
        if (!bdata.success) {
            showToast('❌ Could not create backup before reset', 'error');
            return;
        }
        showToast('📦 Backup created: ' + bdata.filename, 'info');

        // Now perform reset
        const response = await fetch('/api/reset', { method: 'POST' });
        const data = await response.json();
        if (data.success) {
            showToast('✅ All upgrades reset to 0 (backup: ' + (data.backup || bdata.filename) + ')', 'success');
            loadUpgrades();
        } else {
            showToast('❌ Reset failed: ' + (data.error || ''), 'error');
        }
    } catch (error) {
        console.error('Reset error:', error);
        showToast('❌ Reset failed', 'error');
    }
}

async function createBackup() {
    try {
        const response = await fetch('/api/backup', { method: 'POST' });
        const data = await response.json();
        if (data.success) {
            showToast('📦 Backup created: ' + data.filename, 'success');
            // Trigger download
            const link = document.createElement('a');
            link.href = data.url;
            link.download = data.filename;
            document.body.appendChild(link);
            link.click();
            link.remove();
        } else {
            showToast('❌ Backup failed: ' + (data.error || ''), 'error');
        }
    } catch (error) {
        console.error('Backup error:', error);
        showToast('❌ Backup failed', 'error');
    }
}

async function loadSimulationHistory() {
    try {
        const response = await fetch('/api/simulations');
        const simulations = await response.json();

        const historyDiv = document.getElementById('simulation-history');
        historyDiv.innerHTML = '';

        if (simulations.length === 0) {
            historyDiv.innerHTML = '<p>No simulations yet. Run your first simulation!</p>';
            return;
        }

        simulations.forEach(sim => {
            const item = document.createElement('div');
            item.classList.add('history-item');
            item.innerHTML = `
                <div>
                    <strong>${sim.timestamp}</strong><br>
                    Purchases: ${formatNumber(sim.total_purchases)} | 
                    Final CPS: ${formatNumber(Math.floor(sim.final_cps))}
                </div>
                <button class="export-btn" onclick="window.location.href='/simulations/${sim.filename}'">
                    📥 Download
                </button>
            `;
            historyDiv.appendChild(item);
        });

    } catch (error) {
        console.error('Error loading simulation history:', error);
    }
}

// Initial load
loadUpgrades();
