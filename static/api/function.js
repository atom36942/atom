const ParamManager = {
  /**
   * @description Extracts raw parameter rows from a DOM container.
   * @param {HTMLElement} container - The container element.
   * @param {boolean} [isJson=false] - Whether these are JSON body parameters.
   * @returns {any[]}
   */
  extract(container, isJson = false) {
    const rows = [];
    container.querySelectorAll('.input-row').forEach(r => {
      const k = r.querySelector('.row-key').value.trim();
      const v = r.querySelector('.row-val');
      const ts = r.querySelector('.json-type-selector');
      const t = isJson && ts ? ts.value : null;
      if (k || v.value) rows.push({ k, v: v.value, t, f: v.files?.length ? Array.from(v.files) : null });
    });
    return rows;
  },

  /**
   * @description Casts a string value to the specified type.
   * @param {string} val - Value to cast.
   * @param {string} type - Type (int, float, bool, list, object, null, str).
   * @param {string} key - Parameter key (for error reporting).
   * @returns {any}
   */
  cast(val, type, key) {
    if (val === '' || val === 'null' || val === null) return null;
    if (type === 'int' || type === 'float') {
      const num = Number(val);
      if (isNaN(num)) throw new Error(`Field '${key}' expects numeric value`);
      return num;
    }
    if (type === 'bool') {
      const l = String(val).toLowerCase();
      if (l !== 'true' && l !== 'false') throw new Error(`Field '${key}' expects boolean (true/false)`);
      return l === 'true';
    }
    if (type === 'null') return null;
    if (type === 'list' || type === 'object') {
      try {
        const p = (typeof val === 'string') ? JSON.parse(val) : val;
        if (type === 'list' && !Array.isArray(p)) throw new Error(`Field '${key}' expects list`);
        if (type === 'object' && (typeof p !== 'object' || p === null || Array.isArray(p))) throw new Error(`Field '${key}' expects object`);
        return p;
      } catch (e) { throw new Error(`Field '${key}' expects valid JSON`); }
    }
    return val;
  },

  /**
   * @description Extracts current parameter values from the API Runner UI.
   * @returns {{h: any[], q: any[], f: any[], u: any[], j: any[]}}
   */
  getCurrent() {
    return {
      h: this.extract(UI('hCont')),
      q: this.extract(UI('qCont')),
      u: this.extract(UI('uCont')),
      f: this.extract(UI('fCont')),
      j: this.extract(UI('jCont'), true)
    };
  }
};
const downloadBlob = (blob, filename) => {
  const url = window.URL.createObjectURL(blob);
  const a = d.createElement('a');
  a.style.display = 'none';
  a.href = url;
  a.download = filename;
  d.body.appendChild(a);
  a.click();
  window.URL.revokeObjectURL(url);
  a.remove();
};

const downloadCsv = (filename, csvStr) => downloadBlob(new Blob([csvStr], { type: 'text/csv' }), filename);
const downloadJson = (filename, jsonStr) => downloadBlob(new Blob([jsonStr], { type: 'application/json' }), filename);

