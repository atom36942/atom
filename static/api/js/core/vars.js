/** @type {any[]} */
let COMMANDS = [];
/** @type {any} */
let SPEC = null;
/** @type {string|null} */
let activeApiTag = null;
/** @type {string} */
let activeMasterResultFilter = 'all';

let curr = null, orig = [];
let activeMasterRunIndex = null, testResponseRaw = '';
let cellPopRaw = '';
