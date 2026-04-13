/**
 * @description Renders the analytics dashboard modal contents.
 */
const renderAnalytics = () => {
    const roles = {}, methods = {}, tags = {};
    const security = { 'Private': 0, 'Public': 0 };
    const complexity = [];
    COMMANDS.forEach(c => {
        let r = c.p.split("/").length > 2 ? c.p.split("/")[1] : 'index';
        roles[r] = (roles[r] || 0) + 1;
        methods[c.m] = (methods[c.m] || 0) + 1;
        const isPrivate = testNeedsToken(c);
        security[isPrivate ? 'Private' : 'Public']++;
        const paramCount = (c.h?.length || 0) + (c.q?.length || 0) + (c.u?.length || 0) + (c.f?.length || 0) + (c.j?.length || 0);
        complexity.push({ name: `${c.m} ${c.p}`, count: paramCount });
    });
    const summary = getMasterSummaryStats();
    const outcomes = { Pass: summary.passed, Fail: summary.failed };
    let totalMs = 0, count = 0, minMs = Infinity, maxMs = 0;
    Object.values(Store.responses).forEach(r => {
        if (!r || typeof r.time !== 'number') return;
        totalMs += r.time;
        count++;
        minMs = Math.min(minMs, r.time);
        maxMs = Math.max(maxMs, r.time);
    });
    const performance = count > 0 ? {
        'Avg Latency': Math.round(totalMs / count),
        'Min Latency': minMs,
        'Max Latency': maxMs
    } : null;
    const renderCard = (title, data, isLatency = false) => {
        if (!data || !Object.keys(data).length) return '';
        const total = isLatency ? 0 : Object.values(data).reduce((a, b) => a + b, 0);
        const maxVal = Math.max(...Object.values(data));
        const items = Object.entries(data)
            .sort((a, b) => isLatency ? (a[0].includes('Avg') ? -1 : 1) : b[1] - a[1])
            .slice(0, 10)
            .map(([k, v]) => {
                const pct = isLatency ? (v / maxVal * 100) : (v / total * 100);
                let barColor = 'var(--accent)';
                if (k.includes('Private')) barColor = 'var(--delete)';
                if (k.includes('Public') || k === 'Pass') barColor = 'var(--primary)';
                if (k === 'Fail') barColor = 'var(--delete)';
                return `
                    <div class="analytics-item">
                        <div class="analytics-item-header">
                            <span>${k}</span>
                            <span class="analytics-count">${v}${isLatency ? 'ms' : ''}</span>
                        </div>
                        <div class="analytics-bar-wrap">
                            <div class="analytics-bar-fill" style="width:${pct}%; background:${barColor}"></div>
                        </div>
                    </div>`;
            }).join('');
        return `
            <div class="analytics-card">
                <h4><span>${title}</span>${total ? `<span style="font-size:11px;font-weight:400;color:var(--muted);background:rgba(255,255,255,0.05);padding:2px 8px;border-radius:10px">Total: ${total}</span>` : ''}</h4>
                <div class="analytics-list">${items}</div>
            </div>`;
    };
    const topComplexity = complexity
        .sort((a, b) => b.count - a.count)
        .slice(0, 5)
        .reduce((a, b) => ({ ...a, [b.name]: b.count }), {});
    UI('analyticsGrid').innerHTML = 
        renderCard('API Roles', roles) + 
        renderCard('HTTP Methods', methods) + 
        renderCard('Security', security) +
        ((summary.passed + summary.failed) > 0 ? renderCard('Run Outcomes', outcomes) : '') +
        (count > 0 ? renderCard('Run Performance', performance, true) : '') +
        renderCard('Top Params', topComplexity);
};
