const MONTH_NAMES = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];

function pad(n) { return n < 10 ? '0' + n : String(n); }

function formatDate(isoDate, fmt) {
    const parts = isoDate.split('-');
    const y = parseInt(parts[0], 10);
    const m = parseInt(parts[1], 10);
    const d = parseInt(parts[2], 10);

    if (fmt === 'dd/mm/yyyy') return `${pad(d)}/${pad(m)}/${y}`;
    if (fmt === 'long') return formatDateLong(isoDate);
    return isoDate;
}

function formatDateLong(isoDate) {
    const [, m, d] = isoDate.split('-').map(Number);
    const year = +isoDate.split('-')[0];
    const n = d % 100;
    const suffix = (n >= 11 && n <= 13) ? 'th' : [, 'st', 'nd', 'rd'][d % 10] || 'th';
    return `${MONTH_NAMES[m - 1]} ${d}${suffix} ${year}`;
}

function applyDateFormat(entries, fmt) {
    const formatter = fmt === 'long' ? formatDateLong : (iso) => formatDate(iso, fmt);
    entries.forEach((entry) => {
        const dateEl = entry.element.querySelector('.journal-date');
        if (dateEl && entry.iso) {
            const formatted = formatter(entry.iso);
            dateEl.textContent = formatted;
            entry.dateDisplay = formatted.toLowerCase();
        }
    });
}

function filterEntries(entries, query) {
    const q = query.toLowerCase().trim();
    entries.forEach((entry) => {
        const matchesQuery = !q || 
            entry.text.includes(q) || 
            entry.dateDisplay.includes(q) || 
            entry.iso.includes(q);
        entry.element.classList.toggle('hidden', !matchesQuery);
    });
}

document.addEventListener('DOMContentLoaded', () => {
    const savedScroll = sessionStorage.getItem('journalScroll');
    if (savedScroll) {
        window.scrollTo(0, parseInt(savedScroll, 10));
    }

    window.addEventListener('beforeunload', () => {
        sessionStorage.setItem('journalScroll', window.scrollY);
    });

    const rows = document.querySelectorAll('.journal-row');
    if (!rows.length) return;

    const entries = [];
    rows.forEach((el) => {
        const dateEl = el.querySelector('.journal-date');
        const textEl = el.querySelector('.journal-text');
        const iso = dateEl?.textContent.trim() || '';

        el.dataset.isoDate = iso;

        entries.push({
            element: el,
            iso: iso,
            text: textEl?.innerText.toLowerCase() || '',
            dateDisplay: dateEl?.innerText.toLowerCase() || ''
        });
    });

    const searchBox = document.getElementById('searchBox');
    const dateFormat = document.getElementById('dateFormat');

    const savedFormat = localStorage.getItem('dateFormat');
    if (savedFormat && dateFormat) {
        dateFormat.value = savedFormat;
    }

    function updateDisplay() {
        applyDateFormat(entries, dateFormat.value);
        filterEntries(entries, searchBox.value);
    }

    if (searchBox) {
        searchBox.addEventListener('input', updateDisplay);
    }

    if (dateFormat) {
        updateDisplay();
        dateFormat.addEventListener('change', () => {
            localStorage.setItem('dateFormat', dateFormat.value);
            updateDisplay();
        });
    }
});
