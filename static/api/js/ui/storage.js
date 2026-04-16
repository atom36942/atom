/**
 * @description Renders the local storage debug table within the storage modal.
 */
const renderStorage = () => {
  const rowList = getStorageRows();
  if (!rowList.length) {
    UI('storageContent').innerHTML = '<div style="padding:40px;text-align:center;color:var(--muted)">No data stored in localStorage</div>';
    return;
  }
  const keyLengthMax = rowList.reduce((max, row) => {
    if (row.key.length > max) return row.key.length;
    return max;
  }, 0);
  const keyWidthCh = Math.min(Math.max(keyLengthMax + 2, 18), 30);
  const sizeWidthCh = 8;
  const rows = rowList.map((row, idx) => {
    const valStr = typeof row.value === 'object' ? JSON.stringify(row.value, null, 2) : String(row.value);
    const size = new Blob([valStr]).size;
    const sizeStr = size > 1024 ? (size / 1024).toFixed(1) + ' KB' : size + ' B';
    return `
      <tr>
        <td style="width:40px;text-align:left!important">${idx + 1}</td>
        <td style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="${row.key}">${row.key}</td>
        <td style="width:90px;text-align:right">${sizeStr}</td>
        <td style="width:140px;text-align:right">
          <div class="storage-action-wrap" style="display:flex;justify-content:flex-end;gap:8px">
            <button class="icon-btn storage-view-btn" data-key="${row.key}" data-scope="${row.scope}" title="View JSON">${ICON.eye(14)}</button>
            <button class="icon-btn storage-copy-btn" data-key="${row.key}" data-scope="${row.scope}" title="Copy Value">${ICON.copy(14)}</button>
            <button class="icon-btn delete storage-del-btn" data-key="${row.key}" data-scope="${row.scope}" title="${row.removable ? 'Delete Key' : 'Delete Root Key'}">${ICON.trash(14)}</button>
          </div>
        </td>
      </tr>`;
  }).join('');

  UI('storageContent').innerHTML = `
    <div class="resp-tbl-wrap">
        <table class="resp-tbl" style="width:100%;table-layout:fixed">
            <thead>
                <tr>
                    <th style="width:40px;text-align:left!important">#</th>
                    <th style="text-align:left">Key</th>
                    <th style="width:90px;text-align:right">Size</th>
                    <th style="width:140px;text-align:right">Action</th>
                </tr>
            </thead>
            <tbody>${rows}</tbody>
        </table>
    </div>`;
};
