// Stock and option analysis charts

/**
 * Create a stock price chart with optional indicators
 * @param {string} elementId - DOM element ID for the chart
 * @param {Object} stockData - Stock data object with dates, prices, and volumes
 * @param {Object} indicators - Optional technical indicators
 */
function createStockChart(elementId, stockData, indicators = null) {
    const ctx = document.getElementById(elementId).getContext('2d');
    
    // Prepare datasets
    const datasets = [
        {
            label: 'Price',
            data: stockData.prices,
            borderColor: 'rgba(13, 110, 253, 1)',
            backgroundColor: 'rgba(13, 110, 253, 0.1)',
            borderWidth: 2,
            yAxisID: 'y',
            fill: false,
            tension: 0.1
        },
        {
            label: 'Volume',
            data: stockData.volumes,
            backgroundColor: 'rgba(200, 200, 200, 0.5)',
            borderColor: 'rgba(200, 200, 200, 0.8)',
            borderWidth: 1,
            yAxisID: 'y1',
            type: 'bar'
        }
    ];
    
    // Add indicators if provided
    if (indicators) {
        if (indicators.sma_20) {
            datasets.push({
                label: 'SMA 20',
                data: indicators.sma_20,
                borderColor: 'rgba(255, 99, 132, 1)',
                borderWidth: 1.5,
                yAxisID: 'y',
                fill: false,
                pointRadius: 0
            });
        }
        
        if (indicators.sma_50) {
            datasets.push({
                label: 'SMA 50',
                data: indicators.sma_50,
                borderColor: 'rgba(255, 159, 64, 1)',
                borderWidth: 1.5,
                yAxisID: 'y',
                fill: false,
                pointRadius: 0
            });
        }
    }
    
    // Create chart
    new Chart(ctx, {
        type: 'line',
        data: {
            labels: stockData.dates,
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false,
            },
            plugins: {
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            let label = context.dataset.label || '';
                            if (label) {
                                label += ': ';
                            }
                            if (context.dataset.yAxisID === 'y') {
                                label += '$' + context.raw.toFixed(2);
                            } else {
                                label += context.raw.toLocaleString();
                            }
                            return label;
                        }
                    }
                },
                legend: {
                    position: 'top',
                }
            },
            scales: {
                x: {
                    grid: {
                        display: false
                    },
                    ticks: {
                        maxTicksLimit: 10
                    }
                },
                y: {
                    type: 'linear',
                    display: true,
                    position: 'left',
                    grid: {
                        borderDash: [2, 2]
                    },
                    ticks: {
                        callback: function(value) {
                            return '$' + value.toFixed(2);
                        }
                    }
                },
                y1: {
                    type: 'linear',
                    display: true,
                    position: 'right',
                    grid: {
                        drawOnChartArea: false,
                    },
                    ticks: {
                        callback: function(value) {
                            if (value >= 1000000) {
                                return (value / 1000000).toFixed(1) + 'M';
                            } else if (value >= 1000) {
                                return (value / 1000).toFixed(1) + 'K';
                            }
                            return value;
                        }
                    }
                }
            }
        }
    });
}

/**
 * Create a chart showing potential returns for covered call strategies
 * @param {string} elementId - DOM element ID for the chart
 * @param {Array} strategies - Array of strategy objects with names and return values
 */
function createCoveredCallReturnsChart(elementId, strategies) {
    const ctx = document.getElementById(elementId).getContext('2d');
    
    // Extract data from strategies
    const labels = strategies.map(s => s.name);
    const returnValues = strategies.map(s => s.annualReturn);
    
    // Create colors based on return values
    const backgroundColors = returnValues.map(value => {
        if (value >= 15) return 'rgba(40, 167, 69, 0.7)';
        if (value >= 10) return 'rgba(23, 162, 184, 0.7)';
        if (value >= 5) return 'rgba(255, 193, 7, 0.7)';
        return 'rgba(220, 53, 69, 0.7)';
    });
    
    // Create chart
    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Annualized Return (%)',
                data: returnValues,
                backgroundColor: backgroundColors,
                borderColor: 'rgba(0, 0, 0, 0.1)',
                borderWidth: 1
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
                            return `Return: ${context.raw.toFixed(2)}%`;
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: {
                        borderDash: [2, 2]
                    },
                    ticks: {
                        callback: function(value) {
                            return value + '%';
                        }
                    }
                }
            }
        }
    });
}

