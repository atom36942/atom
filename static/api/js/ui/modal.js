/**
 * @description Shows a modal by its ID.
 */
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

/**
 * @description Hides a modal by its ID.
 */
const hideModal = id => {
  const el = UI(id);
  if (!el) return;
  el.style.display = 'none';
  el.style.zIndex = '';
};

/**
 * @namespace ResponseView
 * @description Logic for rendering and switching between response views (Raw/Pretty/Table).
 */
const ResponseView = {
  states: {
    runner: { data: null, status: null, time: null, index: null, view: 'raw' },
    master: { data: null, status: null, time: null, index: null, view: 'raw' }
  },

  render(scope, data, status, time, index = null) {
    const s = this.states[scope];
    s.data = data; s.status = status; s.time = time; s.index = index;
    const isMaster = scope === 'master';
    const codeColor = status >= 200 && status < 300 ? 'var(--primary)' : (status >= 400 ? 'var(--delete)' : 'var(--accent)');
    const codeHtml = (status != null ? `<span style="color:${codeColor};font-weight:600">${status}</span>` : '') + 
                     (time != null ? ` <span style="color:var(--muted);font-size:11px;margin-left:8px">${time}ms</span>` : '');
    UI(isMaster ? 'masterRespCode' : 'rCode').innerHTML = codeHtml;
    UI(isMaster ? 'masterRespBox' : 'rBox').classList.add('show');
    this.switchTo(scope, s.view);
  },

  switchTo(scope, type) {
    const s = this.states[scope];
    s.view = type;
    const isMaster = scope === 'master';
    const btnP = isMaster ? 'masterBtn' : 'btn';
    const viewP = isMaster ? 'masterView' : 'view';
    const data = s.data;
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
      if (tableHtml) {
        UI(isMaster ? 'masterViewTable' : 'viewTable').innerHTML = tableHtml;
      } else {
        UI(isMaster ? 'masterViewTable' : 'viewTable').innerHTML = `<div style="padding:50px;text-align:center;color:var(--muted);font-style:italic;line-height:1.6">Table view not available for this response type.<br>Please use <b>Tree View</b> or <b>Raw View</b> for detailed inspection.</div>`;
      }
    }
  },

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

/**
 * @description Opens a JSON response modal with formatted view.
 */
const openJsonResponseModal = (title, data) => {
  const jsonStr = JSON.stringify(data, null, 2);
  testResponseRaw = jsonStr;
  UI('testResponseTitle').textContent = title;
  UI('testResponseContent').innerHTML = `<pre class="resp-pre" style="padding:20px;margin:0">${highlight(compactArrays(jsonStr))}</pre>`;
  UI('testResponseCopy').onclick = () => copyWithFeedback(UI('testResponseCopy'), jsonStr, 16, 'Response copied');
  UI('testResponseJson').onclick = () => downloadJson('response.json', jsonStr);
  setupIcons();
  showModal('testResponseModal');
};

/**
 * @description Opens the response details modal for a master list item.
 */
const openMasterResponse = (i) => {
    const res = Store.getResponse(i);
    if (!res) return;
    UI('masterRespIn').innerHTML = renderRunnerEndpoint(COMMANDS[i]);
    ResponseView.render('master', res.data, res.status, res.time, i);
    setupIcons();
    showModal('masterResponseModal');
};

/**
 * @description Opens the CURL/Override view modal.
 */
const openCurlViewModal = (indexValue, viewType) => {
  viewType = viewType || 'all';
  const command = COMMANDS[indexValue];
  if (!command || command.m === 'WS') return;

  const ovr = PATH_OVERRIDES[command.p];
  const showAll = viewType === 'all';
  const showOvr = viewType === 'ovr';

  const badge = `<span class="method-badge ${command.m.toLowerCase()}" style="margin-right:8px">${command.m}</span>`;
  UI('curlViewTitle').innerHTML = (showOvr && !showAll) ? `API Overrides: ${command.p}` : `${badge}${command.p}`;
  
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
  setupIcons();
  showModal('curlViewModal');
};

/**
 * @description Opens the multi-card parameter preview modal for a given API.
 */
const openParamsPreviewModal = i => {
    const c = COMMANDS[i];
    if (!c) return;
    const badge = `<span class="method-badge ${c.m.toLowerCase()}" style="margin-right:8px">${c.m}</span>`;
    UI('testParamsTitle').innerHTML = `${badge}${c.p}`;
    
    const carts = [];
    const addCard = (title, data) => {
        if (!data || (Array.isArray(data) && !data.length)) return;
        
        // Flatten array of objects [{k, v}, ...] to {k: v, ...}
        let obj = data;
        if (Array.isArray(data)) {
            obj = {};
            data.forEach(x => { if (x.k) obj[x.k] = x.v; });
        }
        
        if (Object.keys(obj).length === 0) return;

        const formatted = JSON.stringify(obj, null, 2);
        carts.push(`
            <div class="modal-card">
                <div class="modal-card-header"><h4>${title}</h4></div>
                <div class="modal-card-body" style="padding:0">
                    <pre class="resp-pre" style="padding:16px;margin:0;font-size:12px">${highlight(formatted)}</pre>
                </div>
            </div>
        `);
    };

    addCard('PATH PARAMETERS (P)', c.u);
    addCard('QUERY PARAMETERS (Q)', c.q);
    addCard('HEADER PARAMETERS (H)', c.h);
    addCard('FORM DATA (F)', c.f);
    addCard('JSON BODY (B)', c.j);
    addCard('OVERRIDES (O)', PATH_OVERRIDES[c.p]);

    UI('testParamsContent').innerHTML = carts.join('') || `<div style="grid-column:1/-1;padding:50px;text-align:center;color:var(--muted);font-style:italic">No parameters defined for this API.</div>`;
    setupIcons();
    showModal('testParamsModal');
};

/**
 * @description Opens the parameter documentation modal.
 */
const showInfoModal = (k, r_pat, desc) => {
  UI('paramInfoTitle').innerHTML = `Configuration Detail: <span style="color:var(--accent);font-weight:700;background:rgba(255,255,255,0.05);padding:2px 10px;border-radius:6px;margin-left:8px;border:1px solid rgba(255,255,255,0.1)">${he(k)}</span>`;
  UI('paramInfoCopyBtn').innerHTML = ICON.copy(20);
  
  let html = '<div style="background:rgba(255,255,255,0.03);padding:24px;border-radius:12px;border:1px solid rgba(255,255,255,0.08);display:flex;flex-direction:column;gap:12px;width:fit-content;min-width:500px;max-width:900px">';
  
  if (desc || r_pat) {
    const parts = desc ? desc.split('. ').filter(p => p.trim()) : [];
    const finalItems = [];

    if (r_pat) {
      let bullet1 = `<code style="background:rgba(0,0,0,0.2);padding:2px 6px;border-radius:4px;font-size:12px;color:var(--accent);font-family:'SF Mono',Menlo,monospace">${he(r_pat)}</code>`;
      if (parts.length > 0) {
        bullet1 += ` <span style="color:var(--muted);font-style:italic;margin-left:6px">[${he(parts[0])}]</span>`;
      }
      finalItems.push(bullet1);
      if (parts.length > 1) finalItems.push(...parts.slice(1));
    } else {
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
  
  const modalCont = UI('paramInfoModal').querySelector('.modal-content');
  modalCont.style.width = 'fit-content';
  modalCont.style.minWidth = '500px';
  modalCont.style.maxWidth = '1000px';
  showModal('paramInfoModal');
};
