import { enhanceChipSelect } from "./chip-menu.js";

export function initFilters({ onApply }) {
    const form        = document.getElementById('filters');
    const startDate   = document.getElementById('startDate');
    const endDate     = document.getElementById('endDate');
    const orgSelect   = document.getElementById('organizerSelect');
    const typeSelect  = document.getElementById('typeSelect');
    const fmtSelect   = document.getElementById('formatSelect');

    // Подгрузка списков
    fetch('/api/organizers')
        .then(r => r.json())
        .then(data => data.forEach(o => orgSelect.add(new Option(o, o))));
        enhanceChipSelect(orgSelect);
    fetch('/api/event_types')
        .then(r => r.json())
        .then(data => data.forEach(t => typeSelect.add(new Option(t, t))));
        enhanceChipSelect(typeSelect);
    fetch("/api/formats")
        .then(r => r.json())
        .then(arr => { arr.forEach(f => fmtSelect.add(new Option(f,f))); enhanceChipSelect(fmtSelect); });


    // Обработчик сабмита формы
    form.addEventListener('submit', ev => {
    ev.preventDefault();

    const qs = new URLSearchParams();

    if (startDate.value) qs.set('start_date', startDate.value);
    if (endDate.value)   qs.set('end_date',   endDate.value);

    /* --- множественные параметры --- */
    qs.delete('organizer[]');
    qs.delete('event_type[]');

    const orgCSV  = document.getElementById('organizerSelectHidden')?.value || "";
    const typeCSV = document.getElementById('typeSelectHidden')?.value      || "";
    const fmtCSV  = document.getElementById("formatSelectHidden")?.value    || "";

    orgCSV .split(',').map(s => s.trim()).filter(Boolean)
        .forEach(v => qs.append('organizer[]', v));   // ← скобки!

    typeCSV.split(',').map(s => s.trim()).filter(Boolean)
        .forEach(v => qs.append('event_type[]', v));   // ← скобки!

    fmtCSV.split(",").map(s => s.trim()).filter(Boolean)
        .forEach(v => qs.append("format[]", v))

    console.log('[filters] итоговый QS →', qs.toString());
    onApply(qs);
    });
}

document.addEventListener("DOMContentLoaded", () => {
    // ждём пока flatpickr окажется в window
    if (typeof window.flatpickr !== "function") {
        console.error("Flatpickr not loaded"); return;
    }
    flatpickr("#startDate", { dateFormat: "d.m.Y", locale: "ru" });
    flatpickr("#endDate",   { dateFormat: "d.m.Y", locale: "ru" });
});