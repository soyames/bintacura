const CHART_COLORS = {
    primary: '#4a90e2',
    secondary: '#357abd',
    success: '#2ecc71',
    warning: '#f39c12',
    danger: '#e74c3c',
    info: '#3498db',
    purple: '#9b59b6',
    teal: '#1abc9c',
    orange: '#e67e22',
    pink: '#e91e63',
};

const CHART_PALETTE = [
    CHART_COLORS.primary,
    CHART_COLORS.success,
    CHART_COLORS.warning,
    CHART_COLORS.danger,
    CHART_COLORS.purple,
    CHART_COLORS.teal,
    CHART_COLORS.orange,
    CHART_COLORS.pink,
    CHART_COLORS.info,
    '#16a085',
    '#27ae60',
    '#2980b9',
    '#8e44ad',
    '#c0392b',
    '#d35400',
];

let chartInstances = {};

async function loadSurveyStatistics() {
    try {
        const response = await fetch('/api/v1/analytics/survey/statistics/');
        if (!response.ok) {
            throw new Error('Failed to fetch survey statistics');
        }
        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Error loading survey statistics:', error);
        throw error;
    }
}

function createSexDistributionChart(data) {
    const ctx = document.getElementById('sexChart');
    if (!ctx) return;

    const sexLabels = {
        'M': 'Male',
        'F': 'Female',
        'O': 'Other',
        'PND': 'Prefer Not to Disclose'
    };

    const labels = Object.keys(data).map(key => sexLabels[key] || key);
    const values = Object.values(data);

    if (chartInstances.sexChart) {
        chartInstances.sexChart.destroy();
    }

    chartInstances.sexChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: values,
                backgroundColor: [
                    CHART_COLORS.primary,
                    CHART_COLORS.danger,
                    CHART_COLORS.warning,
                    CHART_COLORS.purple,
                ],
                borderWidth: 2,
                borderColor: '#fff',
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        padding: 15,
                        font: {
                            size: 12
                        }
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const label = context.label || '';
                            const value = context.parsed || 0;
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = ((value / total) * 100).toFixed(1);
                            return `${label}: ${value} (${percentage}%)`;
                        }
                    }
                }
            }
        }
    });
}

function createProfessionDistributionChart(data) {
    const ctx = document.getElementById('professionChart');
    if (!ctx) return;

    const sortedEntries = Object.entries(data)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 15);

    const labels = sortedEntries.map(([key]) => key);
    const values = sortedEntries.map(([, value]) => value);

    if (chartInstances.professionChart) {
        chartInstances.professionChart.destroy();
    }

    chartInstances.professionChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Respondents',
                data: values,
                backgroundColor: CHART_COLORS.success,
                borderColor: CHART_COLORS.success,
                borderWidth: 1,
            }]
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return `${context.parsed.x} respondents`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    beginAtZero: true,
                    ticks: {
                        precision: 0
                    }
                },
                y: {
                    ticks: {
                        font: {
                            size: 11
                        }
                    }
                }
            }
        }
    });
}

function createCountryDistributionChart(data) {
    const ctx = document.getElementById('countryChart');
    if (!ctx) return;

    const sortedEntries = Object.entries(data)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 15);

    const labels = sortedEntries.map(([key]) => key);
    const values = sortedEntries.map(([, value]) => value);

    if (chartInstances.countryChart) {
        chartInstances.countryChart.destroy();
    }

    chartInstances.countryChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Respondents',
                data: values,
                backgroundColor: CHART_COLORS.info,
                borderColor: CHART_COLORS.info,
                borderWidth: 1,
            }]
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return `${context.parsed.x} respondents`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    beginAtZero: true,
                    ticks: {
                        precision: 0
                    }
                },
                y: {
                    ticks: {
                        font: {
                            size: 11
                        }
                    }
                }
            }
        }
    });
}

