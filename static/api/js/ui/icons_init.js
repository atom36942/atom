/**
 * @description Centralized icon setup for persistent UI elements.
 */
const setupIcons = () => {
    const iconMap = {
        'infoToggleBtn': ICON.info(18),
        'storageToggleBtn': ICON.database(18),
        'analyticsToggleBtn': ICON.chart(18),
        'apiInfoCsv': ICON.downloadCsv(18),
        'btnRaw': ICON.code(16),
        'btnPretty': ICON.list(16),
        'btnTable': ICON.table(16),
        'rCopy': ICON.copy(16),
        'rCopyFull': ICON.copyCurl(16),
        'rCsv': ICON.downloadCsv(16),
        'rJson': ICON.downloadJson(16),
        'testAllExportCsv': ICON.downloadCsv(16),
        'testResponseJson': ICON.downloadJson(20),
        'testResponseCopy': ICON.copy(20),
        'testParamsCopyCurl': ICON.copy(20),
        'storageCopyAll': ICON.copy(18),
        'storageResetAll': ICON.trash(18),
        'cellPopCopy': ICON.copy(14),
        'curlViewCopy': ICON.copy(16),
        'curlViewResCopy': ICON.copy(16),
        'curlViewOvrCopy': ICON.copy(16),
        'masterBtnRaw': ICON.code(16),
        'masterBtnPretty': ICON.list(16),
        'masterBtnTable': ICON.table(16),
        'masterRespCopy': ICON.copy(16),
        'masterRespCopyFull': ICON.copyCurl(16),
        'masterRespCsv': ICON.downloadCsv(16),
        'masterRespJson': ICON.downloadJson(16),
        'runnerOvrBtn': ICON.ovr(20),
        'runnerLinkBtn': ICON.link(20),
        'runnerCurlBtn': ICON.terminal(20),
        'subBtnIcon': ICON.play(14)
    };

    Object.entries(iconMap).forEach(([id, svg]) => {
        const el = UI(id);
        if (el && svg) el.innerHTML = svg;
    });
    d.querySelectorAll('.modal-header .icon-btn[title="Close"]').forEach(btn => {
        btn.innerHTML = ICON.close(24);
    });
};
