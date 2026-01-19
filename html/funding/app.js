/**
 * Startup Funding Tracker - Core Logic
 */

// --- State Management ---
const state = {
    apiKey: localStorage.getItem('fundingArgs_apiKey') || '',
    useMock: true,
    articles: [],
    loading: false,
    filters: {
        query: '',
        days: 90
    },
    sort: {
        field: 'date',
        direction: 'desc'
    }
};

// --- Constants ---
const MOCK_STARTUPS = [
    { name: 'Nebula AI', amount: '$45M', round: 'Series A' },
    { name: 'GreenFlow', amount: '$12M', round: 'Seed' },
    { name: 'QuantumBits', amount: '$120M', round: 'Series B' },
    { name: 'HealthSync', amount: '$8.5M', round: 'Seed' },
    { name: 'Orbital Logistics', amount: '$60M', round: 'Series B' },
    { name: 'CryptoVault', amount: '$25M', round: 'Series A' },
    { name: 'AgriTech Solutions', amount: '$4M', round: 'Pre-Seed' },
    { name: 'BlueOcean Robotics', amount: '$200M', round: 'Series C' },
    { name: 'CyberShield', amount: '$33M', round: 'Series A' },
    { name: 'NeuroLink', amount: '$15M', round: 'Series A' }
];

const NEWS_KEYWORDS = [
    'startup funding', 'venture capital', 'raised', 'funding round',
    'investment', 'seed round', 'series A', 'pre-seed'
];

// --- Services ---

class MockService {
    async fetchNews(days) {
        // Simulate network delay
        await new Promise(r => setTimeout(r, 800));

        const count = 25; // Generate 25 mock items
        const results = [];
        const now = new Date();

        for (let i = 0; i < count; i++) {
            const startup = MOCK_STARTUPS[Math.floor(Math.random() * MOCK_STARTUPS.length)];
            const date = new Date(now.getTime() - Math.floor(Math.random() * days * 24 * 60 * 60 * 1000));

            results.push({
                source: { name: 'TechCrunch (Mock)' },
                author: 'Tech Writer',
                title: `${startup.name} raises ${startup.amount} in ${startup.round} funding`,
                description: `Leading innovator ${startup.name} announces new capital injection to fuel growth in their sector.`,
                url: `https://www.google.com/search?q=${encodeURIComponent(startup.name + ' funding news')}`,
                urlToImage: null,
                publishedAt: date.toISOString(),
                // Enriched properties for our app
                _startupName: startup.name,
                _amount: startup.amount,
                _amountValue: this.parseAmount(startup.amount)
            });
        }
        return results;
    }

    parseAmount(str) {
        const num = parseFloat(str.replace(/[^0-9.]/g, ''));
        if (str.includes('B')) return num * 1000000000;
        if (str.includes('M')) return num * 1000000;
        if (str.includes('K')) return num * 1000;
        return num;
    }
}

class NewsService {
    constructor(apiKey) {
        this.apiKey = apiKey;
        this.baseUrl = 'https://newsapi.org/v2/everything';
    }

    async fetchNews(query, days) {
        const date = new Date();
        date.setDate(date.getDate() - days);
        const fromDate = date.toISOString().split('T')[0];

        const q = query || 'startup funding';
        const url = `${this.baseUrl}?q=${encodeURIComponent(q)}&from=${fromDate}&sortBy=publishedAt&language=en&pageSize=50&apiKey=${this.apiKey}`;

        try {
            const res = await fetch(url);
            const data = await res.json();

            if (data.status === 'error') throw new Error(data.message);

            return data.articles.map(article => this.processArticle(article));
        } catch (err) {
            console.error('API Error:', err);
            throw err;
        }
    }

    processArticle(article) {
        // Simple heuristic regex to find money matches like $10M, $50 million, etc.
        const moneyRegex = /\$([0-9.]+)\s?(million|billion|M|B|k)/i;
        const match = article.title.match(moneyRegex) || article.description?.match(moneyRegex);

        let amount = 'Undisclosed';
        let amountValue = 0;

        if (match) {
            amount = match[0];
            const val = parseFloat(match[1]);
            const unit = match[2]?.toUpperCase();

            if (unit.startsWith('B')) amountValue = val * 1000000000;
            else if (unit.startsWith('M')) amountValue = val * 1000000;
            else if (unit.startsWith('K')) amountValue = val * 1000;
            else if (unit === 'MILLION') amountValue = val * 1000000;
            else if (unit === 'BILLION') amountValue = val * 1000000000;
        }

        // Attempt to extract startup name (very basic heuristic: first few words before "raises")
        const nameMatch = article.title.split(/raises|secures|bags|closes/i)[0];
        const startupName = nameMatch && nameMatch.length < 30 ? nameMatch.trim() : 'Unknown Startup';

        return {
            ...article,
            _startupName: startupName,
            _amount: amount,
            _amountValue: amountValue
        };
    }
}


