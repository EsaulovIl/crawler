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

  // Запрашиваем данные у API с json
  fetch('/api/events_by_type')
    .then(response => response.json())
    .then(data => {
      // Если данных нет — показываем заглушку в консоли
      if (!data || data.length === 0) {
        console.warn('Нет данных для отображения pie chart');
        return;
      }

      // Формируем массивы меток и значений
      const labels = data.map(item => item.event_type);
      const counts = data.map(item => item.count);

      // Генерируем столько цветов, сколько у нас секторов
      const bgColors = getColorsForData(labels.length);

      // Создаем новый Chart.js – pie chart
      new Chart(ctx, {
        type: 'pie',
        data: {
          labels: labels,
          datasets: [{
            data: counts,
            backgroundColor: bgColors,
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
                font: {
                  family: "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif",
                  size: 12,
                  weight: '500'
                }
              }
            },
            tooltip: {
              enabled: true,
              callbacks: {
                label: function(context) {
                  const label = context.label || '';
                  const value = context.parsed || 0;
                  return label + ': ' + value;
                }
              }
            }
          }
        }
      });
    })
    .catch(err => {
      console.error('Ошибка при получении данных для графика:', err);
    });
});
