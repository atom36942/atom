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
      d: nextSchema.description || null,
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
      d: nextSchema.description || null,
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
      req: false,
      ovr: true
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
      d: param.description || schema.description || null,
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
