const updateAppLoader = (pct, msg) => {
    const fill = UI('appLoaderFill'), text = UI('appLoaderPct'), info = UI('appLoaderMsg');
    if (fill) fill.style.width = pct + '%';
    if (text) text.textContent = pct + '%';
    if (info && msg) info.textContent = msg;
    if (pct >= 100) setTimeout(() => UI('appLoader')?.classList.add('hidden'), 400);
};
const renderApiInfoTags = () => {
    const counts = {};
    COMMANDS.forEach(c => {
        getPathTags(c.p).forEach(t => {
            counts[t] = (counts[t] || 0) + 1;
        });
    });
    const tags = Object.entries(counts).sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]));
    const renderTag = ([t, count]) => {
        const active = activeApiTag === t ? 'active' : '';
        return `<span class="tag-filter ${active}" data-tag="${t}">${t}<span class="tag-filter-count">(${count})</span></span>`;
    };
    UI('pathFilterTotal').textContent = `(${tags.length})`;
    UI('apiInfoTags').innerHTML = `<div class="tag-group">${tags.map(renderTag).join('')}</div>`;
};
const applyMasterTableLayout = () => {
  const root = d.documentElement;
  const pathLengths = COMMANDS.map(c => c.p.length);
  const maxPathLength = pathLengths.length ? Math.max(...pathLengths) : 32;
  const pathWidth = Math.min(340, Math.max(220, maxPathLength * 6 + 18));
  const fixedWidth = 32 + 52 + 74 + 66 + (56 * 2) + 36;
  const shellWidth = Math.min(1180, Math.max(920, pathWidth + fixedWidth + 48));
  root.style.setProperty('--master-path-col', `${pathWidth}px`);
  root.style.setProperty('--master-shell-width', `${shellWidth}px`);
  UI('apiInfoTbl').closest('.master-table-wrap').style.opacity = '1';
};
const toast = msg => {
  const el = d.createElement('div');
  el.className = 'toast';
  el.textContent = msg;
  d.body.appendChild(el);
  setTimeout(() => el.remove(), 2500);
};

const showModal = id => {
  const el = UI(id);
  if (!el) return;
  const modalList = Array.from(d.querySelectorAll('.modal'));
  const visibleList = modalList.filter(item => item.style.display === 'block' && item.id !== id);
  const topZIndex = visibleList.reduce((max, item) => {
    const itemZIndex = parseInt(item.style.zIndex || '2000', 10);
    if (Number.isNaN(itemZIndex)) return max;
    if (itemZIndex > max) return itemZIndex;
    return max;
  }, 1999);
  el.style.zIndex = String(topZIndex + 10);
  el.style.display = 'block';
};
const hideModal = id => {
  const el = UI(id);
  if (!el) return;
  el.style.display = 'none';
  el.style.zIndex = '';
};

