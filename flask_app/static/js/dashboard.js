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
    colors.push(baseColors[i % baseColors.length]);
  }
  return colors;
}

document.addEventListener('DOMContentLoaded', () => {

  // Контексты для дашборда
  const totalEl = document.getElementById('totalCount');
  const lineCtx   = document.getElementById('lineChart').getContext('2d');
  const typeCtx   = document.getElementById('pieChart').getContext('2d');
  const formatCtx = document.getElementById('formatChart').getContext('2d');

  // Линейный график «Событий во времени»
  const lineChart = new Chart(lineCtx, {
    type: 'line',
    data: {
      labels: [],
      datasets: [{
        label: 'Событий',
        data: [],
        borderColor: baseColors[0],
        backgroundColor: 'transparent',
        tension: 0.3
      }]
    },
    options: {
      responsive: true,
      scales: {
        x: { title: { display: true, text: 'Дата' } },
        y: { title: { display: true, text: 'Количество' }, beginAtZero: true }
      }
    }
  });

  // Круговая диаграмма «Доля типов мероприятий»
  const typeChart = new Chart(typeCtx, {
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
          callbacks: {
            label: context => `${context.label}: ${context.parsed}`
          }
        }
      }
    }
  });

  // Круговая диаграмма «Доля форматов проведения»
  const formatChart = new Chart(formatCtx, {
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
      plugins: { legend: { position: 'bottom' } }
    }
  });

  // Функция обновления всех виджетов
  function updateAll(params = new URLSearchParams()) {
    const qs = params.toString() ? `?${params}` : '';

    // Общее количество
    fetch(`/api/events_summary${qs}`)
      .then(r => r.json())
      .then(d => { totalEl.textContent = d.total; })
      .catch(err => console.error('Summary error:', err));

    // Динамика событий во времени
    fetch(`/api/events_over_time${qs}`)
      .then(r => r.json())
      .then(arr => {
        const labels = arr.map(o => o.period);
        const data   = arr.map(o => o.count);
        lineChart.data.labels           = labels;
        lineChart.data.datasets[0].data = data;
        lineChart.update();
      })
      .catch(err => console.error('Trend error:', err));

    // Доля типов мероприятий
    fetch(`/api/events_by_type${qs}`)
      .then(r => r.json())
      .then(arr => {
        const labels = arr.map(o => o.event_type);
        const data   = arr.map(o => o.count);
        typeChart.data.labels                   = labels;
        typeChart.data.datasets[0].data         = data;
        typeChart.data.datasets[0].backgroundColor = getColorsForData(labels.length);
        typeChart.update();
      })
      .catch(err => console.error('Type pie error:', err));

    // Доля форматов проведения
    fetch(`/api/events_by_format${qs}`)
      .then(r => r.json())
      .then(arr => {
        const labels = arr.map(o => o.format);
        const data   = arr.map(o => o.count);
        formatChart.data.labels                   = labels;
        formatChart.data.datasets[0].data         = data;
        formatChart.data.datasets[0].backgroundColor = getColorsForData(labels.length);
        formatChart.update();
      })
      .catch(err => console.error('Format pie error:', err));
  }

  // Подключаем фильтры
  initFilters({ onApply: updateAll });

  // Первичная отрисовка без фильтров
  updateAll();
});
