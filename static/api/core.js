
/** @type {any[]} */
let COMMANDS = [];
/** @type {any} */
let SPEC = null;
/** @type {string|null} */
let activeApiTag = null;
/** @type {string} */
let activeMasterResultFilter = 'all';

const d = document;
/**
 * @namespace UI
 * @description Centralized DOM element registry with caching.
 * @param {string} id - The element ID.
 * @returns {HTMLElement}
 */
const UI = id => (UI.cache[id] || (UI.cache[id] = d.getElementById(id)));
UI.cache = {};
const $ = UI;

let curr = null, orig = [];
let activeMasterRunIndex = null, testResponseRaw = '';

const getPathTags = p => p.split(/[\/-]/).filter(x => x.length > 1 && !x.startsWith('{'));

/**
 * @description Toggles the active API tag filter.
 * @param {string} t - Tag name.
 */
const toggleApiTag = t => {
    activeApiTag = activeApiTag === t ? null : t;
    renderApiInfoTags();
    renderApiInfoTable(UI('apiInfoSearch').value);
};

/**
 * @description Toggles the master result table filter (pass/fail/all).
 * @param {string} type - Filter type.
 */
const toggleMasterResultFilter = type => {
    if (type !== 'all' && !getMasterSummaryStats().hasResults) return;
    if (type === 'all') {
        activeMasterResultFilter = 'all';
    } else {
        activeMasterResultFilter = activeMasterResultFilter === type ? 'all' : type;
    }
    renderApiInfoTable(UI('apiInfoSearch').value);
};

const toggleTagCard = () => {
    UI('apiInfoTags').classList.toggle('collapsed');
    UI('tagToggleIcon').classList.toggle('collapsed');
};

/* ── Storage helper ── */
const STORAGE_KEY_TOKEN = 'token';
const STORAGE_KEY_RESPONSE = 'response';
const parseStorageJson = key => {
  const rawValue = localStorage.getItem(key);
  if (rawValue == null) return null;
  try {
    return JSON.parse(rawValue);
  } catch (err) {
    return rawValue;
  }
};
const migrateLegacyStorage = () => {
  const legacyState = parseStorageJson('api_master');
  const legacyResponses = parseStorageJson('api_master_responses');
  const currentToken = localStorage.getItem(STORAGE_KEY_TOKEN);
  if (!currentToken && legacyState && typeof legacyState === 'object') {
    const nextToken = legacyState.token || legacyState.auth?.token;
    if (nextToken) localStorage.setItem(STORAGE_KEY_TOKEN, nextToken);
  }
  if (!localStorage.getItem(STORAGE_KEY_RESPONSE) && legacyResponses && typeof legacyResponses === 'object' && !Array.isArray(legacyResponses) && Object.keys(legacyResponses).length) {
    localStorage.setItem(STORAGE_KEY_RESPONSE, JSON.stringify(legacyResponses));
  }
  localStorage.removeItem('api_master');
  localStorage.removeItem('api_master_responses');
};
migrateLegacyStorage();
/**
 * @namespace Store
 * @description Unified state management for authentication tokens and API responses.
 */