class RssService {
    constructor() {
        this.feeds = [
            'https://techcrunch.com/category/startups/feed/',
            'https://bg.venturebeat.com/feed/'
        ];
        this.proxy = 'https://api.allorigins.win/raw?url=';
    }

    async fetchNews() {
        const promises = this.feeds.map(feed =>
            fetch(this.proxy + encodeURIComponent(feed))
                .then(res => res.text())
        );

        const responses = await Promise.all(promises);
        const articles = responses.flatMap(xml => this.parseXml(xml));
        return articles;
    }

    parseXml(xmlStr) {
        const parser = new DOMParser();
        const xml = parser.parseFromString(xmlStr, 'text/xml');
        const items = Array.from(xml.querySelectorAll('item'));

        return items.map(item => {
            const title = item.querySelector('title')?.textContent || '';
            const description = item.querySelector('description')?.textContent || '';
            const link = item.querySelector('link')?.textContent || '#';
            const pubDate = item.querySelector('pubDate')?.textContent || new Date().toISOString();

            // Re-use logic to extract amounts
            const moneyRegex = /\$([0-9.]+)\s?(million|billion|M|B|k)/i;
            const match = title.match(moneyRegex) || description?.match(moneyRegex);

            let amount = 'Undisclosed';
            let amountValue = 0;

            if (match) {
                amount = match[0];
                const val = parseFloat(match[1]);
                const unit = match[2]?.toUpperCase();

                if (unit.startsWith('B')) amountValue = val * 1000000000;
                else if (unit.startsWith('M')) amountValue = val * 1000000;
                else if (unit.startsWith('K')) amountValue = val * 1000;
                else if (unit === 'MILLION') amountValue = val * 1000000;
                else if (unit === 'BILLION') amountValue = val * 1000000000;
            }

            const nameMatch = title.split(/raises|secures|bags|closes|funding/i)[0];
            const startupName = nameMatch && nameMatch.length < 40 ? nameMatch.trim() : 'Startup News';

            return {
                source: { name: 'RSS Feed' },
                author: 'Unknown',
                title: title,
                description: description.replace(/<[^>]*>?/gm, '').slice(0, 150) + '...', // Strip HTML tags
                url: link,
                urlToImage: null,
                publishedAt: new Date(pubDate).toISOString(),
                _startupName: startupName,
                _amount: amount,
                _amountValue: amountValue
            };
        });
    }
}

// --- Controller ---

const init = () => {
    // Check if we should use mock or real
    if (state.apiKey && state.apiKey.length > 10) {
        state.useMock = false;
    }

    updateStatusIndicator();
    setupEventListeners();
    fetchData(); // Initial load
};

const updateStatusIndicator = () => {
    const el = document.getElementById('status-indicator');
    if (state.useMock) {
        el.className = 'status-indicator mock';
        el.querySelector('.text').textContent = 'Mock Data Mode';
    } else {
        el.className = 'status-indicator';
        el.querySelector('.text').textContent = 'Live API Mode';
    }
};

const fetchData = async () => {
    setLoading(true);
    const container = document.getElementById('results-list');
    container.innerHTML = ''; // Clear current

    try {
        let items;
        if (state.useMock) {
            const service = new MockService();
            items = await service.fetchNews(state.filters.days);
        } else {
            const service = new NewsService(state.apiKey);
            // Construct a search query combining user input + base funding keywords for better relevance
            const baseQuery = state.filters.query || 'startup funding OR venture capital OR "Series A" OR "Series B"';
            items = await service.fetchNews(baseQuery, state.filters.days);
        }

        state.articles = items;
        renderTable();
    } catch (err) {
        showError(err.message);
    } finally {
        setLoading(false);
    }
};

const setLoading = (isLoading) => {
    state.loading = isLoading;
    const loader = document.getElementById('loading-state');
    const empty = document.getElementById('empty-state');

    if (isLoading) {
        loader.classList.remove('hidden');
        empty.classList.add('hidden');
    } else {
        loader.classList.add('hidden');
    }
};

const showError = (msg) => {
    const container = document.getElementById('results-list');
    container.innerHTML = `<div style="padding:40px; text-align:center; color:#ef4444;">Error: ${msg}</div>`;
};

