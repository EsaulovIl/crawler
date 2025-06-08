import { initFilters } from './filters.js';

//Набор цветов
const baseColors = [
  'rgba(54, 162, 235, 0.7)',
  'rgba(255, 99, 132, 0.7)',
  'rgba(255, 206, 86, 0.7)',
  'rgba(75, 192, 192, 0.7)',
  'rgba(153, 102, 255, 0.7)',
  'rgba(255, 159, 64, 0.7)',
  'rgba(201, 203, 207, 0.7)'
];

// Функция, возвращающая базовый набор RGBA-цветов
function getColorsForData(n) {
  const colors = [];
  for (let i = 0; i < n; i++) {
    // Циклично возвращаем цвет из baseColors
    colors.push(baseColors[i % baseColors.length]);
  }
  return colors;
}

document.addEventListener('DOMContentLoaded', function () {
  // Получаем контекст canvas
  const ctx = document.getElementById('pieChart').getContext('2d');

  // Инициализируем пустой Chart.js
  const chart = new Chart(ctx, {
    type: 'pie',
    data: {
      labels: [],
      datasets: [{
        data: [],
        backgroundColor: [],
        borderColor: 'rgba(255, 255, 255, 0.8)',
        borderWidth: 1
      }]
    },
    options: {
      responsive: true,
      plugins: {
        legend: {
          position: 'bottom',
          labels: {
            boxWidth: 12,
            padding: 10,
            font: { family: "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif'", size: 12, weight: '500' }
          }
        },
        tooltip: {
          enabled: true,
          callbacks: {
            label: context => {
              const label = context.label || '';
              const value = context.parsed || 0;
              return `${label}: ${value}`;
            }
          }
        }
      }
    }
  });

  // Функция загрузки данных и обновления графика
  function updateChart(params = new URLSearchParams()) {
    fetch(`/api/events_by_type?${params.toString()}`)
      .then(response => response.json())
      .then(data => {
        if (!Array.isArray(data) || data.length === 0) {
          console.warn('Нет данных для отображения pie chart');
          chart.data.labels = [];
          chart.data.datasets[0].data = [];
          chart.data.datasets[0].backgroundColor = [];
          return chart.update();
        }
        const labels   = data.map(item => item.event_type);
        const counts   = data.map(item => item.count);
        const colors   = getColorsForData(labels.length);

        chart.data.labels = labels;
        chart.data.datasets[0].data            = counts;
        chart.data.datasets[0].backgroundColor = colors;
        chart.update();
      })
      .catch(err => console.error('Ошибка при получении данных для графика:', err));
  }

  // Инициализируем фильтры, передав updateChart как коллбэк
  initFilters({ onApply: updateChart });

  // Первичный рендер без фильтров
  updateChart();

});
