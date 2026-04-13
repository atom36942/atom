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
        <td class="col-id" style="text-align:left!important">${idx + 1}</td>
        <td class="storage-key-cell" title="${row.key}">${row.key}</td>
        <td class="storage-size-cell">${sizeStr}</td>
        <td>
          <div class="storage-action-wrap">
            <button class="icon-btn storage-view-btn" data-key="${row.key}" data-scope="${row.scope}" title="View JSON">${ICON.eye(14)}</button>
            <button class="icon-btn storage-copy-btn" data-key="${row.key}" data-scope="${row.scope}" title="Copy Value">${ICON.copy(14)}</button>
            <button class="icon-btn delete storage-del-btn" data-key="${row.key}" data-scope="${row.scope}" title="${row.removable ? 'Delete Key' : 'Delete Root Key'}">${ICON.trash(14)}</button>
          </div>
        </td>
      </tr>`;
  }).join('');
  UI('storageContent').innerHTML = `
    <table class="resp-tbl" style="table-layout:fixed;width:100%">
        <colgroup>
            <col style="width:32px">
            <col style="width:${keyWidthCh}ch">
            <col style="width:${sizeWidthCh}ch">
            <col style="width:120px">
        </colgroup>
        <thead>
            <tr>
                <th class="col-id" style="text-align:left!important">#</th>
                <th style="text-align:left">Key</th>
                <th style="text-align:right">Size</th>
                <th style="text-align:right">Action</th>
            </tr>
        </thead>
        <tbody>${rows}</tbody>
    </table>`;
};