const csvEscape = v => {
  const s = v == null ? '' : (typeof v === 'object' ? JSON.stringify(v) : String(v));
  return s.includes(',') || s.includes('"') || s.includes('\n')
    ? '"' + s.replace(/"/g, '""') + '"' : s;
};

const he = v => v == null ? '' : String(v).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');

const arrayToCsv = arr => {
  if(!arr.length) return '';
  const keys = [...new Set(arr.flatMap(Object.keys))];
  return [keys.join(','), ...arr.map(r => keys.map(k => csvEscape(r[k])).join(','))].join('\n');
};

const resolveSchema = (s) => {
  if (!s) return s;
  if (s.$ref) {
    const path = s.$ref.split('/');
    let curr = SPEC;
    for (let i = 1; i < path.length; i++) curr = curr[path[i]];
    return resolveSchema(curr);
  }
  if (s.allOf) {
    const merged = {};
    s.allOf.forEach(sub => {
      const resolved = resolveSchema(sub);
      if (resolved.properties) Object.assign(merged, resolved.properties);
    });
    return { ...s, properties: merged };
  }
  return s;
};

const mapSchemaType = schema => {
  const nextSchema = resolveSchema(schema) || {};
  let typeValue = nextSchema.type;
  if (!typeValue && nextSchema.anyOf) {
    typeValue = nextSchema.anyOf.map(item => resolveSchema(item)?.type).find(item => item && item !== 'null');
  }
  if (!typeValue && nextSchema.oneOf) {
    typeValue = nextSchema.oneOf.map(item => resolveSchema(item)?.type).find(item => item && item !== 'null');
  }
  if (typeValue === 'string') return 'str';
  if (typeValue === 'integer') return 'int';
  if (typeValue === 'number') return 'float';
  if (typeValue === 'boolean') return 'bool';
  if (typeValue === 'array') return 'list';
  if (typeValue === 'object') return 'object';
  return 'str';
};

const getSchemaEnum = schema => {
  const nextSchema = resolveSchema(schema) || {};
  if (Array.isArray(nextSchema.enum)) return nextSchema.enum;
  if (nextSchema.items && Array.isArray(nextSchema.items.enum)) return nextSchema.items.enum;
  return null;
};

const getRequestJsonRows = bodyContent => {
  const jsonSchema = resolveSchema(bodyContent?.['application/json']?.schema);
  if (!jsonSchema) return [];
  const requiredList = Array.isArray(jsonSchema.required) ? jsonSchema.required : [];
  return Object.entries(jsonSchema.properties || {}).map(([key, propSchema]) => {
    const nextSchema = resolveSchema(propSchema) || {};
    const defaultValue = nextSchema.default;
    return {
      k: key,
      v: defaultValue != null ? (typeof defaultValue === 'object' ? JSON.stringify(defaultValue) : String(defaultValue)) : '',
      t: mapSchemaType(nextSchema),
      e: getSchemaEnum(nextSchema),
      r: nextSchema.pattern || null,
      req: requiredList.includes(key)
    };
  });
};

const getRequestFormRows = bodyContent => {
  const formSchema = resolveSchema(bodyContent?.['multipart/form-data']?.schema);
  if (!formSchema) return [];
  const requiredList = Array.isArray(formSchema.required) ? formSchema.required : [];
  return Object.entries(formSchema.properties || {}).map(([key, propSchema]) => {
    const nextSchema = resolveSchema(propSchema) || {};
    const defaultValue = nextSchema.default;
    return {
      k: key,
      v: defaultValue != null ? String(defaultValue) : '',
      t: nextSchema.format === 'binary' || nextSchema.type === 'file' ? 'file' : 'string',
      e: getSchemaEnum(nextSchema),
      r: nextSchema.pattern || null,
      req: requiredList.includes(key)
    };
  });
};

const applyPathOverrides = command => {
  const overrideData = PATH_OVERRIDES[command.p];
  if (!overrideData) return;
  const updateRows = (rowList, isJson = 0) => rowList.forEach(row => {
    if (overrideData[row.k] === undefined) return;
    const value = overrideData[row.k];
    if (isJson) {
      if (value === null) row.t = 'null';
      if (Array.isArray(value)) row.t = 'list';
      if (typeof value === 'number') row.t = 'int';
      if (typeof value === 'boolean') row.t = 'bool';
      if (typeof value === 'object' && value !== null && !Array.isArray(value)) row.t = 'object';
    }
    row.v = typeof value === 'object' && value !== null ? JSON.stringify(value) : String(value);
  });
  updateRows(command.h);
  updateRows(command.q);
  updateRows(command.u);
  updateRows(command.f);
  updateRows(command.j, 1);
  const isBodyMethod = ['POST', 'PUT', 'PATCH', 'DELETE'].includes(command.m);
  Object.entries(overrideData).forEach(([key, value]) => {
    const isKnown = command.j.find(row => row.k === key) || command.q.find(row => row.k === key) || command.u.find(row => row.k === key) || command.h.find(row => row.k === key) || command.f.find(row => row.k === key);
    if (isKnown) return;
    let typeValue = 'str';
    if (value === null) typeValue = 'null';
    else if (Array.isArray(value)) typeValue = 'list';
    else if (typeof value === 'number') typeValue = Number.isInteger(value) ? 'int' : 'float';
    else if (typeof value === 'boolean') typeValue = 'bool';
    else if (typeof value === 'object' && value !== null) typeValue = 'object';
    const row = {
      k: key,
      v: typeof value === 'object' && value !== null ? JSON.stringify(value) : String(value),
      t: typeValue,
      req: false
    };
    if (isBodyMethod) {
      if (command._hf && !command._hj) command.f.push(row);
      else {
        command.j.push(row);
        command._hj = true;
      }
    } else {
      command.q.push(row);
    }
  });
};

const createCommandFromOperation = (path, method, op) => {
  const command = {
    p: path,
    m: method.toUpperCase(),
    h: [],
    q: [],
    f: [],
    u: [],
    j: [],
    tag: op.tags ? op.tags[0] : 'system'
  };
  (op.parameters || []).forEach(param => {
    const schema = resolveSchema(param.schema) || {};
    const item = {
      k: param.name,
      v: schema.default != null ? String(schema.default) : '',
      e: getSchemaEnum(schema) || param.enum || null,
      r: schema.pattern || null,
      req: !!param.required
    };
    if (param.in === 'header') command.h.push(item);
    if (param.in === 'query') command.q.push(item);
    if (param.in === 'path') command.u.push(item);
  });
  const bodyContent = op.requestBody?.content;
  command.j = getRequestJsonRows(bodyContent);
  command.f = getRequestFormRows(bodyContent);
  command._hj = command.j.length > 0 || !!bodyContent?.['application/json'];
  command._hf = command.f.length > 0 || !!bodyContent?.['multipart/form-data'];
  command._paramBadgeH = command.h.length > 0;
  command._paramBadgeP = command.u.length > 0;
  command._paramBadgeQ = command.q.length > 0;
  command._paramBadgeF = command._hf;
  command._paramBadgeB = command._hj;
  const responseSchema = resolveSchema(op.responses?.['200']?.content?.['application/json']?.schema);
  if (responseSchema) command.res = responseSchema;
  command.r = op.pattern || null;
  applyPathOverrides(command);
  return command;
};
const generateCurl = i => {
  const c = COMMANDS[i], is_diff = (curr && COMMANDS.indexOf(curr) === parseInt(i));
  const live = is_diff ? ParamManager.getCurrent() : { h: [], q: [], f: [], u: [], j: [] };
  const merge = (spec, liveRows) => {
    const res = spec.map(s => { const l = liveRows.find(x => x.k === s.k); return { ...s, v: l ? l.v : s.v }; });
    liveRows.forEach(l => { if (l.k && !res.find(x => x.k === l.k)) res.push(l); });
    return res;
  };
  const hData = merge(c.h, live.h), qData = merge(c.q, live.q), fData = merge(c.f, live.f), uData = merge(c.u, live.u), jData = merge(c.j, live.j);
  let path = c.p;
  uData.forEach(x => { path = path.replace(`{${x.k}}`, x.v || 'null'); });
  const sanitize = v => (v === '' || (typeof v === 'string' && v.includes('{') && v.includes('}'))) ? 'null' : v;
  const h = [];
  hData.forEach(x => {
    let val = x.v;
    if (x.k.toLowerCase() === 'authorization') {
      val = Store.token || val;
      const sVal = sanitize(val);
      val = sVal !== 'null' ? (sVal.startsWith('Bearer ') ? sVal : `Bearer ${sVal}`) : 'Bearer null';
      h.push(`-H "${x.k}: ${val}"`);
    } else h.push(`-H "${x.k}: ${sanitize(val)}"`);
  });
  if (Store.token && !hData.some(x => x.k.toLowerCase() === 'authorization')) {
    h.push(`-H "Authorization: Bearer ${Store.token}"`);
  }
  const qStr = qData.filter(x => x.k).map(x => `${encodeURIComponent(x.k)}=${encodeURIComponent(sanitize(x.v)).replace(/%7B/g, '{').replace(/%7D/g, '}')}`).join('&');
  const url = window.location.origin + path + (qStr ? '?' + qStr : '');
  let body = '';
  if (jData.length || c._hj) {
    const b = {};
    jData.forEach(x => { try { b[x.k] = ParamManager.cast(x.v, x.t, x.k); } catch(e) { b[x.k] = x.v; } });
    body = `-d '${JSON.stringify(b)}'`;
    if (!h.some(x => x.includes('Content-Type'))) h.push('-H "Content-Type: application/json"');
  } else if (fData.length || c._hf) {
    body = fData.map(x => `-F "${x.k}=${sanitize(x.v)}"`).join(' ');
  }
  return `curl -X ${c.m} "${url}" ${h.join(' ')} ${body}`.trim().replace(/\s+/g, ' ');
};

/**
 * @description Exports the entire API catalog to a CSV file.
 */
const exportCatalogCsv = () => {
    const getParamSummary = c => {
        const list = [];
        if (c._paramBadgeH) list.push('H');
        if (c._paramBadgeQ) list.push('Q');
        if (c._paramBadgeF) list.push('F');
        if (c._paramBadgeB) list.push('B');
        return list.length ? list.join(' ') : '-';
    };
    const csv = ['#,Method,Path,Params,Curl',
        ...COMMANDS.map((c, i) => `${i + 1},${csvEscape(c.m)},${csvEscape(c.p)},${csvEscape(getParamSummary(c))},${csvEscape(generateCurl(i))}`)
    ].join('\n');
    downloadCsv('api_master_catalog.csv', csv);
};
const wsLog = (msg, type='info') => {
  const time = new Date().toLocaleTimeString();
  const color = type === 'error' ? 'var(--delete)' : (type === 'sent' ? 'var(--accent)' : (type === 'received' ? 'var(--primary)' : 'var(--muted)'));
  const html = `<div style="margin-bottom:4px"><span style="opacity:0.5">[${time}]</span> <span style="color:${color}">${msg}</span></div>`;
  const box = UI('wsLogs');
  box.innerHTML += html;
  box.scrollTop = box.scrollHeight;
};
const wsToggleConnect = () => {
  if (ws && ws.readyState < 2) return wsDisconnect();
  const url = UI('wsUrlIn').value;
  wsLog(`Connecting to ${url}...`);
  ws = new WebSocket(url);
  ws.onopen = () => {
    wsLog('Connection established', 'received');
    UI('wsConnBtn').textContent = 'Disconnect';
    UI('wsConnBtn').style.background = 'var(--delete)';
  };
  ws.onmessage = e => wsLog(`Received: ${e.data}`, 'received');
  ws.onerror = e => wsLog('Connection error', 'error');
  ws.onclose = () => {
    wsLog('Connection closed');
    UI('wsConnBtn').textContent = 'Connect';
    UI('wsConnBtn').style.background = 'var(--primary)';
  };
};
const wsDisconnect = () => { if (ws) ws.close(); };
const wsSend = () => {
  if (!ws || ws.readyState !== 1) return toast('Not connected');
  const val = UI('wsMsgIn').value;
  if (!val) return;
  ws.send(val);
  wsLog(`Sent: ${val}`, 'sent');
  UI('wsMsgIn').value = '';
};
const resolveRef = (r, s) => {
  if (!r || !r.startsWith('#/')) return null;
  const parts = r.split('/').slice(1);
  return parts.reduce((o, i) => o?.[i], s);
};

const schemaToExample = (s, spec) => {
  if (!s) return null;
  if (s.$ref) return schemaToExample(resolveRef(s.$ref, spec), spec);
  if (s.allOf) {
    const combined = { type: 'object', properties: {} };
    s.allOf.forEach(p => {
      const res = resolveRef(p.$ref, spec) || p;
      if (res.properties) Object.assign(combined.properties, res.properties);
    });
    return schemaToExample(combined, spec);
  }
  if (s.anyOf || s.oneOf) {
    const a = (s.anyOf || s.oneOf).find(x => x.type !== 'null') || (s.anyOf || s.oneOf)[0];
    return schemaToExample(a, spec);
  }
  if (s.type === 'object') {
    const res = {};
    for (const [k, p] of Object.entries(s.properties || {})) { res[k] = schemaToExample(p, spec); }
    return res;
  }
  if (s.type === 'array') return [schemaToExample(s.items, spec)];
  if (s.type === 'string') return s.default || 'str';
  if (s.type === 'integer' || s.type === 'number') return s.default || 0;
  if (s.type === 'boolean') return s.default || false;
  return null;
};
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
      if (r.ok && json && curr.p === '/auth/login-password-username') {
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
const testNeedsToken = c => {
  if (c.h && c.h.some(x => x.k.toLowerCase() === 'authorization')) return 1;
  if (c.p.startsWith('/my/') || c.p.startsWith('/admin/')) return 1;
  return 0;
};
/**
 * @description Executes an API by its global index without touching the Runner UI.
 * @param {number} index - The global command index.
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
const exportTestCsv = () => {
  const visibleIndexes = getVisibleMasterIndexes();
  if (!visibleIndexes.length) return toast('No visible APIs to export');
  const csv = ['#,Method,Path,Status,Time(ms),Result,Curl,Response',
    ...visibleIndexes.map(i => {
      const c = COMMANDS[i];
      const responseState = Store.getResponse(i);
      let result = 'NOT_RUN';
      if (responseState) result = responseState.status >= 200 && responseState.status < 300 ? 'PASS' : 'FAIL';
      const status = responseState ? responseState.status : '-';
      const time = responseState ? responseState.time : 0;
      const responseJson = responseState ? JSON.stringify(responseState.data) : '';
      return `${i + 1},${c.m},${csvEscape(c.p)},${status},${time},${result},${csvEscape(generateCurl(i))},${csvEscape(responseJson)}`;
    })
  ].join('\n');
  downloadCsv('api_test_results.csv', csv);
};
const PATH_OVERRIDES = {
  // My & Account
  '/my/api-usage': { days: 7 },
  '/my/account-delete': { mode: 'soft' },
  '/my/parent-read': { table: 'test', parent_table: 'users', parent_column: 'created_by_id' },
  '/my/ids-delete': { table: 'test', ids: '1,2,3,4,5' },
  '/my/object-create': {
    table: 'test',
    is_serialize: 1,
    type: 1,
    title: 'test',
    tag: ['java', 'python', 'sql'],
    location: 'POINT(17.794387 -83.032150)',
    metadata: {
      id: 1,
      name: 'test',
      is_active: 1,
      score: 99.5,
      notes: null,
      tag: ['java', 'sql', 'ai'],
      details: {
        version: '2.1',
        category: 'backend',
        metrics: {
          uptime: 99.9,
          requests: 1000
        }
      }
    }
  },
  '/my/object-update': { id: 1, name: 'test', table: 'users' },
  '/my/object-read': { table: 'test' },

  // Messaging
  '/my/message-received': { mode: 'all' },
  '/my/message-inbox': { mode: 'all' },
  '/my/message-thread': { user_id: 1 },
  '/my/message-delete-single': { id: 1 },
  '/my/message-delete-bulk': { mode: 'all' },

  // Public
  '/admin/sync': { is_background: 1 },
  '/public/converter-number': { datatype: 'int', mode: 'encode', x: '123' },
  '/public/object-create': {
    table: 'test',
    is_serialize: 1,
    type: 1,
    title: 'test',
    tag: ['java', 'python', 'sql'],
    location: 'POINT(17.794387 -83.032150)',
    metadata: {
      id: 1,
      name: 'test',
      is_active: 1,
      score: 99.5,
      notes: null,
      tag: ['java', 'sql', 'ai'],
      details: {
        version: '2.1',
        category: 'backend',
        metrics: {
          uptime: 99.9,
          requests: 1000
        }
      }
    }
  },
  '/public/object-read': {
    table: 'test',
    id: '>=,1',
    type: '=,1',
    tag: 'contains,tag0',
    location: 'point,80.0|15.0|0|5000',
    metadata: 'contains,role|user|str',
    creator_key: 'username,name,email',
    action_key: 'report_test,test_id,count,id'
  },
  '/public/table-tag-read': { table: 'test', column: 'tag' },

  // Private & Admin
  '/admin/postgres-runner': { 
    mode: 'write', 
    query: "DO $$ \nBEGIN \n  FOR i IN 1..1000 LOOP \n    INSERT INTO test (type, title, description, tag, tag_int, location, metadata, is_active, is_verified, rating) \n    VALUES (\n      (i % 10) + 1, \n      'Obj ' || i, \n      'Desc ' || i, \n      ARRAY['tag' || (i % 5), 'tag' || (i % 3)], \n      ARRAY[i % 10, (i + 1) % 10], \n      ST_SetSRID(ST_MakePoint(80.0 + (i * 0.001), 15.0 + (i * 0.001)), 4326)::geography, \n      jsonb_build_object('id', i, 'role', 'user', 'active', true), \n      1, \n      1, \n      (i % 5) + 0.5\n    ); \n  END LOOP; \nEND $$;" 
  },
  '/admin/postgres-export': { query: 'SELECT * FROM test' },
  '/admin/object-create': { table: 'test', obj_list: [{type:1,title:'Object 1'},{type:2,title:'Object 2'},{type:1,title:'Object 3'},{type:3,title:'Object 4'},{type:2,title:'Object 5'},{type:1,title:'Object 6'},{type:4,title:'Object 7'},{type:2,title:'Object 8'},{type:1,title:'Object 9'},{type:3,title:'Object 10'},{type:2,title:'Object 11'},{type:1,title:'Object 12'},{type:4,title:'Object 13'},{type:2,title:'Object 14'},{type:1,title:'Object 15'}] },
  '/admin/object-update': { id: 1, name: 'test', table: 'users' },
  '/admin/object-read': { table: 'test' },
  '/admin/ids-delete': { table: 'test', ids: '1,2,3,4,5' },

  // Pages
  '/page-{name}': { name: 'api' }
};