function createPriceDistributionChart(priceStats) {
    const ctx = document.getElementById('priceChart');
    if (!ctx || !priceStats.values || priceStats.values.length === 0) {
        if (ctx) {
            ctx.parentElement.innerHTML = '<p style="text-align: center; color: #7f8c8d; padding: 2rem;">No price data available</p>';
        }
        return;
    }

    const prices = priceStats.values;
    const min = Math.min(...prices);
    const max = Math.max(...prices);
    const binCount = Math.min(30, Math.ceil(Math.sqrt(prices.length)));
    const binSize = (max - min) / binCount;

    const bins = Array(binCount).fill(0);
    const binLabels = [];

    for (let i = 0; i < binCount; i++) {
        const binStart = min + (i * binSize);
        const binEnd = min + ((i + 1) * binSize);
        binLabels.push(`${binStart.toFixed(0)}-${binEnd.toFixed(0)}`);
    }

    prices.forEach(price => {
        const binIndex = Math.min(Math.floor((price - min) / binSize), binCount - 1);
        bins[binIndex]++;
    });

    if (chartInstances.priceChart) {
        chartInstances.priceChart.destroy();
    }

    chartInstances.priceChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: binLabels,
            datasets: [{
                label: 'Frequency',
                data: bins,
                backgroundColor: CHART_COLORS.success,
                borderColor: CHART_COLORS.success,
                borderWidth: 1,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return `Frequency: ${context.parsed.y}`;
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        precision: 0
                    }
                },
                x: {
                    ticks: {
                        maxRotation: 45,
                        minRotation: 45,
                        font: {
                            size: 10
                        }
                    }
                }
            }
        }
    });
}

function createPriceBoxPlot(priceStats) {
    const ctx = document.getElementById('priceBoxChart');
    if (!ctx || !priceStats.values || priceStats.values.length === 0) {
        if (ctx) {
            ctx.parentElement.innerHTML = '<p style="text-align: center; color: #7f8c8d; padding: 2rem;">No price data available</p>';
        }
        return;
    }

    const prices = [...priceStats.values].sort((a, b) => a - b);
    const q1Index = Math.floor(prices.length * 0.25);
    const q2Index = Math.floor(prices.length * 0.5);
    const q3Index = Math.floor(prices.length * 0.75);

    const q1 = prices[q1Index];
    const median = prices[q2Index];
    const q3 = prices[q3Index];
    const min = prices[0];
    const max = prices[prices.length - 1];
    const iqr = q3 - q1;

    const stats = {
        min: min,
        q1: q1,
        median: median,
        q3: q3,
        max: max,
        mean: priceStats.average,
        std: priceStats.std_dev
    };

    if (chartInstances.priceBoxChart) {
        chartInstances.priceBoxChart.destroy();
    }

    chartInstances.priceBoxChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: ['Price Distribution'],
            datasets: [
                {
                    label: 'Min',
                    data: [min],
                    backgroundColor: CHART_COLORS.danger,
                    borderWidth: 2,
                    borderColor: '#fff',
                },
                {
                    label: 'Q1 (25%)',
                    data: [q1],
                    backgroundColor: CHART_COLORS.warning,
                    borderWidth: 2,
                    borderColor: '#fff',
                },
                {
                    label: 'Median (50%)',
                    data: [median],
                    backgroundColor: CHART_COLORS.primary,
                    borderWidth: 2,
                    borderColor: '#fff',
                },
                {
                    label: 'Q3 (75%)',
                    data: [q3],
                    backgroundColor: CHART_COLORS.success,
                    borderWidth: 2,
                    borderColor: '#fff',
                },
                {
                    label: 'Max',
                    data: [max],
                    backgroundColor: CHART_COLORS.info,
                    borderWidth: 2,
                    borderColor: '#fff',
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        padding: 15,
                        font: {
                            size: 12
                        }
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return `${context.dataset.label}: ${context.parsed.y.toFixed(2)}`;
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
}

function createCurrencyDistributionChart(data) {
    const ctx = document.getElementById('currencyChart');
    if (!ctx) return;

    const labels = Object.keys(data);
    const values = Object.values(data);

    if (chartInstances.currencyChart) {
        chartInstances.currencyChart.destroy();
    }

    chartInstances.currencyChart = new Chart(ctx, {
        type: 'pie',
        data: {
            labels: labels,
            datasets: [{
                data: values,
                backgroundColor: CHART_PALETTE.slice(0, labels.length),
                borderWidth: 2,
                borderColor: '#fff',
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        padding: 15,
                        font: {
                            size: 12
                        }
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const label = context.label || '';
                            const value = context.parsed || 0;
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = ((value / total) * 100).toFixed(1);
                            return `${label}: ${value} (${percentage}%)`;
                        }
                    }
                }
            }
        }
    });
}

function updateStatCards(data) {
    document.getElementById('totalResponses').textContent = data.total_responses;

    const countriesCount = Object.keys(data.country_distribution).length;
    document.getElementById('countriesCount').textContent = countriesCount;

    const professionsCount = Object.keys(data.profession_distribution).length;
    document.getElementById('professionsCount').textContent = professionsCount;

    if (data.price_stats && data.price_stats.average) {
        document.getElementById('avgPrice').textContent = data.price_stats.average.toFixed(2);
    } else {
        document.getElementById('avgPrice').textContent = '0.00';
    }
}

