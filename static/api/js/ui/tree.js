/**
 * @description Recursive tree renderer for JSON objects.
 */
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

/**
 * @description Formats primitive values for the tree view.
 */
const gvVal = v => {
    if (v === null) return '<span class="jl">null</span>';
    if (typeof v === 'string') return `<span class="js">"${v}"</span>`;
    if (typeof v === 'number') return `<span class="jn">${v}</span>`;
    if (typeof v === 'boolean') return `<span class="jb">${v}</span>`;
    return String(v);
};

/**
 * @description Render object/array as a responsive HTML table.
 */
const fmtGrid = v => {
  if (v == null || typeof v !== 'object') return null;
  const isArr = Array.isArray(v);
  const arr = isArr ? v : [v];
  if (!arr.length || typeof arr[0] !== 'object' || arr[0] === null) return null;
  
  const keys = [...new Set(arr.flatMap(Object.keys))];
  const colW = k => Math.min(300, Math.max(120, k.length * 10 + 40));

  // Shared Horizontal Data Grid Logic (Unified for Objects & Arrays)
  const tableRows = arr.map((row, rowIndex) => `
    <tr style="background:${rowIndex % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.01)'}">
      ${keys.map(k => {
          const cv = row[k];
          const val = cv == null ? '' : (typeof cv === 'object' ? JSON.stringify(cv) : String(cv));
          const enc = val.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
          const isLong = val.length > 60;
          const display = isLong ? he(val.substring(0, 57)) + '...' : enc;
          const viewBtn = isLong ? `<button type="button" class="icon-btn cell-expand-btn" data-raw="${encodeURIComponent(val)}" title="View Full Value" style="padding:2px;margin-left:auto">${ICON.expand(14)}</button>` : '';
          return `<td title="${enc}"><div style="display:flex;align-items:center;gap:8px;max-width:${colW(k)}px"><span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap;flex:1">${display}</span>${viewBtn}</div></td>`;
      }).join('')}
    </tr>`).join('');

  return `
    <div class="modal-card panel-shell" style="margin:16px;">
        <div class="modal-card-body" style="padding:0">
            <div class="resp-tbl-wrap master-table-wrap" style="max-height:500px; opacity:1">
                <table class="resp-tbl">
                    <thead><tr>${keys.map(k => `<th style="width:${colW(k)}px;min-width:${colW(k)}px">${he(k)}</th>`).join('')}</tr></thead>
                    <tbody>${tableRows}</tbody>
                </table>
            </div>
        </div>
    </div>`;
};

/**
 * @description Syntax highlighting for JSON strings.
 */
const highlight = s => s
  .replace(/"([^"]+)"\s*:/g, '<span class="jk">"$1"</span>:')
  .replace(/:"([^"]*)"/g, ':<span class="js">"$1"</span>')
  .replace(/:\s*([\d.]+)/g, ': <span class="jn">$1</span>')
  .replace(/:\s*(true|false)/g, ': <span class="jb">$1</span>')
  .replace(/:\s*(null)/g, ': <span class="jl">$1</span>');

/**
 * @description Syntax highlighting for cURL commands.
 */
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

/**
 * @description Compresses JSON array displays in pre blocks.
 */
const compactArrays = s => s.replace(
  /\[\n((\s+("(?:[^"\\]|\\.)*"|[\d.eE+-]+|true|false|null),?\n)+\s*)\]/g,
  m => m.replace(/\n\s*/g, ' ').replace(/,\s*/g, ', ')
);