const Store = {
  get token() { return localStorage.getItem(STORAGE_KEY_TOKEN) || ''; },
  set token(v) { if (!v) localStorage.removeItem(STORAGE_KEY_TOKEN); else localStorage.setItem(STORAGE_KEY_TOKEN, v); },

  get responses() {
    try { return JSON.parse(localStorage.getItem(STORAGE_KEY_RESPONSE)) || {}; } catch { return {}; }
  },
  set responses(v) { if (!v || !Object.keys(v).length) localStorage.removeItem(STORAGE_KEY_RESPONSE); else localStorage.setItem(STORAGE_KEY_RESPONSE, JSON.stringify(v)); },

  getResponse(i) { return this.responses[String(i)] || null; },
  setResponse(i, val) {
    const r = this.responses;
    r[String(i)] = val;
    this.responses = r;
  },
  removeResponse(i) {
    const r = this.responses;
    delete r[String(i)];
    this.responses = r;
  },
  clear() {
    localStorage.removeItem(STORAGE_KEY_TOKEN);
    localStorage.removeItem(STORAGE_KEY_RESPONSE);
  }
};
const getStorageSnapshot = () => {
  const snapshot = {};
  [STORAGE_KEY_TOKEN, STORAGE_KEY_RESPONSE].forEach(key => {
    const rawValue = localStorage.getItem(key);
    if (rawValue == null) return;
    snapshot[key] = parseStorageJson(key);
  });
  return snapshot;
};
const getStorageRows = () => {
  const rowList = [];
  const snapshot = getStorageSnapshot();
  if (Object.prototype.hasOwnProperty.call(snapshot, STORAGE_KEY_TOKEN)) {
    rowList.push({ scope: 'token', key: STORAGE_KEY_TOKEN, value: snapshot[STORAGE_KEY_TOKEN], removable: 1 });
  }
  if (Object.prototype.hasOwnProperty.call(snapshot, STORAGE_KEY_RESPONSE)) {
    rowList.push({ scope: 'response', key: STORAGE_KEY_RESPONSE, value: snapshot[STORAGE_KEY_RESPONSE], removable: 1 });
  }
  return rowList;
};
const deleteStorageEntry = row => {
  if (row.key === STORAGE_KEY_TOKEN) {
    Store.token = null;
    return 1;
  }
  if (row.key === STORAGE_KEY_RESPONSE) {
    Store.responses = null;
    return 1;
  }
  return 0;
};

