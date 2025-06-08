export function initFilters({ onApply }) {
  const form        = document.getElementById('filters');
  const startDate   = document.getElementById('startDate');
  const endDate     = document.getElementById('endDate');
  const orgSelect   = document.getElementById('organizerSelect');
  const typeSelect  = document.getElementById('typeSelect');

  // Подгрузка списков
  fetch('/api/organizers')
    .then(r => r.json())
    .then(data => data.forEach(o => orgSelect.add(new Option(o, o))));
  fetch('/api/event_types')
    .then(r => r.json())
    .then(data => data.forEach(t => typeSelect.add(new Option(t, t))));

  // Обработчик сабмита формы
  form.addEventListener('submit', ev => {
    ev.preventDefault();
    const params = new URLSearchParams();
    if (startDate.value)  params.set('start_date',  startDate.value);
    if (endDate.value)    params.set('end_date',    endDate.value);
    if (orgSelect.value)  params.set('organizer',   orgSelect.value);
    if (typeSelect.value) params.set('event_type',  typeSelect.value);

    onApply(params);
  });
}