const copyWithFeedback = (btn, text, size = 16, msg) => {
  navigator.clipboard.writeText(text);
  if (msg) toast(msg);
  if (btn.dataset.copied === '1') return;
  const originalHtml = btn.innerHTML;
  btn.dataset.copied = '1';
  btn.innerHTML = ICON.check(size);
  setTimeout(() => {
    btn.innerHTML = originalHtml;
    delete btn.dataset.copied;
  }, 1500);
};
const ResponseView = {
  /** @type {Record<string, {data: any, status: any, time: any, index: any, view: string}>} */
  states: {
    runner: { data: null, status: null, time: null, index: null, view: 'raw' },
    master: { data: null, status: null, time: null, index: null, view: 'raw' }
  },

  /**
   * @description Renders a response into the specified view container.
   * @param {'runner'|'master'} scope - The view scope.
   * @param {any} data - Response data.
   * @param {number|string} status - HTTP status code.
   * @param {number} [time] - Execution time in ms.
   * @param {number} [index] - Global command index (for master runner).
   */
  render(scope, data, status, time, index = null) {
    const s = this.states[scope];
    s.data = data; s.status = status; s.time = time; s.index = index;
    const isMaster = scope === 'master';
    const prefix = isMaster ? 'master' : '';
    
    // Status badges
    const codeColor = status >= 200 && status < 300 ? 'var(--primary)' : (status >= 400 ? 'var(--delete)' : 'var(--accent)');
    const codeHtml = (status != null ? `<span style="color:${codeColor};font-weight:600">${status}</span>` : '') + 
                     (time != null ? ` <span style="color:var(--muted);font-size:11px;margin-left:8px">${time}ms</span>` : '');
    UI(isMaster ? 'masterRespCode' : 'rCode').innerHTML = codeHtml;
    
    UI(isMaster ? 'masterRespBox' : 'rBox').classList.add('show');
    this.switchTo(scope, s.view);
  },

  /**
   * @description Switches the active view type (Pretty/Raw/Table).
   * @param {'runner'|'master'} scope - The view scope.
   * @param {'pretty'|'raw'|'table'} type - View type.
   */
  switchTo(scope, type) {
    const s = this.states[scope];
    s.view = type;
    const isMaster = scope === 'master';
    const p = isMaster ? 'master' : '';
    const btnP = isMaster ? 'masterBtn' : 'btn';
    const viewP = isMaster ? 'masterView' : 'view';
    const data = s.data;
    
    // Update button and view visibility
    ['Raw', 'Pretty', 'Table'].forEach(t => {
      const btn = UI(`${btnP}${t}`);
      if (btn) btn.classList.toggle('active', t.toLowerCase() === type);
      const v = UI(`${viewP}${t}`);
      if (v) v.classList.toggle('active', t.toLowerCase() === type);
    });

    if (type === 'raw') {
      UI(isMaster ? 'masterRawPre' : 'rawPre').innerHTML = highlight(JSON.stringify(data, null, 2));
    } else if (type === 'pretty') {
      UI(isMaster ? 'masterViewPretty' : 'viewPretty').innerHTML = renderTree(data);
    } else if (type === 'table') {
      const tableData = data?.data || data?.message || data;
      const tableHtml = fmtGrid(tableData);
      UI(isMaster ? 'masterViewTable' : 'viewTable').innerHTML = tableHtml || `<div style="padding:20px;text-align:center;color:var(--muted)">Table view not available</div>`;
    }
  },

  /**
   * @description Copies the current response data to clipboard.
   * @param {'runner'|'master'} scope - The view scope.
   * @param {boolean} [isFull=false] - Whether to include the generated cURL command.
   */
  copy(scope, isFull = false) {
    const s = this.states[scope];
    if (!s.data) return toast('No data');
    const raw = JSON.stringify(s.data, null, 2);
    const isMaster = scope === 'master';
    if (!isFull) return copyWithFeedback(UI(isMaster ? 'masterRespCopy' : 'rCopy'), raw, 16, 'Copied');
    const curl = generateCurl(isMaster ? s.index : COMMANDS.indexOf(curr));
    copyWithFeedback(UI(isMaster ? 'masterRespCopyFull' : 'rCopyFull'), `CURL:\n${curl}\n\nRESPONSE:\n${raw}`, 16, 'Curl & Response copied');
  }
};

