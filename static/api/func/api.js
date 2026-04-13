/**
 * @description Checks if a given command requires an authorization token.
 */
const testNeedsToken = c => {
  if (c.h && c.h.some(x => x.k.toLowerCase() === 'authorization')) return 1;
  if (c.p.startsWith('/my/') || c.p.startsWith('/admin/')) return 1;
  return 0;
};

/**
 * @description Executes the currently selected API.
 * @param {boolean} [isShowResponse=true]
 * @param {boolean} [isAllowDownload=true]
 */
const executeCurrentApi = async (isShowResponse, isAllowDownload) => {
  isShowResponse = isShowResponse ?? 1; isAllowDownload = isAllowDownload ?? 1;
  if (!curr) return alert('Select API');
  const btn = UI('subBtn'), t0 = performance.now();
  btn.disabled = true; btn.innerHTML = '<span class="spinner"></span>Sending...'; btn.classList.add('loading');
  const params = ParamManager.getCurrent();
  let urlPath = curr.p;
  params.u.forEach(x => { if (x.k) urlPath = urlPath.replace(`{${x.k}}`, encodeURIComponent(x.v || 'null')); });
  let url = window.location.origin + urlPath;
  const qs = params.q.filter(x => x.k).map(x => `${encodeURIComponent(x.k)}=${encodeURIComponent(x.v || 'null')}`).join('&');
  if (qs) url += '?' + qs;
  const h = {};
  params.h.forEach(x => {
    if (x.k) {
      const val = x.v || 'null';
      const finalVal = x.k.toLowerCase() === 'authorization' ? (Store.token || val) : val;
      h[x.k] = x.k.toLowerCase() === 'authorization' ? (finalVal.startsWith('Bearer ') ? finalVal : `Bearer ${finalVal}`) : finalVal;
    }
  });
  const opts = { method: curr.m, headers: h };
  if (Store.token && !Object.keys(h).some(k => k.toLowerCase() === 'authorization')) {
    h['Authorization'] = `Bearer ${Store.token}`;
  }
  if (params.f.length) {
    const fd = new FormData();
    params.f.forEach(x => { 
      if (x.files) x.files.forEach(file => fd.append(x.k, file)); 
      else if (x.k) fd.append(x.k, x.v || 'null');
    });
    opts.body = fd;
  } else if (params.j.length || curr._hj) {
    const body = {};
    try {
      params.j.forEach(x => { if (x.k) body[x.k] = ParamManager.cast(x.v, x.t, x.k); });
      opts.body = JSON.stringify(body);
      h['Content-Type'] = 'application/json';
    } catch (err) {
      alert(err.message);
      btn.disabled = false; btn.classList.remove('loading'); btn.textContent = 'Submit';
      return;
    }
  }
  try {
    const r = await fetch(url, opts),
      ms = Math.round(performance.now() - t0);

    const cd = r.headers.get('Content-Disposition');
    if (cd && cd.includes('attachment')) {
      const blob = await r.blob();
      let filename = 'download';
      const m = cd.match(/filename="?([^"]+)"?/);
      if (m) filename = m[1];
      const fileResponse = { status: 1, message: `File downloaded: ${filename}` };
      if (isAllowDownload) downloadBlob(blob, filename);
      if (isShowResponse) showResponse(fileResponse, r.status, ms);
      if (activeMasterRunIndex !== null) {
        Store.setResponse(activeMasterRunIndex, { status: r.status, time: ms, data: fileResponse, updated_at: Date.now() });
        renderApiInfoTable(UI('apiInfoSearch').value);
      }
      return { status: r.status, time: ms, data: fileResponse };
    } else {
      const text = await r.text();
      let json;
      try { json = JSON.parse(text) } catch { json = { status: r.status, message: text || 'Raw' } }
      if (r.ok && json && curr.p.includes('/auth/login')) {
        if (json.status === 1 && json.message?.token?.token) {
          Store.token = json.message.token.token;
          toast(`Session Token Saved`);
          updateLoginIndicator();
        }
      }
      if (isShowResponse) showResponse(json, r.status, ms);
      if (activeMasterRunIndex !== null) {
        Store.setResponse(activeMasterRunIndex, { status: r.status, time: ms, data: json, updated_at: Date.now() });
        renderApiInfoTable(UI('apiInfoSearch').value);
      }
      return { status: r.status, time: ms, data: json };
    }
  } catch (err) {
    const failMs = Math.round(performance.now() - t0);
    const failResponse = { status: 0, message: err.message };
    if (isShowResponse) showResponse(failResponse, 0, failMs);
    if (activeMasterRunIndex !== null) {
      Store.setResponse(activeMasterRunIndex, { status: 0, time: failMs, data: failResponse, updated_at: Date.now() });
      renderApiInfoTable(UI('apiInfoSearch').value);
    }
    return { status: 0, time: failMs, data: failResponse };
  } finally {
    btn.disabled = false;
    btn.classList.remove('loading');
    btn.textContent = 'Submit';
  }
};

/**
 * @description Executes an API by its global index without touching the Runner UI.
 */
