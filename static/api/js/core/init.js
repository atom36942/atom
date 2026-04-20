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

    // Sort COMMANDS based on path categories: index, auth, my, public, private, admin
    const categoryOrder = ['index', 'auth', 'my', 'public', 'private', 'admin'];
    COMMANDS.sort((a, b) => {
      const getCat = p => {
        const parts = p.split('/').filter(Boolean);
        return (parts.length <= 1) ? 'index' : parts[0];
      };
      const catA = getCat(a.p), catB = getCat(b.p);
      const idxA = categoryOrder.indexOf(catA), idxB = categoryOrder.indexOf(catB);
      
      if (idxA !== -1 && idxB !== -1) {
        if (idxA !== idxB) return idxA - idxB;
      } else if (idxA !== -1) return -1;
      else if (idxB !== -1) return 1;
      
      return a.p.localeCompare(b.p);
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