const openJsonResponseModal = (title, data) => {
  const jsonStr = JSON.stringify(data, null, 2);
  testResponseRaw = jsonStr;
  UI('testResponseTitle').textContent = title;
  UI('testResponseContent').innerHTML = `<pre class="resp-pre" style="padding:20px;margin:0">${highlight(compactArrays(jsonStr))}</pre>`;
  UI('testResponseCopy').onclick = () => copyWithFeedback(UI('testResponseCopy'), jsonStr, 16, 'Response copied');
  UI('testResponseJson').onclick = () => downloadJson('response.json', jsonStr);
  UI('testResponseCopy').innerHTML = ICON.copy(20);
  UI('testResponseJson').innerHTML = ICON.fileJson(20);
  showModal('testResponseModal');
};
const updateTestSummary = () => {
  const summaryEl = UI('testSummary');
  if (!summaryEl) return;
  const stats = getMasterSummaryStats();
  const isDisabled = stats.hasResults ? '' : 'disabled';
  const valuePassed = stats.hasResults ? stats.passed : '-';
  const valueFailed = stats.hasResults ? stats.failed : '-';
  const valueAvg = stats.hasResults ? `${stats.avg}ms` : '-';
  UI('testSummary').innerHTML = `
    <div class="test-summary-stats">
        <span class="clickable ${activeMasterResultFilter === 'all' ? 'active' : ''}" data-type="all">Total: <strong style="color:#e6eef3">${stats.total}</strong></span>
        <span class="clickable ${activeMasterResultFilter === 'pass' && stats.hasResults ? 'active' : ''} ${isDisabled}" data-type="pass">Passed: <strong style="color:var(--primary)">${valuePassed}</strong></span>
        <span class="clickable ${activeMasterResultFilter === 'fail' && stats.hasResults ? 'active' : ''} ${isDisabled}" data-type="fail">Failed: <strong style="color:var(--delete)">${valueFailed}</strong></span>
    </div>
    <div class="test-summary-actions">
        <div class="test-summary-avg-slot">
            <span class="test-summary-avg-pill">Avg: <strong style="color:var(--primary)">${valueAvg}</strong></span>
        </div>
        <div class="test-summary-export-slot">
            <button type="button" class="icon-btn" id="testAllExportCsv" title="Export Visible Results CSV" style="padding:8px" ${stats.hasResults ? '' : 'disabled'}>${ICON.download(18)}</button>
        </div>
        <div class="test-summary-run-slot">
            <button type="button" class="icon-btn save" id="testRunBtn" title="Run Visible APIs" style="padding:8px">${ICON.play(18)}</button>
        </div>
    </div>
  `;
  const runBtn = d.getElementById('testRunBtn');
  const exportBtn = d.getElementById('testAllExportCsv');
  if (exportBtn) {
    exportBtn.style.opacity = stats.hasResults ? '1' : '0.35';
    exportBtn.style.cursor = stats.hasResults ? 'pointer' : 'default';
    exportBtn.disabled = !stats.hasResults;
  }
  if (testRunning && runBtn) {
    runBtn.disabled = true;
    runBtn.style.opacity = '0.5';
    runBtn.innerHTML = ICON.tester(18);
  }
};
const updateLoginIndicator = () => {
  const ind = UI('loginIndicator');
  if (!ind) return;
  const tUser = Store.token;
  if (tUser) {
    ind.innerHTML = `<span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:currentColor"></span>Logout`;
    ind.style.background = 'rgba(56,161,105,0.1)'; ind.style.color = 'var(--primary)';
  } else {
    ind.innerHTML = `<span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:currentColor"></span>Login`;
  }
};
const bindClear = r => {
  const inp = r.querySelector('.row-val'),
    btn = r.querySelector('.clear-input-btn');
  if (!btn || !inp) return;
  const upd = () => { btn.style.display = inp.value ? 'block' : 'none' };
  upd();
  inp.oninput = upd;
  inp.onchange = upd;
  btn.onclick = e => { e.stopPropagation(); inp.value = ''; upd(); inp.focus() };
};

const valHtml = (ct, v, t, e) => {
  const TYPES = ['str', 'int', 'float', 'bool', 'list', 'object', 'null'];
  const wrap = inner => `<div class="input-wrapper">${inner}<button type="button" class="clear-input-btn">×</button></div>`;
  let inputHtml;
  if (e && Array.isArray(e) && e.length > 0) {
    inputHtml = `<select class="row-val"><option value="">-- select --</option>${e.map(opt => `<option value="${he(opt)}" ${String(v) === String(opt) ? 'selected' : ''}>${he(opt)}</option>`).join('')}</select>`;
  } else if (t === 'file') {
    inputHtml = `<input type="file" class="row-val" multiple>`;
  } else {
    inputHtml = `<input type="text" class="row-val" value="${he(v)}">`;
  }
  if (ct === UI('jCont'))
    return wrap(inputHtml) +
      `<select class="json-type-selector">${TYPES.map(x => `<option value="${x}" ${t === x ? 'selected' : ''}>${x}</option>`).join('')}</select>`;
  return wrap(inputHtml);
};