const renderTable = () => {
    const container = document.getElementById('results-list');
    const empty = document.getElementById('empty-state');

    // Sort logic
    const { field, direction } = state.sort;
    const sorted = [...state.articles].sort((a, b) => {
        let valA, valB;

        if (field === 'date') {
            valA = new Date(a.publishedAt).getTime();
            valB = new Date(b.publishedAt).getTime();
        } else if (field === 'amount') {
            valA = a._amountValue || 0;
            valB = b._amountValue || 0;
        } else if (field === 'startup') {
            valA = a._startupName.toLowerCase();
            valB = b._startupName.toLowerCase();
        }

        return direction === 'asc' ? valA - valB : valB - valA;
    });

    if (sorted.length === 0) {
        empty.classList.remove('hidden');
        return;
    } else {
        empty.classList.add('hidden');
    }

    const html = sorted.map(article => `
        <div class="table-row">
            <div class="row-date">${new Date(article.publishedAt).toLocaleDateString()}</div>
            <div class="row-startup">${article._startupName}</div>
            <div class="row-amount">${article._amount}</div>
            <div class="row-news" title="${article.title}">${article.title}</div>
            <div class="row-link">
                <a href="${article.url}" target="_blank" class="link-btn" title="View Source">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path>
                        <polyline points="15 3 21 3 21 9"></polyline>
                        <line x1="10" y1="14" x2="21" y2="3"></line>
                    </svg>
                </a>
            </div>
            
            <!-- Mobile Only View embedded (css hides/shows) -->
        </div>
    `).join('');

    container.innerHTML = html;
};

// --- Exports ---

const exportCSV = () => {
    if (!state.articles.length) return alert('No data to export!');

    const headers = ['Date', 'Startup', 'Amount', 'Headline', 'Source URL'];
    const rows = state.articles.map(a => [
        new Date(a.publishedAt).toISOString().split('T')[0],
        `"${a._startupName.replace(/"/g, '""')}"`, // Handle quotes in CSV
        `"${a._amount}"`,
        `"${a.title.replace(/"/g, '""')}"`,
        a.url
    ]);

    const csvContent = [headers.join(','), ...rows.map(r => r.join(','))].join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);

    const link = document.createElement('a');
    link.setAttribute('href', url);
    link.setAttribute('download', `funding_export_${new Date().toISOString().slice(0, 10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
};

// --- Events ---

const setupEventListeners = () => {
    // Search
    let debounce;
    document.getElementById('search-input').addEventListener('input', (e) => {
        clearTimeout(debounce);
        debounce = setTimeout(() => {
            state.filters.query = e.target.value;
            fetchData();
        }, 600);
    });

    // Date Range
    document.getElementById('date-range').addEventListener('change', (e) => {
        state.filters.days = parseInt(e.target.value);
        fetchData();
    });

    // Sorting
    document.querySelectorAll('.th.sortable').forEach(th => {
        th.addEventListener('click', () => {
            const field = th.dataset.sort;
            if (state.sort.field === field) {
                state.sort.direction = state.sort.direction === 'asc' ? 'desc' : 'asc';
            } else {
                state.sort.field = field;
                state.sort.direction = 'desc';
            }

            // Update UI arrows
            document.querySelectorAll('.th.sortable span').forEach(s => s.textContent = '');
            th.querySelector('span').textContent = state.sort.direction === 'asc' ? '↑' : '↓';

            renderTable();
        });
    });

    // Settings Modal
    const modal = document.getElementById('settings-modal');
    document.getElementById('btn-settings').addEventListener('click', () => {
        document.getElementById('api-key').value = state.apiKey;

        // set radio state
        const radios = document.getElementsByName('source-type');
        let currentSource = state.sourceType || 'rss';
        if (state.useMock && !state.sourceType) currentSource = 'mock'; // Backwards compatibility fallback

        radios.forEach(r => {
            if (r.value === currentSource) r.checked = true;
        });

        toggleApiKeyInput(currentSource);
        modal.showModal();
    });

    // Toggle api key visibility based on selection
    document.getElementsByName('source-type').forEach(r => {
        r.addEventListener('change', (e) => {
            toggleApiKeyInput(e.target.value);
        });
    });

    const toggleApiKeyInput = (val) => {
        const group = document.getElementById('api-key-group');
        if (val === 'api') group.classList.remove('hidden');
        else group.classList.add('hidden');
    };

    document.getElementById('close-modal').addEventListener('click', () => modal.close());

    document.getElementById('save-settings').addEventListener('click', () => {
        const key = document.getElementById('api-key').value.trim();
        const source = document.querySelector('input[name="source-type"]:checked').value;

        state.apiKey = key;
        state.sourceType = source;
        state.useMock = source === 'mock';

        localStorage.setItem('fundingArgs_apiKey', key);
        localStorage.setItem('fundingArgs_source', source);

        updateStatusIndicator();
        modal.close();
        fetchData(); // Refresh with new settings
    });

    // Export
    document.getElementById('btn-export').addEventListener('click', exportCSV);
};

// Start
document.addEventListener('DOMContentLoaded', init);