function showError(message) {
    const contentWrapper = document.querySelector('.content-wrapper');
    contentWrapper.innerHTML = `
        <div class="error-message">
            <h2>⚠️ Error</h2>
            <p>${message}</p>
            <a href="/survey/" class="action-btn" onclick="location.reload(); return false;">Retry</a>
        </div>
    `;
}

function showNoData() {
    const contentWrapper = document.querySelector('.content-wrapper');
    contentWrapper.innerHTML = `
        <h1 class="page-title">📊 Statistiques de l'Enquête</h1>
        <div class="no-data">
            <h2>Aucune donnée disponible</h2>
            <p>Aucune réponse d'enquête n'a encore été collectée.</p>
            <a href="/survey/submit/" class="action-btn">Participer à l'enquête</a>
        </div>
    `;
}

async function initializeSurveyStatistics() {
    try {
        const data = await loadSurveyStatistics();

        if (data.total_responses === 0) {
            showNoData();
            return;
        }

        updateStatCards(data);

        if (Object.keys(data.sex_distribution).length > 0) {
            createSexDistributionChart(data.sex_distribution);
        }

        if (Object.keys(data.profession_distribution).length > 0) {
            createProfessionDistributionChart(data.profession_distribution);
        }

        if (Object.keys(data.country_distribution).length > 0) {
            createCountryDistributionChart(data.country_distribution);
        }

        if (data.price_stats && data.price_stats.values) {
            createPriceDistributionChart(data.price_stats);
            createPriceBoxPlot(data.price_stats);
        }

        if (Object.keys(data.currency_distribution).length > 0) {
            createCurrencyDistributionChart(data.currency_distribution);
        }

    } catch (error) {
        console.error('Failed to initialize survey statistics:', error);
        showError('Failed to load survey statistics. Please try again later.');
    }
}

function enableAutoRefresh(intervalSeconds = 30) {
    setInterval(async () => {
        try {
            const data = await loadSurveyStatistics();
            if (data.total_responses > 0) {
                updateStatCards(data);

                if (chartInstances.sexChart && Object.keys(data.sex_distribution).length > 0) {
                    chartInstances.sexChart.data.labels = Object.keys(data.sex_distribution).map(key => {
                        const sexLabels = {'M': 'Male', 'F': 'Female', 'O': 'Other', 'PND': 'Prefer Not to Disclose'};
                        return sexLabels[key] || key;
                    });
                    chartInstances.sexChart.data.datasets[0].data = Object.values(data.sex_distribution);
                    chartInstances.sexChart.update('none');
                }

                if (chartInstances.professionChart && Object.keys(data.profession_distribution).length > 0) {
                    const sortedEntries = Object.entries(data.profession_distribution).sort((a, b) => b[1] - a[1]).slice(0, 15);
                    chartInstances.professionChart.data.labels = sortedEntries.map(([key]) => key);
                    chartInstances.professionChart.data.datasets[0].data = sortedEntries.map(([, value]) => value);
                    chartInstances.professionChart.update('none');
                }

                if (chartInstances.countryChart && Object.keys(data.country_distribution).length > 0) {
                    const sortedEntries = Object.entries(data.country_distribution).sort((a, b) => b[1] - a[1]).slice(0, 15);
                    chartInstances.countryChart.data.labels = sortedEntries.map(([key]) => key);
                    chartInstances.countryChart.data.datasets[0].data = sortedEntries.map(([, value]) => value);
                    chartInstances.countryChart.update('none');
                }

                if (chartInstances.currencyChart && Object.keys(data.currency_distribution).length > 0) {
                    chartInstances.currencyChart.data.labels = Object.keys(data.currency_distribution);
                    chartInstances.currencyChart.data.datasets[0].data = Object.values(data.currency_distribution);
                    chartInstances.currencyChart.update('none');
                }

                if (data.price_stats && data.price_stats.values && chartInstances.priceChart) {
                    const prices = data.price_stats.values;
                    const min = Math.min(...prices);
                    const max = Math.max(...prices);
                    const binCount = Math.min(30, Math.ceil(Math.sqrt(prices.length)));
                    const binSize = (max - min) / binCount;
                    const bins = Array(binCount).fill(0);

                    prices.forEach(price => {
                        const binIndex = Math.min(Math.floor((price - min) / binSize), binCount - 1);
                        bins[binIndex]++;
                    });

                    chartInstances.priceChart.data.datasets[0].data = bins;
                    chartInstances.priceChart.update('none');
                }
            }
        } catch (error) {
            console.error('Auto-refresh failed:', error);
        }
    }, intervalSeconds * 1000);
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        initializeSurveyStatistics();
        enableAutoRefresh(30);
    });
} else {
    initializeSurveyStatistics();
    enableAutoRefresh(30);
}