const showInfoModal = (k, r_pat, desc) => {
  UI('paramInfoTitle').innerHTML = `Configuration Detail: <span style="color:var(--accent);font-weight:700;background:rgba(255,255,255,0.05);padding:2px 10px;border-radius:6px;margin-left:8px;border:1px solid rgba(255,255,255,0.1)">${he(k)}</span>`;
  UI('paramInfoCopyBtn').innerHTML = ICON.copy(20);
  
  let html = '<div style="background:rgba(255,255,255,0.03);padding:24px;border-radius:12px;border:1px solid rgba(255,255,255,0.08);display:flex;flex-direction:column;gap:12px;width:fit-content;min-width:500px;max-width:900px">';
  
  if (desc || r_pat) {
    const parts = desc ? desc.split('. ').filter(p => p.trim()) : [];
    const finalItems = [];

    if (r_pat) {
      // First Bullet: Regex [Description]
      let bullet1 = `<code style="background:rgba(0,0,0,0.2);padding:2px 6px;border-radius:4px;font-size:12px;color:var(--accent);font-family:'SF Mono',Menlo,monospace">${he(r_pat)}</code>`;
      if (parts.length > 0) {
        bullet1 += ` <span style="color:var(--muted);font-style:italic;margin-left:6px">[${he(parts[0])}]</span>`;
      }
      finalItems.push(bullet1);
      // Remaining bullets
      if (parts.length > 1) finalItems.push(...parts.slice(1));
    } else {
      // No Regex, just show all description parts
      if (parts.length > 0) finalItems.push(...parts);
    }

    html += `
      <ul style="margin:0;padding:0;list-style:none;display:flex;flex-direction:column;gap:12px">
        ${finalItems.map(item => `
          <li style="display:flex;gap:12px;line-height:1.6;color:#e6eef3;font-size:13px;white-space:nowrap">
            <span style="color:var(--primary);flex-shrink:0;font-size:18px;line-height:12px;margin-top:4px">•</span>
            <span>${item}</span>
          </li>`).join('')}
      </ul>`;
  } else {
    html += '<div style="color:var(--muted);font-style:italic">No additional configuration details available.</div>';
  }
  
  html += '</div>';
  
  UI('paramInfoBody').innerHTML = html;
  
  // Dynamic width for the modal content
  const modalCont = UI('paramInfoModal').querySelector('.modal-content');
  modalCont.style.width = 'fit-content';
  modalCont.style.minWidth = '500px';
  modalCont.style.maxWidth = '1000px';

  showModal('paramInfoModal');
};

const mkRow = (ct, k = '', v = '', t = 'string', e = null, r_pat = null, isFixed = false, isReq = false, desc = null) => {
  const r = d.createElement('div');
  r.className = 'input-row';
  const rmBtn = `<button type="button" class="remove-btn"${isReq ? ' disabled' : ''}>${ICON.trash(16)}</button>`;
  const infoIconHtml = (r_pat || desc) ? `<span class="info-icon-btn" data-key="${he(k)}" data-regex="${he(r_pat || '')}" data-desc="${he(desc || '')}">${ICON.info(13)}</span>` : '';
  const keyHtml = isReq 
    ? `<div style="flex:0 0 180px;padding:11px 14px;font-size:14px;border-radius:8px;border:1px solid rgba(255,255,255,.04);background:rgba(255,255,255,.02);color:var(--muted);cursor:default;box-sizing:border-box;white-space:nowrap" ><span style="color:var(--delete);margin-right:4px;font-weight:bold">*</span>${he(k)}${infoIconHtml ? `<span style="margin-left:6px">${infoIconHtml}</span>` : ''}</div><input type="hidden" class="row-key" value="${he(k)}">` 
    : `<div style="flex:0 0 180px;position:relative;display:flex;align-items:center"><input type="text" class="row-key" value="${he(k)}" ${isFixed ? 'readonly tabindex="-1"' : ''} >${infoIconHtml ? `<div style="position:absolute;right:8px;top:50%;transform:translateY(-50%);display:flex;align-items:center;z-index:11">${infoIconHtml}</div>` : ''}</div>`;
  r.innerHTML = `${keyHtml}${valHtml(ct, v, t, e)}${rmBtn}`;
  if (!isReq) r.querySelector('.remove-btn').onclick = () => r.remove();
  bindClear(r);
  ct.appendChild(r);
};

