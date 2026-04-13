/**
 * @description Updates the application loader progress bar.
 * @param {number} pct - Progress percentage.
 * @param {string} msg - Status message.
 */
const updateAppLoader = (pct, msg) => {
    const fill = UI('appLoaderFill'), text = UI('appLoaderPct'), info = UI('appLoaderMsg');
    if (fill) fill.style.width = pct + '%';
    if (text) text.textContent = pct + '%';
    if (info && msg) info.textContent = msg;
    if (pct >= 100) setTimeout(() => UI('appLoader')?.classList.add('hidden'), 400);
};