const refreshDebugUi = () => {
  renderStorage();
  updateLoginIndicator();
  renderApiInfoTable(UI('apiInfoSearch').value);
  if (UI('analyticsModal').style.display === 'block') renderAnalytics();
};
const getIcon = v => v ? ICON.check(16) : ICON.cross(16);
const getStatusClass = status => {
  if (status == null) return 'neutral';
  if (status >= 200 && status < 300) return 'success';
  if (status >= 400 || status === 0) return 'error';
  return 'info';
};
const renderStatusBadge = status => {
  if (status == null) return '<span class="status-text neutral">-</span>';
  return `<span class="status-text ${getStatusClass(status)}">${status}</span>`;
};
const renderParamBadges = command => {
  const mapping = [
    { k: 'p', l: 'P', t: 'Path parameters (OpenAPI)', f: c => !!c._paramBadgeP },
    { k: 'h', l: 'H', t: 'Header parameters (OpenAPI)', f: c => !!c._paramBadgeH },
    { k: 'q', l: 'Q', t: 'Query parameters (OpenAPI)', f: c => !!c._paramBadgeQ },
    { k: 'f', l: 'F', t: 'Form data (OpenAPI)', f: c => !!c._paramBadgeF },
    { k: 'b', l: 'B', t: 'JSON body (OpenAPI)', f: c => !!c._paramBadgeB },
    { k: 'o', l: 'O', t: 'Path overrides (Local)', f: c => !!PATH_OVERRIDES[c.p] }
  ];
  return `<div class="param-badge-list">${mapping.map(m => {
    const isOff = !m.f(command);
    return `<span class="param-badge ${m.k} ${isOff ? 'off' : ''}" title="${isOff ? 'Not present' : m.t}">${m.l}</span>`;
  }).join('')}</div>`;
};
const renderRunnerEndpoint = command => {
  if (!command) return '';
  return `<span class="method-badge ${command.m.toLowerCase()}" style="margin-right:0">${command.m}</span><span class="runner-endpoint-path">${he(command.p)}</span>`;
};
const openCurlViewModal = (indexValue, viewType) => {
  viewType = viewType || 'all';
  const command = COMMANDS[indexValue];
  if (!command || command.m === 'WS') return;

  const ovr = PATH_OVERRIDES[command.p];
  const showAll = viewType === 'all';
  const showOvr = viewType === 'ovr';

  // Title & Mode Handling
  const badge = `<span class="method-badge ${command.m.toLowerCase()}" style="margin-right:8px">${command.m}</span>`;
  UI('curlViewTitle').innerHTML = (showOvr && !showAll) ? `API Overrides: ${command.p}` : `${badge}${command.p}`;
  
  // Visibility
  UI('curlViewOvrCard').style.display = (ovr && showOvr) ? 'flex' : 'none';
  UI('curlViewCard').style.display = showAll ? 'flex' : 'none';
  UI('curlViewResCard').style.display = showAll ? 'flex' : 'none';

  if (ovr && showOvr) {
    const ovrText = JSON.stringify(ovr, null, 2);
    UI('curlViewOvrContent').innerHTML = `<pre class="resp-pre" style="padding:16px;margin:0">${highlight(ovrText)}</pre>`;
    UI('curlViewOvrCopy').onclick = () => copyWithFeedback(UI('curlViewOvrCopy'), ovrText, 16, 'Overrides copied');
  }

  if (showAll) {
    const curve = generateCurl(indexValue);
    const formatted = curve.replace(/ -H /g, ' \\\n  -H ').replace(/ -d /g, ' \\\n  -d ').replace(/ -F /g, ' \\\n  -F ');
    UI('curlViewContent').innerHTML = `<pre class="resp-pre" style="padding:16px;margin:0;white-space:pre;overflow-x:auto">${highlightCurl(formatted)}</pre>`;
    UI('curlViewCopy').onclick = () => copyWithFeedback(UI('curlViewCopy'), curve, 16, 'Curl copied');

    if (command.res) {
      const exampleValue = schemaToExample(command.res, SPEC);
      const exampleText = JSON.stringify(exampleValue || { message: 'No schema provided' }, null, 2);
      UI('curlViewResContent').innerHTML = `<pre class="resp-pre" style="padding:16px;margin:0">${highlight(compactArrays(exampleText))}</pre>`;
      UI('curlViewResCopy').onclick = () => copyWithFeedback(UI('curlViewResCopy'), exampleText, 16, 'Expected response copied');
    } else {
      UI('curlViewResContent').innerHTML = `<div style="padding:40px;text-align:center;color:var(--muted);font-style:italic">No expected response schema provided in OpenAPI.</div>`;
      UI('curlViewResCopy').onclick = () => toast('No schema to copy');
    }
  }
  showModal('curlViewModal');
const debounce = (fn, ms) => {
  let t;
  return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms) };
};
async function init() {
  updateAppLoader(5, 'Connecting to server...');
  try {
    updateAppLoader(20, 'Fetching OpenAPI spec...');
    const specR = await fetch('/openapi.json', { cache: 'no-cache' });
    updateAppLoader(40, 'Parsing specification...');
    const spec = await specR.json();
    SPEC = spec;
    if (!spec || !spec.paths) throw new Error("Invalid OpenAPI spec returned");
    COMMANDS = [];
    updateAppLoader(60, 'Generating commands...');
    Object.entries(spec.paths).forEach(([path, methods]) => {
      Object.entries(methods).forEach(([method, op]) => {
        COMMANDS.push(createCommandFromOperation(path, method, op));
      });
    });
    orig = COMMANDS.map((c, i) => ({ ...c, oi: i }));
    updateAppLoader(80, 'Rendering interface...');
    applyMasterTableLayout();
    const b = UI('baseUrl');
    if (b) b.textContent = window.location.origin;
    renderApiInfoTags();
    
    let initialSearch = '';
    const urlParams = new URLSearchParams(window.location.search);
    const runApi = urlParams.get('api');
    if (runApi) {
        const [method, path] = runApi.includes('|') ? runApi.split('|') : [null, runApi];
        const idx = COMMANDS.findIndex(c => c.p === path && (!method || c.m === method.toUpperCase()));
        if (idx !== -1) {
            initialSearch = path;
            UI('apiInfoSearch').value = path;
            const clearBtn = UI('apiInfoSearchClear');
            if (clearBtn) clearBtn.style.display = 'block';
            activeMasterRunIndex = idx;
            setTimeout(() => {
                const cmd = COMMANDS[idx];
                if (cmd && cmd.m === 'WS') {
                    showModal('wsRunnerModal');
                    if (typeof loadWs === 'function') loadWs(idx);
                } else {
                    showModal('apiRunnerModal');
                    load(idx);
                }
            }, 100);
        }
    }
    
    renderApiInfoTable(initialSearch);
    updateLoginIndicator();
    if (!runApi || UI('apiInfoSearch').value !== initialSearch) load(null);
    updateTestSummary();
    setupIcons();
    UI('runnerCurlBtn').innerHTML = ICON.terminal(20);
    setupEventListeners();
    updateAppLoader(100, 'Ready');
  } catch (err) {
    updateAppLoader(100, 'Error');
    console.error('Failed to load API info', err);
    d.getElementById('apiInfoTbl').innerHTML = `<tr><td colspan="9" style="text-align:center;color:var(--delete);padding:20px">Failed to load API info: ${err.message}. Click Refresh to try again.</td></tr>`;
    load(null);
    updateTestSummary();
  }
}

