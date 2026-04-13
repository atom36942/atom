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