/**
 * Load stock data from API and create a chart
 * @param {string} symbol - Stock symbol
 * @param {string} elementId - DOM element ID for chart
 */
function loadStockDataAndCreateChart(symbol, elementId) {
    // Show loading indicator
    const chartContainer = document.getElementById(elementId).parentElement;
    chartContainer.innerHTML = '<div class="text-center my-5"><div class="spinner-border text-primary" role="status"><span class="visually-hidden">Loading...</span></div><p class="mt-2">Loading stock data...</p></div>';
    
    // Fetch stock data from API
    fetch(`/api/stock-data/${symbol}`)
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            // Clear loading indicator and restore canvas
            chartContainer.innerHTML = `<canvas id="${elementId}"></canvas>`;
            
            // Create chart with the data
            createStockChart(elementId, data);
        })
        .catch(error => {
            console.error('Error fetching stock data:', error);
            chartContainer.innerHTML = `<div class="alert alert-danger">Error loading stock data: ${error.message}</div>`;
        });
}

/**
 * Create a gauge chart for RSI indicator
 * @param {string} elementId - DOM element ID for the chart
 * @param {number} rsiValue - RSI value (0-100)
 */
function createRSIGauge(elementId, rsiValue) {
    const ctx = document.getElementById(elementId).getContext('2d');
    
    // Determine color based on RSI value
    let color = 'rgba(40, 167, 69, 0.7)';  // Green (neutral)
    
    if (rsiValue >= 70) {
        color = 'rgba(220, 53, 69, 0.7)';  // Red (overbought)
    } else if (rsiValue <= 30) {
        color = 'rgba(255, 193, 7, 0.7)';  // Yellow (oversold)
    }
    
    // Create gauge chart
    new Chart(ctx, {
        type: 'doughnut',
        data: {
            datasets: [{
                data: [rsiValue, 100 - rsiValue],
                backgroundColor: [color, 'rgba(200, 200, 200, 0.2)'],
                borderWidth: 0
            }]
        },
        options: {
            circumference: 180,
            rotation: 270,
            cutout: '70%',
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                tooltip: {
                    enabled: false
                },
                legend: {
                    display: false
                }
            }
        },
        plugins: [{
            id: 'rsiText',
            afterDraw: function(chart) {
                const width = chart.width;
                const height = chart.height;
                const ctx = chart.ctx;
                
                ctx.restore();
                
                // RSI value
                ctx.font = 'bold 24px Arial';
                ctx.textBaseline = 'middle';
                ctx.textAlign = 'center';
                ctx.fillStyle = color;
                ctx.fillText(Math.round(rsiValue), width / 2, height - 30);
                
                // RSI label
                ctx.font = '14px Arial';
                ctx.fillStyle = '#888';
                ctx.fillText('RSI', width / 2, height - 10);
                
                ctx.save();
            }
        }]
    });
}

/**
 * Initialize all charts on the analysis page
 */
function initAnalysisCharts() {
    // Initialize stock charts for each opportunity
    document.querySelectorAll('[data-chart-symbol]').forEach(element => {
        const symbol = element.getAttribute('data-chart-symbol');
        const chartId = element.getAttribute('id');
        
        loadStockDataAndCreateChart(symbol, chartId);
    });
    
    // Initialize RSI gauges
    document.querySelectorAll('[data-rsi-value]').forEach(element => {
        const rsiValue = parseFloat(element.getAttribute('data-rsi-value'));
        const gaugeId = element.getAttribute('id');
        
        createRSIGauge(gaugeId, rsiValue);
    });
    
    // Initialize return comparison charts
    document.querySelectorAll('[data-returns-chart]').forEach(element => {
        const chartId = element.getAttribute('id');
        const chartData = JSON.parse(element.getAttribute('data-returns-chart'));
        
        createCoveredCallReturnsChart(chartId, chartData);
    });
}

// Initialize charts when page loads
document.addEventListener('DOMContentLoaded', function() {
    // Check if we're on the analysis page
    if (document.querySelector('[data-chart-symbol]') || 
        document.querySelector('[data-rsi-value]') ||
        document.querySelector('[data-returns-chart]')) {
        initAnalysisCharts();
    }
});
