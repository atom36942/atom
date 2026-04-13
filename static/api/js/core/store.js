/* ── Storage helper ── */
const STORAGE_KEY_TOKEN = 'token';
const STORAGE_KEY_RESPONSE = 'response';

const parseStorageJson = key => {
  const rawValue = localStorage.getItem(key);
  if (rawValue == null) return null;
  try {
    return JSON.parse(rawValue);
  } catch (err) {
    return rawValue;
  }
};

const migrateLegacyStorage = () => {
  const legacyState = parseStorageJson('api_master');
  const legacyResponses = parseStorageJson('api_master_responses');
  const currentToken = localStorage.getItem(STORAGE_KEY_TOKEN);
  if (!currentToken && legacyState && typeof legacyState === 'object') {
    const nextToken = legacyState.token || legacyState.auth?.token;
    if (nextToken) localStorage.setItem(STORAGE_KEY_TOKEN, nextToken);
  }
  if (!localStorage.getItem(STORAGE_KEY_RESPONSE) && legacyResponses && typeof legacyResponses === 'object' && !Array.isArray(legacyResponses) && Object.keys(legacyResponses).length) {
    localStorage.setItem(STORAGE_KEY_RESPONSE, JSON.stringify(legacyResponses));
  }
  localStorage.removeItem('api_master');
  localStorage.removeItem('api_master_responses');
};

migrateLegacyStorage();

/**
 * @namespace Store
 * @description Unified state management for authentication tokens and API responses.
 */
const Store = {
  get token() { return localStorage.getItem(STORAGE_KEY_TOKEN) || ''; },
  set token(v) { if (!v) localStorage.removeItem(STORAGE_KEY_TOKEN); else localStorage.setItem(STORAGE_KEY_TOKEN, v); },

  get responses() {
    try { return JSON.parse(localStorage.getItem(STORAGE_KEY_RESPONSE)) || {}; } catch { return {}; }
  },
  set responses(v) { if (!v || !Object.keys(v).length) localStorage.removeItem(STORAGE_KEY_RESPONSE); else localStorage.setItem(STORAGE_KEY_RESPONSE, JSON.stringify(v)); },

  getResponse(i) { return this.responses[String(i)] || null; },
  setResponse(i, val) {
    const r = this.responses;
    r[String(i)] = val;
    this.responses = r;
  },
  removeResponse(i) {
    const r = this.responses;
    delete r[String(i)];
    this.responses = r;
  },
  clear() {
    localStorage.removeItem(STORAGE_KEY_TOKEN);
    localStorage.removeItem(STORAGE_KEY_RESPONSE);
  }
};

const getStorageSnapshot = () => {
  const snapshot = {};
  [STORAGE_KEY_TOKEN, STORAGE_KEY_RESPONSE].forEach(key => {
    const rawValue = localStorage.getItem(key);
    if (rawValue == null) return;
    snapshot[key] = parseStorageJson(key);
  });
  return snapshot;
};

const getStorageRows = () => {
  const rowList = [];
  const snapshot = getStorageSnapshot();
  if (Object.prototype.hasOwnProperty.call(snapshot, STORAGE_KEY_TOKEN)) {
    rowList.push({ scope: 'token', key: STORAGE_KEY_TOKEN, value: snapshot[STORAGE_KEY_TOKEN], removable: 1 });
  }
  if (Object.prototype.hasOwnProperty.call(snapshot, STORAGE_KEY_RESPONSE)) {
    rowList.push({ scope: 'response', key: STORAGE_KEY_RESPONSE, value: snapshot[STORAGE_KEY_RESPONSE], removable: 1 });
  }
  return rowList;
};

const deleteStorageEntry = row => {
  if (row.key === STORAGE_KEY_TOKEN) {
    Store.token = null;
    return 1;
  }
  if (row.key === STORAGE_KEY_RESPONSE) {
    Store.responses = null;
    return 1;
  }
  return 0;
};
