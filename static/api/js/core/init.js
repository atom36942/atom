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
 * @description Refreshes and re-renders all dynamic UI components.
 */
const refreshDebugUi = () => {
  renderStorage();
  updateLoginIndicator();
  renderApiInfoTable(UI('apiInfoSearch').value);
  if (UI('analyticsModal').style.display === 'block') renderAnalytics();
};

/**
 * @description Main application entry point. Initializes state, fetches OpenAPI, and renders the UI.
 */
async function init() {
  injectModals();
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
                    loadWs(idx);
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
        'paramInfoCloseBtn': 'paramInfoModal',
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
    UI('paramInfoCopyBtn')?.addEventListener('click', () => {
        const txt = UI('paramInfoBody').innerText;
        if (txt) copyWithFeedback(UI('paramInfoCopyBtn'), txt, 20, 'Details copied');
    });
    UI('runnerCurlBtn')?.addEventListener('click', () => {
        if (curr) openCurlViewModal(COMMANDS.indexOf(curr), 'all');
    });

    // Info Icon Regex/Desc Modal (Delegation)
    d.addEventListener('click', e => {
        const btn = e.target.closest('.info-icon-btn');
        if (btn) {
            e.stopPropagation();
            showInfoModal(btn.dataset.key || '', btn.dataset.regex || '', btn.dataset.desc || '');
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
            const idx = COMMANDS.findIndex(c => c.p === '/auth/login-username-password' && c.m === 'POST');
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

        const ovrBtn = e.target.closest('.ovr-btn');
        if (ovrBtn) {
            if (ovrBtn.classList.contains('clickable')) openCurlViewModal(idx, 'ovr');
            return;
        }

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
    
    // Global Event Handlers
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
};

/**
 * @description Centralized icon setup for persistent UI elements.
 */
const setupIcons = () => {
    const iconMap = {
        'infoToggleBtn': ICON.info(18),
        'storageToggleBtn': ICON.database(18),
        'analyticsToggleBtn': ICON.chart(18),
        'apiInfoCsv': ICON.download(18),
        'btnRaw': ICON.code(16),
        'btnPretty': ICON.list(16),
        'btnTable': ICON.table(16),
        'rCopy': ICON.copy(16),
        'rCopyFull': ICON.copyCurl(16),
        'rCsv': ICON.fileCsv(16),
        'rJson': ICON.fileJson(16),
        'testAllExportCsv': ICON.download(16),
        'testResponseJson': ICON.fileJson(20),
        'testResponseCopy': ICON.copy(20),
        'testParamsCopyCurl': ICON.copy(20),
        'storageCopyAll': ICON.copy(18),
        'storageResetAll': ICON.trash(18),
        'cellPopCopy': ICON.copy(14),
        'curlViewCopy': ICON.copy(16),
        'curlViewResCopy': ICON.copy(16),
        'curlViewOvrCopy': ICON.copy(16),
        'masterBtnRaw': ICON.code(16),
        'masterBtnPretty': ICON.list(16),
        'masterBtnTable': ICON.table(16),
        'masterRespCopy': ICON.copy(16),
        'masterRespCopyFull': ICON.copyCurl(16),
        'masterRespCsv': ICON.fileCsv(16),
        'masterRespJson': ICON.fileJson(16),
        'runnerOvrBtn': ICON.ovr(20),
        'runnerLinkBtn': ICON.link(20)
    };

    Object.entries(iconMap).forEach(([id, svg]) => {
        const el = UI(id);
        if (el) el.innerHTML = svg;
    });
    d.querySelectorAll('.modal-header .icon-btn[title="Close"]').forEach(btn => {
        btn.innerHTML = ICON.close(24);
    });
};
