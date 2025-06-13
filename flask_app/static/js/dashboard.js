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


Chart.defaults.color = 'rgba(255,255,255,.7)';
Chart.defaults.font.family = "'Inter', sans-serif";
Chart.defaults.font.weight = 500;


// Функция, возвращающая базовый набор RGBA-цветов
function getColorsForData(n) {
    const colors = [];
    for (let i = 0; i < n; i++) {
        colors.push(baseColors[i % baseColors.length]);
    }
    return colors;
}


function makeSpark(ctx){
    const ds = {
        data: [],
        borderColor:'#4CAF50',
        backgroundColor:'transparent',
        tension:.4, borderWidth:2,
        pointRadius:(ctx)=> ctx.dataIndex === ctx.dataset.data.length-1 ? 4 : 0,
        pointBackgroundColor:'#4CAF50'
    };
    return new Chart(ctx,{
        type:'line',
        data:{ labels:[], datasets:[ds] },
        options:{
          responsive:false, animation:false,
          scales:{ x:{display:false}, y:{display:false} },
          plugins:{ legend:{display:false}, tooltip:{enabled:false} }
        }
    });
}


document.addEventListener('DOMContentLoaded', () => {

    // Контексты для дашборда
    const trendCtx = document.getElementById('trendChart').getContext('2d');
    const radarCtx = document.getElementById('radarChart').getContext('2d');
    const orgCtx = document.getElementById('orgChart').getContext('2d');
    const orgLegendBox = document.getElementById('orgLegend');
    const tfCtx = document.getElementById('typeFormatChart').getContext('2d');
    const formatCtx = document.getElementById('formatChart').getContext('2d');
    const formatLegendBox = document.getElementById('formatLegend');

    const totalSpark = makeSpark(document.getElementById('totalSpark').getContext('2d'));
    const topSpark   = makeSpark(document.getElementById('topSpark').getContext('2d'));

    const typeCtx = document.getElementById('typeDonut').getContext('2d');
    const typeLegendBox = document.getElementById('typeLegend');

    const stackCtx = document.getElementById('stackChart').getContext('2d');

    // Линейный график «Событий во времени»
    const trendChart = new Chart(trendCtx, {
        type: 'line',
        data: { labels: [], datasets: [] },
        options: {
            responsive: true,
            interaction: { mode: 'nearest', intersect: false },
            scales:{
                x:{
                    grid:{ color:'rgba(255,255,255,.20)', lineWidth:1, borderDash:[3,3] },
                    ticks:{
                        maxRotation:0,
                        autoSkip:false,
                        padding:8,
                        callback: function(val,idx,values){
                            /* this.getLabelForValue(val) – текущий текст */
                            const label = this.getLabelForValue(val);
                            /* переносим при > 10 символов */
                            return label.length>10
                            ? label.match(/.{1,10}/g) // разбить по 10 символов
                            : label;
                        }
                    }
                },
                y:{ grid:{ color:'rgba(255,255,255,.20)', lineWidth:1, borderDash:[3,3] },
                beginAtZero:true, title:{ display:true, text:'Количество' } }
            },
            elements:{
                line:{ tension:.4, borderWidth:2 },
                point:{ radius:4, hoverRadius:6 }
            },
            plugins:{
                legend:{ position:'bottom' },
                datalabels:{
                    color: 'rgba(255,255,255,.7)',
                    align: 'top',
                    formatter:value => value
                }
            }
        }
    });


    // Radar chart «Доля типов мероприятий»
    const radarChart = new Chart(radarCtx, {
        type: 'radar',
        data: { labels: [], datasets: [] },
        options: {
            responsive: true,
            scales: {
                r: {
                    grid : { color:'rgba(255,255,255,.20)', lineWidth:1 },
                    angleLines : { color:'rgba(255,255,255,.20)', lineWidth:1 },
                    beginAtZero: true,
                    ticks: { backdropColor: 'transparent', stepSize: 20 }
                }
            },
            elements: { line: { borderWidth: 2 } },
            plugins : {
                legend : {
                    position: 'bottom',
                    labels : {
                        usePointStyle: true,    // вместо квадрата
                        pointStyle : 'circle',  // кружок в легенде
                        boxWidth : 6,
                        boxHeight : 6,
                        padding : 12,
                        font : { size: 12, weight: 500 }
                    }
                }
            }
        }
    });

    // Круговая диаграмма «Доля организаторов»
    const orgChart = new Chart(orgCtx, {
        type: 'doughnut',
        data: {
            labels: [],
            datasets: [{
                data: [],
                backgroundColor: getColorsForData(10),
                borderWidth: 0,
            }],
            /* кастомное поле по центру */
            totalValue: 0
        },
        options: {
            cutout: '35%', // диаметр doughnut chart
            responsive: true,
            plugins: {
                legend: { display:false },
                datalabels:{ anchor:'end', align:'end', offset:8,
                    color:ctx=>ctx.dataset.backgroundColor[ctx.dataIndex],
                    formatter:(v,ctx)=>`${ctx.chart.data.labels[ctx.dataIndex]}\n${v}`
                }
            }
        }
    });

    // Bar chart с распределением по форматам и типам мероприятий
    const tfChart = new Chart(tfCtx, {
        type : 'bar',
        data : { labels: [], datasets: [] },
        options : {
            responsive : true,
            interaction: { intersect:false },
            scales : {
                x : { stacked:true,
                    grid:{ color:'rgba(255,255,255,.20)', lineWidth:1 , borderDash:[3,3] },
                    ticks:{ maxRotation:0, autoSkip:false, padding:6 } },
                y : { stacked:true,
                    beginAtZero:true,
                    grid:{ color:'rgba(255,255,255,.20)', lineWidth:1 , borderDash:[3,3] },
                    title:{ display:true, text:'Количество' } }
            },
            plugins : {
                legend : { position:'bottom',
                    labels : { usePointStyle:true, pointStyle:'circle',
                       boxWidth:6, boxHeight:6, font:{size:12,weight:500} }
                },
                datalabels:{
                    color:'#ffffff', anchor:'center', align:'center', font:{size:11},
                    formatter:v=>v
                }
            }
        }
    });

    // donut chart «по форматам»
    const formatChart = new Chart(formatCtx, {
        type: 'doughnut',
        data: { labels: [], datasets: [{
            data: [], backgroundColor: getColorsForData(10), borderWidth:0 }],
            totalValue: 0
        },
        options:{
            cutout:'35%',
            plugins:{
                legend:{ display:false },
                datalabels:{
                    anchor:'end', align:'end', offset:16, clamp:true,
                    font:{ size:13, weight:600 },
                    color:ctx=>ctx.dataset.backgroundColor[ctx.dataIndex],
                    formatter:(v,ctx)=>`${ctx.chart.data.labels[ctx.dataIndex]}\n${v}`
                }
            }
        }
    });

    // donut chart «по типам»
    const typeDonut = new Chart(typeCtx, {
        type: 'doughnut',
        data: {
            labels: [],
            datasets: [{
                data: [],
                backgroundColor: getColorsForData(12),
                borderWidth: 0
            }],
            totalValue: 0
        },
        options: {
            cutout: '35%',
            responsive: true,
            plugins: {
                legend: { display: false },
                datalabels:{
                    anchor:'end', align:'end', offset:16, clamp:true,
                    font:{ weight:600, size:13 },
                    color: ctx => ctx.dataset.backgroundColor[ctx.dataIndex],
                    formatter:(v,ctx)=>`${ctx.chart.data.labels[ctx.dataIndex]}\n${v}`
                }
            }
        }
    });

    // bar chart «типы по годам»
    const stackChart = new Chart(stackCtx, {
        type: 'bar',
        data: { labels: [], datasets: [] },
        options:{
            responsive: true,
            interaction:{ mode:'index', intersect:false },
            scales:{
                x:{ stacked:true, grid:{ color:'rgba(255,255,255,.20)', dash:[3,3] } },
                y:{ stacked:true, grid:{ color:'rgba(255,255,255,.20)', dash:[3,3] },
                  beginAtZero:true }
            },
            plugins:{
                legend:{ position:'bottom',
                    labels:{ usePointStyle:true, boxWidth:10 } }
            }
        }
    });

    /* Карточка-индикатор */
    async function updateSummary(){
        /* Общие значения по годам */
        const yearRows = await fetch("/api/yearly_totals").then(r=>r.json());
        if(!yearRows.length) return;

        const totalSeries = yearRows.map(o=>o.cnt);
        const totalYears = yearRows.map(o=>o.year);
        totalSpark.data.labels = totalYears;
        totalSpark.data.datasets[0].data = totalSeries;

        /* динамика -> цвет */
        const totalUp = totalSeries.at(-1) >= (totalSeries.at(-2) ?? totalSeries.at(-1));
        const totColor = totalUp ? '#34C759' : '#FF3B30';
        Object.assign(totalSpark.data.datasets[0], {
            borderColor: totColor,
            pointBackgroundColor: totColor
        });
        totalSpark.update();

        /* подписи + стрелка */
        const box = document.getElementById('totalNow');
        box.textContent = totalSeries.at(-1);
        const vb = box.parentElement;
        vb.classList.toggle('up', totalUp);
        vb.classList.toggle('down', !totalUp);
        document.getElementById('totalCaption')
              .textContent = `Мероприятий в ${totalYears.at(-1)} году`;

        /* top-type текущего года */
        const top = await fetch("/api/top_type_current_year").then(r=>r.json());
        if(!top.type) return;

        const topSeries = top.series;
        const topYears = Array.from({length: topSeries.length}, (_,i)=> top.begin_year + i);

        const topUp = topSeries.at(-1) >= (topSeries.at(-2) ?? topSeries.at(-1));
        const topColor = topUp ? '#34C759' : '#FF3B30';

        topSpark.data.labels = topYears;
        topSpark.data.datasets[0].data = topSeries;
        Object.assign(topSpark.data.datasets[0], {
            borderColor: topColor,
            pointBackgroundColor: topColor
        });
        topSpark.update();

        const box2 = document.getElementById('topNow');
        const wrap2 = document.getElementById('topBox');
        box2.textContent = topSeries.at(-1);
        wrap2.classList.toggle('up', topUp);
        wrap2.classList.toggle('down', !topUp);
        document.getElementById('topCaption')
            .textContent = `${top.type} в ${topYears.at(-1)} году`;
    }


    // Функция обновления всех виджетов
    function updateAll(params = new URLSearchParams()) {
        const qs = params.toString() ? `?${params}` : '';

        // Динамика событий во времени
        fetch(`/api/trend_by_type${qs}`)
        .then(r => r.json())
        .then(arr => {
            /* уникальные типы (по оси X) */
            const labels = [...new Set(arr.map(o => o.event_type))];
            /* уникальные годы -> дата-сеты */
            const years  = [...new Set(arr.map(o => o.year))].sort();
            const datasets = years.map((year,i)=>{
                const data = labels.map(t=>{
                    const row = arr.find(o => o.event_type===t && o.year===year);
                    return row ? row.count : 0;
                });
                return {
                    label: year.toString(),
                    data,
                    borderColor: baseColors[i % baseColors.length],
                    backgroundColor: baseColors[i % baseColors.length],
                    fill:false
                };
            });

            trendChart.data.labels = labels;
            trendChart.data.datasets = datasets;
            trendChart.update();
        })
        .catch(err => console.error('Trend by type error:', err));

        // Доля типов мероприятий
        fetch(`/api/top_event_types_radar${qs}`)
            .then(r => r.json())
            .then(arr => {
                const types = [...new Set(arr.map(o => o.event_type))];
                const years = [...new Set(arr.map(o => o.year))].sort();

                const datasets = years.map((year,i)=>({
                  label : year.toString(),
                  data  : types.map(t=>{
                    const row = arr.find(o => o.event_type===t && o.year===year);
                    return row ? row.count : 0;
                  }),
                  borderColor : baseColors[i % baseColors.length],
                  backgroundColor : baseColors[i % baseColors.length].replace('0.7','0.15'),
                  fill:true, pointRadius:3
                }));

                /* вычисляем адаптивную шкалу */
                const maxVal = Math.max(...datasets.flatMap(ds => ds.data));
                const niceMax = Math.ceil(maxVal / 10) * 10; // округляем вверх до десятка
                const step = niceMax / 5 || 1;  // 5 колец (если 0 то 1)

                radarChart.options.scales.r.max = niceMax;
                radarChart.options.scales.r.ticks.stepSize = step;

                radarChart.data.labels   = types;
                radarChart.data.datasets = datasets;
                radarChart.update();
            })
            .catch(err => console.error('Radar error:', err));

        // Доля форматов проведения
        fetch(`/api/events_by_organizer${qs}`)
            .then(r => r.json())
            .then(arr => {
                const labels = arr.map(o => o.organizer);
                const data = arr.map(o => o.count);
                orgChart.data.labels = labels;
                orgChart.data.datasets[0].data = data;
                orgChart.data.datasets[0].backgroundColor = getColorsForData(labels.length);
                /* сумма для центр-текста */
                orgChart.data.totalValue = data.reduce((s,n)=>s+n,0);
                orgChart.update();

                orgLegendBox.innerHTML = '';
                labels.forEach((lbl,i)=>{
                    const color = orgChart.data.datasets[0].backgroundColor[i];
                    const li = document.createElement('li');
                    li.innerHTML = `<span class="bullet" style="background:${color}"></span>${lbl}`;
                    orgLegendBox.append(li);
                });
            })
            .catch(err => console.error('Organizer pie error:', err));

        // распределение форматов по типам
        fetch(`/api/events_by_type_format${qs}`)
            .then(r=>r.json())
            .then(arr=>{
                const types = [...new Set(arr.map(o=>o.event_type))];
                const formats = ['Онлайн','Гибрид','Очно']; // порядок в легенде

                const colorMap = {
                  'Онлайн': baseColors[0],
                  'Гибрид': baseColors[2],
                  'Очно' : baseColors[4]
                };

                const datasets = formats.map(fmt=>({
                  label : fmt,
                  backgroundColor : colorMap[fmt],
                  data : types.map(t=>{
                    const row = arr.find(o=>o.event_type===t && o.event_format===fmt);
                    return row ? row.count : 0;
                  })
                }));

                tfChart.data.labels = types;
                tfChart.data.datasets = datasets;
                tfChart.update();
            })
            .catch(err=>console.error('Type-format bar error:',err));

        fetch(`/api/events_by_format${qs}`)
            .then(r=>r.json())
            .then(arr=>{
                const labels = arr.map(o=>o.event_format);
                const data   = arr.map(o=>o.count);

                formatChart.data.labels = labels;
                formatChart.data.datasets[0].data = data;
                formatChart.data.datasets[0].backgroundColor= getColorsForData(labels.length);
                formatChart.data.totalValue = data.reduce((s,n)=>s+n,0);
                formatChart.update();

                // легенда-кружочки
                formatLegendBox.innerHTML = '';
                labels.forEach((lbl,i)=>{
                    const colour = formatChart.data.datasets[0].backgroundColor[i];
                    formatLegendBox.insertAdjacentHTML('beforeend',
                      `<li><span class="bullet" style="background:${colour}"></span>${lbl}</li>`);
                });
            })
            .catch(err=>console.error('Format donut error:', err));

        fetch(`/api/events_by_event_type${qs}`)
            .then(r => r.json())
            .then(arr => {
                const labels = arr.map(o => o.event_type);
                const data = arr.map(o => o.count);
                typeDonut.data.labels = labels;
                typeDonut.data.datasets[0].data = data;
                typeDonut.data.datasets[0].backgroundColor = getColorsForData(labels.length);
                typeDonut.data.totalValue = data.reduce((s,n)=>s+n,0);
                typeDonut.update();

                // кастомная легенда
                typeLegendBox.innerHTML = '';
                labels.forEach((lbl,i)=>{
                    const color = typeDonut.data.datasets[0].backgroundColor[i];
                    typeLegendBox.insertAdjacentHTML(
                        'beforeend',
                        `<li><span class="bullet" style="background:${color}"></span>${lbl}</li>`
                    );
                });
            })
            .catch(err => console.error('Type-donut error:', err));

        fetch(`/api/event_types_by_year${qs}`)
            .then(r => r.json())
            .then(arr =>{
                const years = [...new Set(arr.map(o=>o.year))].sort();
                const types = [...new Set(arr.map(o=>o.event_type))];

                const datasets = types.map((t,i)=>{
                    const data = years.map(y=>{
                        const row = arr.find(o=>o.year===y && o.event_type===t);
                        return row ? row.count : 0;
                    });
                    return {
                        label: t,
                        data,
                        backgroundColor: baseColors[i % baseColors.length],
                        borderWidth:0
                    };
                });

                stackChart.data.labels   = years;
                stackChart.data.datasets = datasets;
                stackChart.update();
            })
            .catch(err=>console.error('Stack chart error', err));

        updateSummary();
    }

    // Подключаем фильтры
    initFilters({ onApply: updateAll });

    // Первичная отрисовка без фильтров
    updateAll();
});

async function loadSummary() {
    const r = await fetch("/api/summary");
    const j = await r.json();
    document.getElementById("kpiPlanned").textContent = j.planned ?? "–";
    document.getElementById("kpiFinished").textContent = j.finished ?? "–";
    document.getElementById("kpiToday").textContent = j.today ?? "–";
}
loadSummary();