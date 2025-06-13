export function enhanceChipSelect(sel) {
    if (sel.dataset.chipEnhanced) return;
    sel.dataset.chipEnhanced = "1";
    console.log("[chip-menu] enhance", sel.id);

    const hidden = document.createElement("input");
    hidden.id = sel.id + "Hidden";
    hidden.type = "hidden";
    hidden.name = sel.name.endsWith("[]") ? sel.name : sel.name + "[]";
    sel.after(hidden);

    const labelOpt = sel.options[0];

    /* меню в <body> поверх всего */
    const menu = document.createElement("ul");
    menu.className = "chip-menu";
    menu.hidden = true;
    document.body.append(menu);

    /* массив выбранных value */
    const chosen = new Set();

    const redrawLabel = () => {
        const list = Array.from(chosen);
        let txt = "Любой";
        if (list.length) {
            const joined = list.join(", ");
            txt = joined.length > 40 ? `${list.slice(0,2).join(", ")}…` : joined;
        }
        labelOpt.textContent = txt;
        labelOpt.value = list.join(",");
        sel.selectedIndex = 0;
        hidden.value = list.join(",");
    };

    const rebuildMenu = () => {
        menu.innerHTML = "";
        Array.from(sel.options).forEach(opt => {
            if (opt === labelOpt) return;
            const li = document.createElement("li");
            li.className = "chip-item";
            li.textContent = opt.textContent;
            li.classList.toggle("is-active", chosen.has(opt.value));
            li.onclick = () => {
                chosen.has(opt.value) ? chosen.delete(opt.value) : chosen.add(opt.value);
                redrawLabel();
                rebuildMenu(); // перерисовка меню
            };
            menu.append(li);
        });
    };

    /* ───────── открытие меню ───────── */
    sel.addEventListener("mousedown", e => {
        e.preventDefault();
        rebuildMenu();
        const r = sel.getBoundingClientRect();
        menu.style.left = `${r.left}px`;
        menu.style.top = `${r.bottom + 8}px`;
        menu.style.width = `${r.width}px`;
        menu.hidden = !menu.hidden;
    });

    /* клик вне — закрыть */
    document.addEventListener("click", e => {
        if (!menu.hidden && !menu.contains(e.target) && e.target !== sel) {
            menu.hidden = true;
        }
    });

    /* начальная инициализация */
    redrawLabel();
}

/* auto-init всех .chip-select */
document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll("select.chip-select").forEach(enhanceChipSelect);
});
