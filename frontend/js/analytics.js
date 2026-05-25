// analytics.js - Chart.js implementations for Page 2

let chartPieInstance = null;
let chartBarInstance = null;
let chartLineInstance = null;

// Mock historical data since backend currently doesn't persist this
const mockHourly = [120, 150, 180, 130, 200, 250, 190, 210];
const mockTrends = [95, 92, 94, 91, 96, 95, 98, 97];
const labelsTime = ['08:00', '09:00', '10:00', '11:00', '12:00', '13:00', '14:00', '15:00'];

const chartConfig = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      labels: { color: '#a1a1aa', font: { family: 'Inter', size: 12 } }
    }
  },
  scales: {
    x: { ticks: { color: '#71717a' }, grid: { color: 'rgba(255,255,255,0.05)' } },
    y: { ticks: { color: '#71717a' }, grid: { color: 'rgba(255,255,255,0.05)' } }
  }
};

function initCharts() {
  const ctxPie = document.getElementById('chartPie')?.getContext('2d');
  const ctxBar = document.getElementById('chartBar')?.getContext('2d');
  const ctxLine = document.getElementById('chartLine')?.getContext('2d');
  
  if (!ctxPie || !ctxBar || !ctxLine) return;

  // Global defaults
  Chart.defaults.color = '#a1a1aa';
  Chart.defaults.font.family = 'Inter';

  // 1. Pass/Fail Pie Chart
  chartPieInstance = new Chart(ctxPie, {
    type: 'doughnut',
    data: {
      labels: ['Passed', 'Failed'],
      datasets: [{
        data: [1, 1], // initial dummy data
        backgroundColor: ['#10b981', '#ef4444'],
        borderWidth: 0,
        hoverOffset: 4
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: '70%',
      plugins: {
        legend: { position: 'bottom', labels: { padding: 20 } }
      }
    }
  });

  // 2. Hourly Bar Chart
  chartBarInstance = new Chart(ctxBar, {
    type: 'bar',
    data: {
      labels: labelsTime,
      datasets: [{
        label: 'Total Detections',
        data: mockHourly,
        backgroundColor: '#06b6d4',
        borderRadius: 4
      }]
    },
    options: chartConfig
  });

  // 3. Trends Line Chart
  chartLineInstance = new Chart(ctxLine, {
    type: 'line',
    data: {
      labels: labelsTime,
      datasets: [{
        label: 'Yield Rate (%)',
        data: mockTrends,
        borderColor: '#3b82f6',
        backgroundColor: 'rgba(59, 130, 246, 0.1)',
        borderWidth: 2,
        fill: true,
        tension: 0.4
      }]
    },
    options: chartConfig
  });
}

// Function attached to window so app.js can trigger it when stats update or tab changes
window.updateCharts = function() {
  if (!chartPieInstance) {
    initCharts();
  }
  
  // Use global totalPass / totalFail from app.js if they exist
  const tp = typeof totalPass !== 'undefined' ? totalPass : 1;
  const tf = typeof totalFail !== 'undefined' ? totalFail : 0;
  
  if (chartPieInstance) {
    chartPieInstance.data.datasets[0].data = [tp === 0 && tf === 0 ? 1 : tp, tf];
    chartPieInstance.update();
  }
};

// Initial setup
document.addEventListener('DOMContentLoaded', () => {
  initCharts();
});