const getMasterBaseIndexes = () => COMMANDS.reduce((acc, c, i) => {
  const searchQuery = UI('apiInfoSearch')?.value?.toLowerCase() || '';
  const matchesPath = !searchQuery || c.p.toLowerCase().includes(searchQuery);
  const matchesMethod = searchQuery && c.m.toLowerCase().includes(searchQuery);
  const allParams = [...c.h, ...c.q, ...c.u, ...c.j, ...c.f];
  const matchesParam = searchQuery && allParams.some(p => p.k.toLowerCase().includes(searchQuery));
  
  const matchesSearch = matchesPath || matchesMethod || matchesParam;
  const matchesTag = !activeApiTag || getPathTags(c.p).includes(activeApiTag);
  if (matchesSearch && matchesTag) acc.push(i);
  return acc;
}, []);

const isMasterPassResponse = responseState => !!responseState && responseState.status >= 200 && responseState.status < 300;

const getVisibleMasterIndexes = () => getMasterBaseIndexes().filter(i => {
  const responseState = Store.getResponse(i);
  if (activeMasterResultFilter === 'pass') return isMasterPassResponse(responseState);
  if (activeMasterResultFilter === 'fail') return responseState ? !isMasterPassResponse(responseState) : 0;
  return 1;
});

const getMasterSummaryStats = () => {
  const visibleIndexes = getMasterBaseIndexes();
  let passed = 0;
  let failed = 0;
  let totalMs = 0;
  let countMs = 0;
  let resultCount = 0;
  visibleIndexes.forEach(i => {
    const responseState = Store.getResponse(i);
    if (!responseState) return;
    resultCount += 1;
    if (isMasterPassResponse(responseState)) passed += 1;
    else failed += 1;
    if (typeof responseState.time === 'number') {
      totalMs += responseState.time;
      countMs += 1;
    }
  });
  return {
    total: visibleIndexes.length,
    resultCount,
    hasResults: resultCount > 0 ? 1 : 0,
    passed,
    failed,
    avg: countMs > 0 ? (totalMs / countMs).toFixed(1) : '0.0'
  };
};
let ws = null;
const loadWs = i => {
  curr = COMMANDS[i];
  const prot = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  UI('wsUrlIn').value = `${prot}//${window.location.host}${curr.p}`;
  UI('wsLogs').innerHTML = '<div style="color:var(--accent)">Waiting to connect...</div>';
  UI('wsConnBtn').textContent = 'Connect';
  UI('wsConnBtn').style.background = 'var(--primary)';
};
d.addEventListener('click', e => {
    const td = e.target.closest('.resp-tbl td[data-raw]');
    if (!td) return;
    const raw = decodeURIComponent(td.dataset.raw);
    const pop = UI('cellPop');
    UI('cellPopTxt').textContent = raw;
    cellPopRaw = raw;
    const r = td.getBoundingClientRect();
    pop.style.left = Math.min(r.left, window.innerWidth - 420) + 'px';
    pop.style.top = (r.bottom + 4) + 'px';
    pop.classList.add('show');
});

