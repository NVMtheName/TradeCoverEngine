// Dashboard JavaScript
document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Initialize popovers
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    var popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    // Account summary card - show/hide details
    const accountDetailsToggle = document.getElementById('accountDetailsToggle');
    if (accountDetailsToggle) {
        accountDetailsToggle.addEventListener('click', function() {
            const detailsSection = document.getElementById('accountDetailsSection');
            if (detailsSection.style.display === 'none') {
                detailsSection.style.display = 'block';
                accountDetailsToggle.textContent = 'Hide Details';
            } else {
                detailsSection.style.display = 'none';
                accountDetailsToggle.textContent = 'Show Details';
            }
        });
    }

    // Recent trades table - add expand/collapse functionality for details
    const tradeDetailButtons = document.querySelectorAll('.trade-detail-btn');
    tradeDetailButtons.forEach(button => {
        button.addEventListener('click', function() {
            const tradeId = this.getAttribute('data-trade-id');
            const detailRow = document.getElementById(`tradeDetail${tradeId}`);

            if (detailRow.classList.contains('d-none')) {
                detailRow.classList.remove('d-none');
                this.innerHTML = '<i class="fas fa-chevron-up"></i>';
            } else {
                detailRow.classList.add('d-none');
                this.innerHTML = '<i class="fas fa-chevron-down"></i>';
            }
        });
    });

    // Initialize performance charts if the elements exist
    initializePerformanceCharts();
});

// Initialize performance charts
function initializePerformanceCharts() {
    // Check if the chart containers exist
    const equityChartElement = document.getElementById('equityChart');
    const returnsChartElement = document.getElementById('monthlyReturnsChart');

    if (equityChartElement) {
        // Get data from the data attribute
        const equityData = equityChartElement.getAttribute('data-equity');
        if (equityData) {
            try {
                const chartData = JSON.parse(equityData);
                createEquityChart(equityChartElement, chartData);
            } catch (e) {
                console.error('Error parsing equity data:', e);
            }
        }
    }

    if (returnsChartElement) {
        // Get data from the data attribute
        const returnsData = returnsChartElement.getAttribute('data-returns');
        if (returnsData) {
            try {
                const chartData = JSON.parse(returnsData);
                createMonthlyReturnsChart(returnsChartElement, chartData);
            } catch (e) {
                console.error('Error parsing returns data:', e);
            }
        }
    }
}

// Create equity chart
function createEquityChart(element, data) {
    const ctx = element.getContext('2d');

    new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.dates,
            datasets: [{
                label: 'Account Value',
                data: data.equity,
                backgroundColor: 'rgba(13, 110, 253, 0.1)',
                borderColor: 'rgba(13, 110, 253, 1)',
                borderWidth: 2,
                pointRadius: 0,
                pointHoverRadius: 5,
                pointHoverBackgroundColor: 'rgba(13, 110, 253, 1)',
                pointHoverBorderColor: '#fff',
                pointHoverBorderWidth: 2,
                tension: 0.1,
                fill: true
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
                    mode: 'index',
                    intersect: false,
                    callbacks: {
                        label: function(context) {
                            return `Account Value: $${context.raw.toFixed(2)}`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: {
                        display: false
                    },
                    ticks: {
                        maxTicksLimit: 8
                    }
                },
                y: {
                    beginAtZero: false,
                    grid: {
                        borderDash: [2, 2]
                    },
                    ticks: {
                        callback: function(value) {
                            return '$' + value.toLocaleString();
                        }
                    }
                }
            }
        }
    });
}

// Create monthly returns chart
function createMonthlyReturnsChart(element, data) {
    const ctx = element.getContext('2d');

    // Create colors array based on return values (positive = green, negative = red)
    const colors = data.returns.map(value => 
        value >= 0 ? 'rgba(40, 167, 69, 0.7)' : 'rgba(220, 53, 69, 0.7)'
    );

    const borderColors = data.returns.map(value => 
        value >= 0 ? 'rgba(40, 167, 69, 1)' : 'rgba(220, 53, 69, 1)'
    );

    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: data.months,
            datasets: [{
                label: 'Monthly Return',
                data: data.returns,
                backgroundColor: colors,
                borderColor: borderColors,
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
                x: {
                    grid: {
                        display: false
                    }
                },
                y: {
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

// Function to update position status indicators
function updatePositionStatuses() {
    const positions = document.querySelectorAll('.position-item');

    positions.forEach(position => {
        const plPercentage = parseFloat(position.getAttribute('data-pl-percent'));
        const statusIndicator = position.querySelector('.position-status');

        if (plPercentage >= 5) {
            statusIndicator.className = 'position-status bg-success';
            statusIndicator.setAttribute('title', 'Target profit reached');
        } else if (plPercentage <= -3) {
            statusIndicator.className = 'position-status bg-danger';
            statusIndicator.setAttribute('title', 'Stop loss triggered');
        } else if (plPercentage > 0) {
            statusIndicator.className = 'position-status bg-info';
            statusIndicator.setAttribute('title', 'Profitable position');
        } else {
            statusIndicator.className = 'position-status bg-warning';
            statusIndicator.setAttribute('title', 'Position at loss');
        }
    });
}

// Call update function when page loads
document.addEventListener('DOMContentLoaded', updatePositionStatuses);

// Project download functionality
document.getElementById('downloadProject').addEventListener('click', function() {
    window.location.href = '/download_project';
});