const runMasterApiByIndex = async (index) => {
  const c = COMMANDS[index];
  if (!c) return;
  const t0 = performance.now();
  const params = {
    h: c.h.map(x => ({...x})),
    q: c.q.map(x => ({...x})),
    u: c.u.map(x => ({...x})),
    f: c.f.map(x => ({...x})),
    j: c.j.map(x => ({...x}))
  };
  
  let urlPath = c.p;
  params.u.forEach(x => { if (x.k) urlPath = urlPath.replace(`{${x.k}}`, encodeURIComponent(x.v || 'null')); });
  let url = window.location.origin + urlPath;
  const qs = params.q.filter(x => x.k).map(x => `${encodeURIComponent(x.k)}=${encodeURIComponent(x.v || 'null')}`).join('&');
  if (qs) url += '?' + qs;

  const h = {};
  params.h.forEach(x => {
    if (x.k) {
      const val = x.v || 'null';
      const finalVal = x.k.toLowerCase() === 'authorization' ? (Store.token || val) : val;
      h[x.k] = x.k.toLowerCase() === 'authorization' ? (finalVal.startsWith('Bearer ') ? finalVal : `Bearer ${finalVal}`) : finalVal;
    }
  });

  const opts = { method: c.m, headers: h };
  if (Store.token && !Object.keys(h).some(k => k.toLowerCase() === 'authorization')) {
    h['Authorization'] = `Bearer ${Store.token}`;
  }
  if (params.f.length) {
    const fd = new FormData();
    params.f.forEach(x => { if (x.k) fd.append(x.k, x.v || 'null'); });
    opts.body = fd;
  } else if (params.j.length || c._hj) {
    const body = {};
    try {
      params.j.forEach(x => { if (x.k) body[x.k] = ParamManager.cast(x.v, x.t, x.k); });
      opts.body = JSON.stringify(body);
      h['Content-Type'] = 'application/json';
    } catch(e) {
      const ms = Math.round(performance.now() - t0);
      Store.setResponse(index, { status: 0, time: ms, data: { status: 0, message: e.message }, updated_at: Date.now() });
      renderApiInfoTable(UI('apiInfoSearch').value);
      return;
    }
  }

  try {
    const r = await fetch(url, opts);
    const ms = Math.round(performance.now() - t0);
    const text = await r.text();
    let json;
    try { json = JSON.parse(text) } catch { json = { status: r.status, message: text || 'Raw' } }
    
    Store.setResponse(index, { status: r.status, time: ms, data: json, updated_at: Date.now() });
    renderApiInfoTable(UI('apiInfoSearch').value);
  } catch (err) {
    const ms = Math.round(performance.now() - t0);
    Store.setResponse(index, { status: 0, time: ms, data: { status: 0, message: err.message }, updated_at: Date.now() });
    renderApiInfoTable(UI('apiInfoSearch').value);
  }
};

let testRunning = 0;
/**
 * @description Runs all visible APIs in the master list sequentially.
 */
const testRunApis = async () => {
  if (testRunning) return toast('Test already running');
  const visibleIndexes = getVisibleMasterIndexes();
  if (!visibleIndexes.length) return toast('No APIs available in the current filters');
  testRunning = 1;
  const runBtn = UI('testRunBtn');
  UI('testProgress').style.display = 'flex';
  UI('testProgressFill').style.width = '0%';
  const total = visibleIndexes.length;
  for (let offset = 0; offset < total; offset++) {
    const i = visibleIndexes[offset];
    const c = COMMANDS[i];
    const pct = Math.round(((offset + 1) / total) * 100);
    UI('testProgressText').textContent = `${offset + 1}/${total}`;
    UI('testProgressFill').style.width = pct + '%';
    if (c.m === 'WS') {
      Store.setResponse(i, { status: 0, time: 0, data: { status: 0, message: 'Bulk runner supports HTTP APIs only' }, updated_at: Date.now() });
      renderApiInfoTable(UI('apiInfoSearch').value);
      continue;
    }
    await runMasterApiByIndex(i, 0, 0);
  }
  testRunning = 0;
  UI('testProgress').style.display = 'none';
  updateTestSummary();
  runBtn.disabled = false;
  runBtn.style.opacity = '1';
  runBtn.innerHTML = ICON.play(18);
};

/**
 * @description Gets basic search-matched indexes from the master list.
 */
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

/**
 * @description Checks if a response state indicates success.
 */
const isMasterPassResponse = responseState => !!responseState && responseState.status >= 200 && responseState.status < 300;

/**
 * @description Gets visible indexes based on active filters (passed/failed/etc).
 */
const getVisibleMasterIndexes = () => getMasterBaseIndexes().filter(i => {
  const responseState = Store.getResponse(i);
  if (activeMasterResultFilter === 'pass') return isMasterPassResponse(responseState);
  if (activeMasterResultFilter === 'fail') return responseState ? !isMasterPassResponse(responseState) : 0;
  return 1;
});

/**
 * @description Calculates summary statistics for the visible master list.
 */
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

/**
 * @description Alias to ResponseView.render for external callers.
 */
const showResponse = (json, httpCode, ms) => ResponseView.render('runner', json, httpCode, ms);
