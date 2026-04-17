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
const downloadJson = (filename, data) => {
  const jsonStr = typeof data === 'string' ? data : JSON.stringify(data, null, 2);
  downloadBlob(new Blob([jsonStr], { type: 'application/json' }), filename);
};

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

const debounce = (fn, ms) => {
  let t;
  return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms) };
};

const generateCurl = cmdOrIdx => {
  const c = typeof cmdOrIdx === 'number' ? COMMANDS[cmdOrIdx] : cmdOrIdx;
  if (!c) return '';
  const is_diff = curr && (c === curr);
  const live = is_diff ? ParamManager.getCurrent() : { h: [], q: [], f: [], u: [], j: [] };
  const merge = (spec, liveRows) => {
    const res = (spec || []).map(s => { const l = liveRows.find(x => x.k === s.k); return { ...s, v: l ? l.v : s.v, files: l ? l.files : null }; });
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
    body = fData.map(x => {
        if (x.files?.length || x.t === 'file') {
            const fileName = (x.v || '').replace(/^C:\\fakepath\\/, '') || 'file.csv';
            return `-F "${x.k}=@${fileName}"`;
        }
        return `-F "${x.k}=${sanitize(x.v)}"`;
    }).join(' ');
  }
  return `curl -X ${c.m} "${url}" ${h.join(' ')} ${body}`.trim().replace(/\s+/g, ' ');
};

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
