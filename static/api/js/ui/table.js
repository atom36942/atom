/**
 * @description Renders the API filter tags based on current path distribution.
 */
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

/**
 * @description Adjusts the master table layout based on path lengths.
 */
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

/**
 * @description Renders the main API master table.
 */
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
      const hasRes = !!responseState;
      
      return `
        <tr data-i="${globalIndex}">
          <td class="col-id master-static-cell">${globalIndex + 1}</td>
          <td class="col-method master-static-cell"><span class="method-badge ${c.m.toLowerCase()}">${c.m}</span></td>
          <td class="col-path master-static-cell" title="${c.p}">${c.p}</td>
          <td class="col-param master-static-cell clickable params-preview-btn" title="View Configuration Details">${isWs ? '-' : renderParamBadges(c)}</td>
          <td class="col-time master-status-cell ${hasRes ? 'clickable' : ''}" title="${hasRes ? `HTTP ${responseState.status}` : 'No response yet'}">${isWs ? '-' : renderStatusBadge(responseState?.status)}</td>
          <td class="col-time master-time-cell">${isWs ? '-' : (responseState ? `${responseState.time}ms` : '-')}</td>
          <td class="col-run run-btn clickable" title="Run">${ICON.play(16)}</td>
        </tr>`;

    }).join('')}</tbody>`;
  updateTestSummary();
};

/**
 * @description Renders status badge HTML for a given status code.
 */
const renderStatusBadge = status => {
  if (status == null) return '<span class="status-text neutral">-</span>';
  return `<span class="status-text ${getStatusClass(status)}">${status}</span>`;
};

/**
 * @description Renders parameter presence badges for an API command.
 */
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

/**
 * @description Renders method badge and path for the runner header.
 */
const renderRunnerEndpoint = command => {
  if (!command) return '';
  return `<div style="display:flex;align-items:center;gap:10px;font-family:'SF Mono',Menlo,monospace;line-height:1"><span class="method-badge ${command.m.toLowerCase()}" style="margin:0;line-height:1.2">${command.m}</span><span class="runner-endpoint-path" style="display:inline;margin:0;line-height:1">${he(command.p)}</span></div>`;
};
