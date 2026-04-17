/**
 * @description Centralized event listener setup for all UI interactions.
 */
const setupEventListeners = () => {
    // Top-level UI & Toolbars
    UI('tagCardHeader')?.addEventListener('click', toggleTagCard);

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
        'testResponseCloseBtn': 'testResponseModal',
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

    // Direct Bindings for Header Actions (Foolproof explicit onclick)
    setTimeout(() => {
        const bind = (id, fn) => { const el = d.getElementById(id); if (el) el.onclick = fn; };
        bind('infoToggleBtn', () => { showModal('infoModal'); setupIcons(); });
        bind('storageToggleBtn', () => { showModal('storageModal'); renderStorage(); setupIcons(); });
        bind('analyticsToggleBtn', () => { showModal('analyticsModal'); renderAnalytics(); setupIcons(); });
        bind('apiInfoCsv', exportCatalogCsv);
        bind('runnerCurlBtn', () => {
            if (activeMasterRunIndex !== null) openCurlViewModal(activeMasterRunIndex, 'all');
        });
        bind('runnerLinkBtn', () => {
            const btn = d.getElementById('runnerLinkBtn');
            if (curr && btn) {
                const link = `${window.location.origin}${window.location.pathname}?api=${curr.m}|${curr.p}`;
                copyWithFeedback(btn, link, 20, 'Link copied');
            }
        });
    }, 100);

    UI('apiForm')?.addEventListener('submit', e => {
        e.preventDefault();
        executeCurrentApi();
    });
    
    UI('paramInfoCopyBtn')?.addEventListener('click', () => {
        const txt = UI('paramInfoBody').innerText;
        if (txt) copyWithFeedback(UI('paramInfoCopyBtn'), txt, 20, 'Details copied');
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
        if (s.data) {
            const raw = s.data?.message;
            if (raw && typeof raw === 'object') {
                downloadCsv('api_response.csv', arrayToCsv(Array.isArray(raw) ? raw : [raw]));
            }
        }
    });
    UI('masterRespJson')?.addEventListener('click', () => {
        const s = ResponseView.states.master;
        if (s.data) downloadJson('api_response.json', s.data);
    });

    // Runner Response Actions
    UI('rCopy')?.addEventListener('click', () => {
        const s = ResponseView.states.runner;
        if (s.data) copyWithFeedback(UI('rCopy'), JSON.stringify(s.data, null, 2), 16, 'Response copied');
    });
    UI('rCopyFull')?.addEventListener('click', () => {
        const s = ResponseView.states.runner;
        if (s.data && curr) {
            const idx = COMMANDS.indexOf(curr);
            const full = `## CURL\n${generateCurl(idx)}\n\n## RESPONSE\n${JSON.stringify(s.data, null, 2)}`;
            copyWithFeedback(UI('rCopyFull'), full, 16, 'Curl & Response copied');
        }
    });
    UI('rCsv')?.addEventListener('click', () => {
        const s = ResponseView.states.runner;
        if (s.data) {
            const raw = s.data?.message;
            if (raw && typeof raw === 'object') {
                downloadCsv('api_response.csv', arrayToCsv(Array.isArray(raw) ? raw : [raw]));
            }
        }
    });
    UI('rJson')?.addEventListener('click', () => {
        const s = ResponseView.states.runner;
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
            openJsonResponseModal(`Storage Key: ${row.key}`, row.value);
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

        if (e.target.closest('.col-param.clickable')) {
            openParamsPreviewModal(idx);
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
        const btn = e.target.closest('.cell-expand-btn');
        if (!btn) return;
        const raw = decodeURIComponent(btn.dataset.raw);
        const pop = UI('cellPop');
        UI('cellPopTxt').textContent = raw;
        cellPopRaw = raw;
        const r = btn.getBoundingClientRect();
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
      
      // Global Workspace Shortcuts (if no input is focused)
      if (document.activeElement.tagName !== 'INPUT' && document.activeElement.tagName !== 'TEXTAREA') {
        if (e.key.toLowerCase() === 'd') { e.preventDefault(); showModal('infoModal'); setupIcons(); }
        if (e.key.toLowerCase() === 's') { e.preventDefault(); showModal('storageModal'); renderStorage(); setupIcons(); }
        if (e.key.toLowerCase() === 'a') { e.preventDefault(); showModal('analyticsModal'); renderAnalytics(); setupIcons(); }
        if (e.key.toLowerCase() === 'e') { e.preventDefault(); exportCatalogCsv(); }
      }
    });
};
