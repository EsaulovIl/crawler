// Заворачиваем в IIFE, чтобы не засорять глобальную область
;(function() {
    // Убедимся, что flatpickr уже загружен
    if (typeof window.flatpickr !== 'function') {
        console.error('Flatpickr не найден — убедитесь, что flatpickr.js подключён перед calendar.js');
        return;
    }

    function initCustomCalendar() {
        flatpickr("#startDate", {
            locale: "ru",
            mode: "single",
            dateFormat: "d.m.Y",
            static: true,
            allowInput: false,
            clickOpens: true,

            // свои маленькие SVG-стрелки
            prevArrow: '<svg viewBox="0 0 8 8"><path d="M5 0 L1 4 L5 8" /></svg>',
            nextArrow: '<svg viewBox="0 0 8 8"><path d="M3 0 L7 4 L3 8" /></svg>',

            onReady(_, __, instance) {
                const cal = instance.calendarContainer;
                // помечаем контейнер, чтобы CSS-правила применились
                cal.classList.add("custom-calendar");

                // кастомизируем хэдер
                const hdr = cal.querySelector(".flatpickr-months");
                hdr.classList.add("custom-header");


                // стилизуем стрелки как круглые чипы
                const prev = hdr.querySelector(".flatpickr-prev-month");
                const next = hdr.querySelector(".flatpickr-next-month");
                prev.classList.add("custom-nav");
                next.classList.add("custom-nav");

                // создаём свой pill с месяцем и годом
                const pill = document.createElement("div");
                pill.className = "current-month-pill";
                const monthName = instance.l10n.months.longhand[instance.currentMonth];
                pill.textContent = `${monthName} ${instance.currentYear}`;

                // перестраиваем содержимое хедера: [prev][pill][next]
                hdr.innerHTML = "";
                hdr.append(prev, pill, next);

                // подвязываем клики
                prev.addEventListener("click", () => instance.changeMonth(-1));
                next.addEventListener("click", () => instance.changeMonth(1));
            },

            onMonthChange(_, __, instance) {
                const pill = instance.calendarContainer.querySelector(".current-month-pill");
                if (pill) {
                const monthName = instance.l10n.months.longhand[instance.currentMonth];
                pill.textContent = `${monthName} ${instance.currentYear}`;
                }
            }
        });
    }

    document.addEventListener("DOMContentLoaded", initCustomCalendar);
})();
