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

function applyDateFormat(rowData, fmt) {
    const formatter = fmt === 'long' ? formatDateLong : (iso) => formatDate(iso, fmt);
    rowData.forEach(({ element, iso, dateDisplayRef }) => {
        const dateEl = element.querySelector('.journal-date');
        if (dateEl && iso) {
            const formatted = formatter(iso);
            dateEl.textContent = formatted;
            if (dateDisplayRef) dateDisplayRef.current = formatted.toLowerCase();
        }
    });
}

function filterRows(rowData, searchBox) {
    const q = (searchBox?.value || '').toLowerCase().trim();

    rowData.forEach(({ element, iso, text, dateDisplayRef }) => {
        const dateDisplay = dateDisplayRef?.current || '';
        const matchesQuery = !q || text.includes(q) || dateDisplay.includes(q) || iso.includes(q);
        element.classList.toggle('hidden', !matchesQuery);
    });
}

function init() {
    const savedScroll = sessionStorage.getItem('journalScroll');
    if (savedScroll) {
        window.scrollTo(0, parseInt(savedScroll, 10));
    }

    window.addEventListener('beforeunload', () => {
        sessionStorage.setItem('journalScroll', window.scrollY);
    });

    const rows = document.querySelectorAll('.journal-row');
    if (!rows.length) return;

    const rowData = [];
    rows.forEach((el) => {
        const dateEl = el.querySelector('.journal-date');
        const textEl = el.querySelector('.journal-text');
        const iso = dateEl?.textContent.trim() || '';

        el.dataset.isoDate = iso;

        const dateDisplayRef = { current: '' };
        dateDisplayRef.current = dateEl?.innerText.toLowerCase() || '';

        rowData.push({
            element: el,
            iso,
            text: textEl?.innerText.toLowerCase() || '',
            dateDisplay: dateEl?.innerText.toLowerCase() || '',
            dateDisplayRef
        });
    });

    const searchBox = document.getElementById('searchBox');
    const dateFormat = document.getElementById('dateFormat');

    const savedFormat = localStorage.getItem('dateFormat');
    if (savedFormat && dateFormat) {
        dateFormat.value = savedFormat;
    }

    if (searchBox) searchBox.addEventListener('input', () => filterRows(rowData, searchBox));
    if (dateFormat) {
        applyDateFormat(rowData, dateFormat.value);
        rowData.forEach(({ element, dateDisplayRef }) => {
            const dateEl = element.querySelector('.journal-date');
            if (dateEl) dateDisplayRef.current = dateEl.innerText.toLowerCase();
        });
        dateFormat.addEventListener('change', (e) => {
            localStorage.setItem('dateFormat', e.target.value);
            applyDateFormat(rowData, e.target.value);
            rowData.forEach(({ element, dateDisplayRef }) => {
                const dateEl = element.querySelector('.journal-date');
                if (dateEl) dateDisplayRef.current = dateEl.innerText.toLowerCase();
            });
            filterRows(rowData, searchBox);
        });
    }

    filterRows(rowData, searchBox);
}

init();
