/**
 * @description Updates the test summary stats in the master view.
 */
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

/**
 * @description Updates the login status indicator.
 */
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

/**
 * @description Binds clear button logic to an input row.
 */
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

/**
 * @description Generates HTML for an input value field.
 */
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

/**
 * @description Creates a new input row in the parameter container.
 */
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

/**
 * @description Syncs the current command parameters with the UI inputs.
 */
const syncParams = () => {
  if (!curr) return;
  const p = ParamManager.getCurrent();
  curr.h = p.h; curr.q = p.q; curr.u = p.u; curr.f = p.f; curr.j = p.j;
};

/**
 * @description Populates the UI container with parameter rows from a spec.
 */
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

/**
 * @description Loads an API command into the Runner UI.
 */
const load = i => {
  curr = i === null ? null : COMMANDS[i];
  SECTIONS.forEach(([, sec, cont]) => { UI(cont).innerHTML = ''; UI(sec).classList.remove('active'); });
  const rBox = UI('rBox');
  if (rBox) rBox.classList.remove('show');
  
  const pathHeader = UI('runnerPathHeader');
  if (pathHeader) pathHeader.innerHTML = curr ? renderRunnerEndpoint(curr) : '';
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
  setupIcons();
};

/**
 * @description Toggles the active master result table filter.
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

/**
 * @description Toggles the tag filter card visibility.
 */
const toggleTagCard = () => {
    UI('apiInfoTags').classList.toggle('collapsed');
    UI('tagToggleIcon').classList.toggle('collapsed');
};