/* ── Sections ── */
const SECTIONS = [['addH', 'hSec', 'hCont'], ['addQ', 'qSec', 'qCont'], ['addF', 'fSec', 'fCont'], ['addJ', 'jSec', 'jCont'], ['addU', 'uSec', 'uCont']];
const syncParams = () => {
  if (!curr) return;
  const p = ParamManager.getCurrent();
  curr.h = p.h; curr.q = p.q; curr.u = p.u; curr.f = p.f; curr.j = p.j;
};



const load = i => {
  curr = i === null ? null : COMMANDS[i];
  SECTIONS.forEach(([, sec, cont]) => { UI(cont).innerHTML = ''; UI(sec).classList.remove('active'); });
  UI('rBox').classList.remove('show');
  UI('apiIn').innerHTML = curr ? renderRunnerEndpoint(curr) : '';
  if (!curr) return;
  populate('hCont', 'hSec', curr.h);
  populate('uCont', 'uSec', curr.u);
  populate('qCont', 'qSec', curr.q);
  populate('fCont', 'fSec', (curr._hf ? curr.f : []));
  populate('jCont', 'jSec', (curr._hj ? curr.j : []), true);
  if (curr._hf && !UI('fCont').children.length) { UI('fSec').classList.add('active'); mkRow(UI('fCont')); }
  if (curr._hj && !UI('jCont').children.length) { UI('jSec').classList.add('active'); mkRow(UI('jCont')); }
  const hasOvr = !!PATH_OVERRIDES[curr.p];
  const btnOvr = UI('runnerOvrBtn');
  if (btnOvr) {
      btnOvr.disabled = !hasOvr;
      btnOvr.style.opacity = hasOvr ? '1' : '0.4';
      btnOvr.style.cursor = hasOvr ? 'pointer' : 'not-allowed';
  }
};