UI('rCopy').onclick = () => ResponseView.copy('runner');
UI('rCopyFull').onclick = () => ResponseView.copy('runner', true);
UI('rJson').onclick = () => {
    const s = ResponseView.states.runner;
    if (s) downloadJson('response.json', JSON.stringify(s.json, null, 2));
};


UI('cellPopCopy').onclick = e => {
  e.stopPropagation();
  copyWithFeedback(UI('cellPopCopy'), cellPopRaw, 14);
};
d.addEventListener('keydown', e => {
  if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
    e.preventDefault();
    UI('apiForm').requestSubmit();
  }
  if (e.key === 'Escape') {
    hideModal('apiRunnerModal');
    hideModal('storageModal');
    UI('cellPop').classList.remove('show');
  }
});

/**
 * @description Centralized event listener setup for all UI interactions.
 */
const setupEventListeners = () => {
    // Top-level UI & Toolbars
    UI('tagCardHeader')?.addEventListener('click', toggleTagCard);
    UI('infoToggleBtn')?.addEventListener('click', () => showModal('infoModal'));
    UI('storageToggleBtn')?.addEventListener('click', () => { showModal('storageModal'); renderStorage(); });
    UI('analyticsToggleBtn')?.addEventListener('click', () => { showModal('analyticsModal'); renderAnalytics(); });
    UI('apiInfoCsv')?.addEventListener('click', () => exportCatalogCsv());

    // Search
    UI('apiInfoSearch')?.addEventListener('input', e => {
        const v = e.target.value;
        UI('apiInfoSearchClear').style.display = v ? 'block' : 'none';
        renderApiInfoTable(v);
    });
    UI('apiInfoSearchClear')?.addEventListener('click', () => {
        UI('apiInfoSearch').value = '';
        UI('apiInfoSearchClear').style.display = 'none';
        renderApiInfoTable('');
    });

    // Modals Backdrop Handling
    d.querySelectorAll('.modal').forEach(modal => {
        modal.addEventListener('click', e => { if (e.target === modal) hideModal(modal.id); });
    });

    // Close Buttons
    const closeMapping = {
        'runnerCloseBtn': 'apiRunnerModal',
        'wsRunnerCloseBtn': 'wsRunnerModal',
        'testParamsCloseBtn': 'testParamsModal',
        'masterResponseCloseBtn': 'masterResponseModal',
        'infoCloseBtn': 'infoModal',
        'curlViewCloseBtn': 'curlViewModal',
        'storageCloseBtn': 'storageModal',
        'analyticsCloseBtn': 'analyticsModal'
    };
    Object.entries(closeMapping).forEach(([btnId, modalId]) => {
        UI(btnId)?.addEventListener('click', () => {
            if (modalId === 'wsRunnerModal') wsDisconnect();
            hideModal(modalId);
        });
    });

    // WebSocket Runner
    UI('wsConnBtn')?.addEventListener('click', wsToggleConnect);
    UI('wsSendBtn')?.addEventListener('click', wsSend);
    UI('wsLogsClearBtn')?.addEventListener('click', () => { UI('wsLogs').innerHTML = ''; });
    UI('wsMsgIn')?.addEventListener('keydown', e => { if (e.key === 'Enter') wsSend(); });

    UI('apiForm')?.addEventListener('submit', e => {
        e.preventDefault();
        executeCurrentApi();
    });
    UI('runnerLinkBtn')?.addEventListener('click', () => {
        if (curr) {
            const link = `${window.location.origin}${window.location.pathname}?api=${curr.m}|${curr.p}`;
            copyWithFeedback(UI('runnerLinkBtn'), link, 20, 'Link copied');
        }
    });
    UI('runnerOvrBtn')?.addEventListener('click', () => {
        if (curr) openCurlViewModal(COMMANDS.indexOf(curr), 'ovr');
    });
    UI('runnerCurlBtn')?.addEventListener('click', () => {
        if (curr) openCurlViewModal(COMMANDS.indexOf(curr), 'all');
    });

    // Info Icon Regex Copy (Delegation)
    d.addEventListener('click', e => {
        const btn = e.target.closest('.info-icon-btn');
        if (btn && btn.dataset.regex) {
            e.stopPropagation();
            copyWithFeedback(btn, btn.dataset.regex, 14, 'Regex copied');
        }
    });
    // API Runner Sections
    SECTIONS.forEach(([btn, sec, cont]) => {
        UI(btn)?.addEventListener('click', () => { 
            UI(sec).classList.add('active'); 
            mkRow(UI(cont)); 
            syncParams(); 
        });
        UI(cont)?.addEventListener('input', debounce(syncParams, 500));
        UI(cont)?.addEventListener('change', syncParams);
        UI(cont)?.addEventListener('click', e => { 
            if (e.target.closest('.remove-btn')) setTimeout(syncParams, 0); 
        });
    });

    // Response View Switching (Delegation)
    d.addEventListener('click', e => {
        const btn = e.target.closest('.view-btn');
        if (btn) {
            const scope = btn.classList.contains('master-view-btn') ? 'master' : 'runner';
            ResponseView.switchTo(scope, btn.dataset.view);
        }
    });

    UI('masterRespCopy')?.addEventListener('click', () => {
        const s = ResponseView.states.master;
        if (s.data) copyWithFeedback(UI('masterRespCopy'), JSON.stringify(s.data, null, 2), 16, 'Response copied');
    });
    UI('masterRespCopyFull')?.addEventListener('click', () => {
        const s = ResponseView.states.master;
        if (s.data && s.index !== null) {
            const full = `## CURL\n${generateCurl(s.index)}\n\n## RESPONSE\n${JSON.stringify(s.data, null, 2)}`;
            copyWithFeedback(UI('masterRespCopyFull'), full, 16, 'Curl & Response copied');
        }
    });
    UI('masterRespCsv')?.addEventListener('click', () => {
        const s = ResponseView.states.master;
        if (s.data) downloadCsv('api_response.csv', s.data?.data || s.data?.message || s.data);
    });
    UI('masterRespJson')?.addEventListener('click', () => {
        const s = ResponseView.states.master;
        if (s.data) downloadJson('api_response.json', s.data);
    });

    // Storage Global Actions
    UI('storageCopyAll')?.addEventListener('click', () => {
        const snapshot = getStorageSnapshot();
        copyWithFeedback(UI('storageCopyAll'), JSON.stringify(snapshot, null, 2), 18, 'Full state copied');
    });
    UI('storageResetAll')?.addEventListener('click', () => {
        if (confirm('RESET ALL:\nPermanently delete ALL API Master keys?')) {
            Store.clear();
            activeMasterResultFilter = 'all';
            refreshDebugUi();
            toast('Storage cleared');
        }
    });

    // Login Indicator
    UI('loginIndicator')?.addEventListener('click', () => {
        if (Store.token) {
            if (confirm('LOGOUT:\nThis will delete key: "token" from localStorage. Continue?')) {
                Store.token = null;
                updateLoginIndicator();
                toast('Logged Out');
            }
        } else {
            const idx = COMMANDS.findIndex(c => c.p === '/auth/login-password-username' && c.m === 'POST');
            if (idx !== -1) {
                activeMasterRunIndex = null;
                showModal('apiRunnerModal');
                load(idx);
            } else {
                toast('Login API not found');
            }
        }
    });

    // Local Storage Table Clicks (Delegation)
    UI('apiInfoTags')?.addEventListener('click', e => {
        const tagEl = e.target.closest('.tag-filter');
        if (tagEl) toggleApiTag(tagEl.dataset.tag);
    });

    UI('testSummary')?.addEventListener('click', e => {
        const filterEl = e.target.closest('.clickable');
        if (filterEl) toggleMasterResultFilter(filterEl.dataset.type);
        const runBtn = e.target.closest('#testRunBtn');
        if (runBtn) testRunApis();
        const exportBtn = e.target.closest('#testAllExportCsv');
        if (exportBtn) exportTestCsv();
    });

    // Local Storage Table Clicks (Delegation)
    UI('storageContent')?.addEventListener('click', e => {
        const viewBtn = e.target.closest('.storage-view-btn');
        const copyBtn = e.target.closest('.storage-copy-btn');
        const delBtn = e.target.closest('.storage-del-btn');
        const getRow = btn => {
            const key = btn.dataset.key;
            const scope = btn.dataset.scope;
            return getStorageRows().find(row => row.key === key && row.scope === scope) || null;
        };
        if (viewBtn) {
            const row = getRow(viewBtn);
            if (!row) return;
            const valStr = typeof row.value === 'object' ? JSON.stringify(row.value, null, 2) : String(row.value);
            UI('testResponseTitle').textContent = `Storage Key: ${row.key}`;
            UI('testResponseContent').innerHTML = `<pre class="resp-pre" style="padding:20px;margin:0">${highlight(valStr)}</pre>`;
            UI('testResponseCopy').onclick = () => copyWithFeedback(UI('testResponseCopy'), valStr, 16, 'Copied value');
            showModal('testResponseModal');
        } else if (copyBtn) {
            const row = getRow(copyBtn);
            if (!row) return;
            const valStr = typeof row.value === 'object' ? JSON.stringify(row.value, null, 2) : String(row.value);
            copyWithFeedback(copyBtn, valStr, 14, `Copied value for: ${row.key}`);
        } else if (delBtn) {
            const row = getRow(delBtn);
            if (!row) return;
            if (confirm(`DELETE KEY:\nAre you sure you want to delete "${row.key}" from localStorage?`)) {
                if (!deleteStorageEntry(row)) return;
                renderStorage();
                if (!Object.keys(Store.responses).length) activeMasterResultFilter = 'all';
                refreshDebugUi();
                toast(`Key "${row.key}" deleted`);
            }
        }
    });

    UI('apiInfoTbl')?.addEventListener('click', e => {
        const tr = e.target.closest('tr[data-i]');
        if (!tr) return;
        const idx = parseInt(tr.dataset.i, 10);
        const cmd = COMMANDS[idx];

        // 1. Run Column
        if (e.target.closest('.run-btn')) {
            activeMasterRunIndex = idx;
            if (cmd && cmd.m === 'WS') {
                showModal('wsRunnerModal');
                loadWs(idx);
            } else {
                showModal('apiRunnerModal');
                load(idx);
            }
            return;
        }

        // 2. View Override from Master Row
        const ovrBtn = e.target.closest('.ovr-btn');
        if (ovrBtn) {
            if (ovrBtn.classList.contains('clickable')) openCurlViewModal(idx, 'ovr');
            return;
        }

        // 3. Status Column
        if (e.target.closest('.master-status-cell.clickable')) {
            openMasterResponse(idx);
            return;
        }
    });

    // Tree Toggles (Delegation)
    d.addEventListener('click', e => {
        const toggle = e.target.closest('.tree-toggle');
        if (toggle) {
            toggle.nextElementSibling.classList.toggle('show');
            toggle.querySelector('.tree-arrow').classList.toggle('open');
        }
    });
};
init();
