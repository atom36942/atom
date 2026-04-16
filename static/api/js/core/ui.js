const d = document;

/**
 * @namespace UI
 * @description Centralized DOM element registry with caching.
 * Re-fetches from DOM if the cached element is no longer connected.
 * @param {string} id - The element ID.
 * @returns {HTMLElement}
 */
const UI = id => {
    const cached = UI.cache[id];
    if (cached && cached.isConnected) return cached;
    return (UI.cache[id] = d.getElementById(id));
};
UI.cache = {};
const $ = UI;

/**
 * @description Extracts tags from a path string.
 * @param {string} p - The path.
 * @returns {string[]}
 */
const getPathTags = p => p.split(/[\/-]/).filter(x => x.length > 1 && !x.startsWith('{'));

/**
 * @description Gets the CSS class for a status code.
 * @param {number|null} status - The HTTP status code.
 * @returns {string}
 */
const getStatusClass = status => {
  if (status == null) return 'neutral';
  if (status >= 200 && status < 300) return 'success';
  if (status >= 400 || status === 0) return 'error';
  return 'info';
};