const populate = (cont, sec, spec, isJson = false) => {
  if (spec && spec.length) UI(sec).classList.add('active');
  (spec || []).forEach(x => {
    let val = x.v;
    if (x.k.toLowerCase() === 'authorization') {
      const lsVal = Store.token;
      if (lsVal) val = lsVal.startsWith('Bearer ') ? lsVal : `Bearer ${lsVal}`;
      else if (val && !val.startsWith('Bearer ')) val = `Bearer ${val}`;
    }
    mkRow(UI(cont), x.k, val, x.t || 'string', x.e, x.r || null, !!spec.find(s => s.k === x.k), !!spec.find(s => s.k === x.k && s.req), x.d || null);
  });
};
const renderApiInfoTable = (searchQuery = '') => {
  const filteredIndexes = getVisibleMasterIndexes();
  UI('apiInfoTbl').innerHTML =
    `<thead><tr>
        <th class="col-id">#</th>
        <th class="col-method">Method</th>
        <th class="col-path">Path</th>
        <th class="col-param">Param</th>
        <th class="col-time">Status</th>
        <th class="col-time">Time</th>
        <th class="col-run">Run</th>
    </tr></thead>` +

    `<tbody>${filteredIndexes.map(globalIndex => {
      const c = COMMANDS[globalIndex];
      const isWs = c.m === 'WS';
      const responseState = Store.getResponse(globalIndex);
      const isOvr = !!PATH_OVERRIDES[c.p];
      const hasRes = !!responseState;
      
      return `
        <tr data-i="${globalIndex}">
          <td class="col-id master-static-cell">${globalIndex + 1}</td>
          <td class="col-method master-static-cell"><span class="method-badge ${c.m.toLowerCase()}">${c.m}</span></td>
          <td class="col-path master-static-cell" title="${c.p}">${c.p}</td>
          <td class="col-param master-static-cell">${isWs ? '-' : renderParamBadges(c)}</td>
          <td class="col-time master-status-cell ${hasRes ? 'clickable' : ''}" title="${hasRes ? `HTTP ${responseState.status}` : 'No response yet'}">${isWs ? '-' : renderStatusBadge(responseState?.status)}</td>
          <td class="col-time master-time-cell">${isWs ? '-' : (responseState ? `${responseState.time}ms` : '-')}</td>
          <td class="col-run run-btn clickable" title="Run">${ICON.play(16)}</td>
        </tr>`;

    }).join('')}</tbody>`;
  updateTestSummary();
};
const renderStorage = () => {
  const rowList = getStorageRows();
  if (!rowList.length) {
    UI('storageContent').innerHTML = '<div style="padding:40px;text-align:center;color:var(--muted)">No data stored in localStorage</div>';
    return;
  }
  const keyLengthMax = rowList.reduce((max, row) => {
    if (row.key.length > max) return row.key.length;
    return max;
  }, 0);
  const keyWidthCh = Math.min(Math.max(keyLengthMax + 2, 18), 30);
  const sizeWidthCh = 8;
  const rows = rowList.map((row, idx) => {
    const valStr = typeof row.value === 'object' ? JSON.stringify(row.value, null, 2) : String(row.value);
    const size = new Blob([valStr]).size;
    const sizeStr = size > 1024 ? (size / 1024).toFixed(1) + ' KB' : size + ' B';
    return `
      <tr>
        <td class="col-id" style="text-align:left!important">${idx + 1}</td>
        <td class="storage-key-cell" title="${row.key}">${row.key}</td>
        <td class="storage-size-cell">${sizeStr}</td>
        <td>
          <div class="storage-action-wrap">
            <button class="icon-btn storage-view-btn" data-key="${row.key}" data-scope="${row.scope}" title="View JSON">${ICON.eye(14)}</button>
            <button class="icon-btn storage-copy-btn" data-key="${row.key}" data-scope="${row.scope}" title="Copy Value">${ICON.copy(14)}</button>
            <button class="icon-btn delete storage-del-btn" data-key="${row.key}" data-scope="${row.scope}" title="${row.removable ? 'Delete Key' : 'Delete Root Key'}">${ICON.trash(14)}</button>
          </div>
        </td>
      </tr>`;
  }).join('');
  UI('storageContent').innerHTML = `
    <table class="resp-tbl" style="table-layout:fixed;width:100%">
        <colgroup>
            <col style="width:32px">
            <col style="width:${keyWidthCh}ch">
            <col style="width:${sizeWidthCh}ch">
            <col style="width:120px">
        </colgroup>
        <thead>
            <tr>
                <th class="col-id" style="text-align:left!important">#</th>
                <th style="text-align:left">Key</th>
                <th style="text-align:right">Size</th>
                <th style="text-align:right">Action</th>
            </tr>
        </thead>
        <tbody>${rows}</tbody>
    </table>`;
};
const highlight = s => s
  .replace(/"([^"]+)"\s*:/g, '<span class="jk">"$1"</span>:')
  .replace(/:"([^"]*)"/g, ':<span class="js">"$1"</span>')
  .replace(/:\s*([\d.]+)/g, ': <span class="jn">$1</span>')
  .replace(/:\s*(true|false)/g, ': <span class="jb">$1</span>')
  .replace(/:\s*(null)/g, ': <span class="jl">$1</span>');

