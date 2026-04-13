let ws = null;

/**
 * @description Logs a message to the WebSocket runner console.
 */
const wsLog = (msg, type='info') => {
  const time = new Date().toLocaleTimeString();
  const color = type === 'error' ? 'var(--delete)' : (type === 'sent' ? 'var(--accent)' : (type === 'received' ? 'var(--primary)' : 'var(--muted)'));
  const html = `<div style="margin-bottom:4px"><span style="opacity:0.5">[${time}]</span> <span style="color:${color}">${msg}</span></div>`;
  const box = UI('wsLogs');
  box.innerHTML += html;
  box.scrollTop = box.scrollHeight;
};

/**
 * @description Toggles the WebSocket connection.
 */
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

/**
 * @description Forcefully closes the current WebSocket.
 */
const wsDisconnect = () => { if (ws) ws.close(); };

/**
 * @description Sends a message through the active WebSocket.
 */
const wsSend = () => {
  if (!ws || ws.readyState !== 1) return toast('Not connected');
  const val = UI('wsMsgIn').value;
  if (!val) return;
  ws.send(val);
  wsLog(`Sent: ${val}`, 'sent');
  UI('wsMsgIn').value = '';
};

/**
 * @description Initializes the WebSocket runner for a given command index.
 */
const loadWs = i => {
  curr = COMMANDS[i];
  const prot = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  UI('wsUrlIn').value = `${prot}//${window.location.host}${curr.p}`;
  UI('wsLogs').innerHTML = '<div style="color:var(--accent)">Waiting to connect...</div>';
  UI('wsConnBtn').textContent = 'Connect';
  UI('wsConnBtn').style.background = 'var(--primary)';
};