const highlightCurl = s => {
  const lines = s.split(' \\\n');
  return lines.map((l, i) => {
    let line = l.trim();
    if (i === 0) {
      line = line.replace(/^curl/, '<span class="ck">curl</span>')
                 .replace(/-X\s+(\w+)/, '<span class="cf">-X</span> <span class="cm">$1</span>')
                 .replace(/"(https?:\/\/[^"]+)"/, '<span class="cs">"$1"</span>');
    } else {
      line = line.replace(/^(-[HdF])\s+(.*)$/, (m, p1, p2) => {
        let val = p2;
        if (p1 === '-d' && val.startsWith("'") && val.endsWith("'")) {
          const inner = val.slice(1, -1);
          try { 
            const parsed = JSON.parse(inner);
            val = `'${highlight(JSON.stringify(parsed, null, 2))}'`;
          } catch(e) {}
        }
        return `<span class="cf">${p1}</span> <span class="cs">${val}</span>`;
      });
    }
    return (i > 0 ? '  ' : '') + line;
  }).join(' \\\n');
};
const compactArrays = s => s.replace(
  /\[\n((\s+("(?:[^"\\]|\\.)*"|[\d.eE+-]+|true|false|null),?\n)+\s*)\]/g,
  m => m.replace(/\n\s*/g, ' ').replace(/,\s*/g, ', ')
);
const showResponse = (json, httpCode, ms) => ResponseView.render('runner', json, httpCode, ms);

const openMasterResponse = (i) => {
    const res = Store.getResponse(i);
    if (!res) return;
    UI('masterRespIn').innerHTML = renderRunnerEndpoint(COMMANDS[i]);
    ResponseView.render('master', res.data, res.status, res.time, i);
    UI('masterRespCopy').onclick = () => ResponseView.copy('master');
    UI('masterRespCopyFull').onclick = () => ResponseView.copy('master', true);
    UI('masterRespJson').onclick = () => downloadJson('response.json', JSON.stringify(res.data, null, 2));
    showModal('masterResponseModal');
};
const renderTree = (val, key = null) => {
    if (val === null || typeof val !== 'object') {
        const valHtml = gvVal(val);
        if (key === null) return valHtml;
        return `<div class="tree-row"><span class="tree-spacer" style="width:12px;flex-shrink:0"></span><span class="tree-key">${key}</span><span class="tree-colon">:</span><span class="tree-val">${valHtml}</span></div>`;
    }
    
    const isArr = Array.isArray(val);
    const entries = Object.entries(val);
    const size = entries.length;
    if (size === 0) {
        const empty = isArr ? '[]' : '{}';
        if (key === null) return empty;
        return `<div class="tree-row"><span class="tree-spacer" style="width:12px;flex-shrink:0"></span><span class="tree-key">${key}</span><span class="tree-colon">:</span><span class="tree-val">${empty}</span></div>`;
    }
    
    const label = isArr ? `Array(${size})` : `Object(${size})`;
    const rows = entries.map(([k, v]) => renderTree(v, k)).join('');
    
    return `
        <div class="tree-node">
            <div class="tree-toggle">
                <span class="tree-arrow">▶</span>
                <span class="tree-key">${key || ''}</span>
                ${key ? '<span class="tree-colon">:</span>' : ''}
                <span class="tree-val" style="color:var(--muted);margin-left:4px">${isArr ? '[' : '{'}</span>
                <span class="tree-summary">${label}</span>
            </div>
            <div class="tree-content">
                ${rows}
                <div class="tree-row"><span class="tree-spacer" style="width:12px;flex-shrink:0"></span><span style="color:var(--muted)">${isArr ? ']' : '}'}</span></div>
            </div>
        </div>
    `;
};

const gvVal = v => {
    if (v === null) return '<span class="jl">null</span>';
    if (typeof v === 'string') return `<span class="js">"${v}"</span>`;
    if (typeof v === 'number') return `<span class="jn">${v}</span>`;
    if (typeof v === 'boolean') return `<span class="jb">${v}</span>`;
    return String(v);
};

const fmtGrid = v => {
  if (v == null || typeof v !== 'object') return null;
  const arr = Array.isArray(v) ? v : [v];
  if (!arr.length || typeof arr[0] !== 'object' || arr[0] === null) return null;
  const keys = [...new Set(arr.flatMap(Object.keys))];
  const colW = k => Math.max(90, k.length * 9 + 24);
  return `<div class="resp-tbl-wrap"><table class="resp-tbl">` +
    `<thead><tr>${keys.map(k => `<th style="width:${colW(k)}px;min-width:${colW(k)}px">${k}</th>`).join('')}</tr></thead>` +
    `<tbody>${arr.map(row => `<tr>${keys.map(k => {
        const cv = row[k];
        const val = cv == null ? '' : (typeof cv === 'object' ? JSON.stringify(cv) : String(cv));
        const enc = val.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
        return `<td title="${enc}" data-raw="${encodeURIComponent(val)}">${enc}</td>`;
    }).join('')}</tr>`).join('')}</tbody>` +
    `</table></div>`;
};
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
