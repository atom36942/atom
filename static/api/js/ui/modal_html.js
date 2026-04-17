/**
 * @namespace MODAL_HTML
 * @description Static HTML templates for all application modals and overlays.
 */
const MODAL_HTML = `
<!-- API Runner Modal -->
<div id="apiRunnerModal" class="modal"><div class="modal-content" style="max-width:760px;margin:2% auto">
    <div class="modal-header">
        <div class="modal-title-block">
            <h3>API Runner</h3>
        </div>
        <div class="modal-actions">
            <button type="button" class="icon-btn" id="runnerLinkBtn" title="Copy Direct API Link" onclick="if(curr){const link=\`\${window.location.origin}\${window.location.pathname}?api=\${curr.m}|\${curr.p}\`;copyWithFeedback(this,link,20,'Link copied');}"></button>
            <button type="button" class="icon-btn delete" id="runnerResetBtn" title="Clear Response History"></button>
            <button type="button" class="icon-btn" id="runnerCurlBtn" title="View Curl & Expected Response" onclick="if(activeMasterRunIndex!==null)openCurlViewModal(activeMasterRunIndex,'all');"></button>
            <button type="submit" class="btn btn-primary" id="subBtn" form="apiForm" title="Run API" style="height:36px;padding:0 16px;font-size:13px;flex:0 0 auto;gap:8px;display:flex;align-items:center"><div class="spinner"></div><span id="subBtnIcon" style="display:flex;align-items:center"></span><span id="subBtnText">Run</span></button>
            <button type="button" class="icon-btn" id="runnerCloseBtn" title="Close"></button>
        </div>
    </div>
    <div class="modal-body" style="height:75vh;display:flex;flex-direction:column;gap:10px;padding-bottom:12px">
        <div class="modal-card" style="flex:1;display:flex;flex-direction:column;min-height:0">
            <div class="modal-card-header">
                <div id="runnerPathHeader" style="font-size:13px;color:var(--muted);font-family:'SF Mono',Menlo,monospace"></div>
            </div>
            <div class="modal-card-body" style="overflow-y:auto">
                <form id="apiForm">
                    <div class="section-group" id="hSec"><div class="section-label">Headers <button type="button" id="addH" class="add-btn-small">+</button></div><div id="hCont" class="dynamic-container"></div></div>
                    <div class="section-group" id="uSec"><div class="section-label">Path Params <button type="button" id="addU" class="add-btn-small">+</button></div><div id="uCont" class="dynamic-container"></div></div>
                    <div class="section-group" id="qSec"><div class="section-label">Query Params <button type="button" id="addQ" class="add-btn-small">+</button></div><div id="qCont" class="dynamic-container"></div></div>
                    <div class="section-group" id="fSec"><div class="section-label">Form Data <button type="button" id="addF" class="add-btn-small">+</button></div><div id="fCont" class="dynamic-container"></div></div>
                    <div class="section-group" id="jSec"><div class="section-label">JSON Body <button type="button" id="addJ" class="add-btn-small">+</button></div><div id="jCont" class="dynamic-container"></div></div>
                </form>
            </div>
        </div>

        <div class="modal-card resp-box" id="rBox" style="flex:1;display:flex;flex-direction:column;min-height:0">
            <div class="modal-card-header">
                <h4>API RESPONSE <span id="rCode" style="font-weight:400;margin-left:8px"></span></h4>
                <div style="display:flex;align-items:center;gap:6px;margin-left:auto">
                    <button class="view-btn" data-view="raw" title="Raw View" id="btnRaw" disabled style="opacity:0.35;pointer-events:none"></button>
                    <button class="view-btn" data-view="pretty" title="Tree View" id="btnPretty" disabled style="opacity:0.35;pointer-events:none"></button>
                    <button class="view-btn" data-view="table" title="Table View" id="btnTable" disabled style="opacity:0.35;pointer-events:none"></button>
                    <div style="width:1px;height:16px;background:rgba(255,255,255,0.1);margin:0 4px"></div>
                    <button id="rCopy" class="icon-btn" title="Copy Response" disabled style="opacity:0.35;pointer-events:none"></button>
                    <button id="rCopyFull" class="icon-btn" title="Copy Curl & Response" disabled style="opacity:0.35;pointer-events:none"></button>
                    <div style="width:1px;height:16px;background:rgba(255,255,255,0.1);margin:0 4px"></div>
                    <button id="rCsv" class="icon-btn" title="Download CSV" disabled style="opacity:0.35;pointer-events:none"></button>
                    <button id="rJson" class="icon-btn" title="Download JSON" disabled style="opacity:0.35;pointer-events:none"></button>
                </div>
            </div>
            <div class="modal-card-body" style="padding:0;overflow-y:auto;display:flex;flex-direction:column">
                <div class="resp-content" style="flex:1">
                    <div id="viewPretty" class="resp-view active"></div>
                    <div id="viewRaw" class="resp-view"><pre class="resp-pre" id="rawPre" style="margin:0"></pre></div>
                    <div id="viewTable" class="resp-view"></div>
                </div>
            </div>
        </div>
    </div>
</div></div>

<!-- WebSocket Runner Modal -->
<div id="wsRunnerModal" class="modal"><div class="modal-content" style="max-width:760px;margin:2% auto">
    <div class="modal-header">
        <h3>WebSocket Runner</h3>
        <div class="modal-actions">
            <button type="button" class="icon-btn" id="wsRunnerCloseBtn" title="Close"></button>
        </div>
    </div>
    <div class="modal-body">
        <div id="wsIn" style="margin-bottom:20px;padding:12px;background:rgba(255,255,255,0.03);border-radius:8px;border:1px solid rgba(255,255,255,0.08);font-family:'SF Mono',Menlo,monospace;font-size:13px"></div>
        <div style="display:flex;gap:12px;margin-bottom:20px">
            <input type="text" id="wsUrlIn" readonly style="flex:1;background:rgba(255,255,255,0.02);color:var(--accent);font-weight:600">
            <button id="wsConnBtn" type="button" class="btn btn-primary" style="flex:0 0 120px">Connect</button>
        </div>
        <div style="margin-bottom:20px">
            <div class="section-label">Send Message</div>
            <div style="display:flex;gap:8px">
                <input type="text" id="wsMsgIn" placeholder="Type a message..." style="flex:1">
                <button type="button" id="wsSendBtn" class="btn btn-primary" style="flex:0 0 80px">Send</button>
            </div>
        </div>
        <div class="resp-box show" id="wsBox" style="display:flex;max-height:400px">
            <div class="resp-header">
                <span>Connection Logs <span id="wsCode" style="font-weight:400"></span></span>
                <button class="copy-btn" id="wsLogsClearBtn" title="Clear Logs"></button>
            </div>
            <div class="resp-content" id="wsLogs" style="padding:16px;font-family:'SF Mono',Menlo,monospace;font-size:12px;color:var(--muted)"></div>
        </div>
    </div>
</div></div>

<!-- Test Response Modal -->
<div id="testResponseModal" class="modal">
    <div class="modal-content" style="max-width:700px;margin:5% auto">
        <div class="modal-header">
            <h3 id="testResponseTitle">API Response</h3>
            <div class="modal-actions">
                <button type="button" class="icon-btn" id="testResponseJson" title="Download JSON"></button>
                <button type="button" class="icon-btn" id="testResponseCopy" title="Copy Response"></button>
                <button type="button" class="icon-btn" id="testResponseCloseBtn" title="Close"></button>
            </div>
        </div>
        <div class="modal-body">
            <div id="testResponseContent" style="background:#14171c;border-radius:8px;border:1px solid rgba(255,255,255,.08)"></div>
        </div>
    </div>
</div>

<!-- Test Params Modal -->
<div id="testParamsModal" class="modal">
    <div class="modal-content" style="max-width:540px;margin:5% auto">
        <div class="modal-header">
            <h3 id="testParamsTitle">API Configuration Preview</h3>
            <div class="modal-actions">
                <button type="button" class="icon-btn" id="testParamsCloseBtn" title="Close"></button>
            </div>
        </div>
        <div id="testParamsContent" class="modal-body modal-card-grid vertical-stack"></div>
    </div>
</div>



<!-- Info Modal -->
<div id="infoModal" class="modal"><div class="modal-content" style="max-width:800px;margin:2% auto">
    <div class="modal-header">
        <h3>API Master Information</h3>
        <div class="modal-actions">
            <button type="button" class="icon-btn" id="infoCloseBtn" title="Close"></button>
        </div>
    </div>
    <div class="modal-body modal-card-grid" style="display:flex;flex-direction:column;gap:10px">
        <div class="modal-card">
            <div class="modal-card-header"><h4>GENERAL INFORMATION</h4></div>
            <div class="modal-card-body">
                <div style="display:flex;flex-direction:column;gap:12px">
                    <div style="font-size:13px;color:var(--muted);display:flex;gap:12px;align-items:center">
                        <span style="opacity:0.6;min-width:145px">Base URL:</span>
                        <span id="baseUrl" style="color:var(--accent);font-weight:600;letter-spacing:0.5px"></span>
                    </div>
                    <div style="font-size:13px;color:var(--muted);display:flex;gap:12px;align-items:center">
                        <span style="opacity:0.6;min-width:145px">OpenAPI Specification:</span>
                        <a href="/openapi.json" target="_blank" style="color:var(--primary);text-decoration:none;font-weight:600">/openapi.json</a>
                    </div>
                </div>
            </div>
        </div>
        <div class="modal-card">
            <div class="modal-card-header"><h4>OPERATIONAL NOTES</h4></div>
            <div class="modal-card-body">
                <div style="display:flex;flex-direction:column;gap:10px">
                    <div style="font-size:13px;color:var(--muted);line-height:1.5">1. All endpoints are loaded live from <b>/openapi.json</b>.</div>
                    <div style="font-size:13px;color:var(--muted);line-height:1.5">2. Display values can be overridden from the internal override map.</div>
                    <div style="font-size:13px;color:var(--muted);line-height:1.5">3. Execution follows the live schema plus any manual override you define.</div>
                    <div style="font-size:13px;color:var(--muted);line-height:1.5">4. Unknown override keys are added to <b>Query for GET</b> and <b>Body for non-GET</b> methods.</div>
                </div>
            </div>
        </div>
        <div class="modal-card">
            <div class="modal-card-header"><h4>QUERY EXAMPLES (GET /object-read)</h4></div>
            <div class="modal-card-body">
                <div style="display:flex;flex-direction:column;gap:8px">
                    <div style="font-size:12px;color:var(--muted)">1. <b>Comparison:</b> <code>id==,5</code>, <code>id=&gt;,100</code>, <code>created_at=&gt;=,2024-01-01</code></div>
                    <div style="font-size:12px;color:var(--muted)">2. <b>List & Null:</b> <code>id=in,1|2|3|4</code>, <code>title=is,null</code>, <code>is_active=is distinct from,0</code></div>
                    <div style="font-size:12px;color:var(--muted)">3. <b>Pattern & Range:</b> <code>title=ilike,%python%</code>, <code>rating=between,4.0|5.0</code></div>
                    <div style="font-size:12px;color:var(--muted)">4. <b>Spatial (PostGIS):</b> <code>location=point,80.0|15.0|0|1000</code> <small style="opacity:.6">(lon|lat|min_meter|max_meter)</small></div>
                    <div style="font-size:12px;color:var(--muted)">5. <b>Array:</b> <code>tag=contains,python</code>, <code>tag=overlap,python|sql</code>, <code>tag=any,python</code></div>
                    <div style="font-size:12px;color:var(--muted)">6. <b>Array (Int/Bigint):</b> <code>tag_int=contains,1|2</code>, <code>tag_bigint=overlap,1|2</code></div>
                    <div style="font-size:12px;color:var(--muted)">7. <b>JSONB:</b> <code>metadata=contains,role|admin|str</code>, <code>metadata=exists,is_verified</code></div>
                </div>
            </div>
        </div>
    </div>
</div></div>

<!-- Param Info Modal -->
<div id="paramInfoModal" class="modal"><div class="modal-content" style="max-width:1000px;margin:2% auto">
    <div class="modal-header">
        <h3 id="paramInfoTitle">Parameter Configuration</h3>
        <div class="modal-actions">
            <button type="button" class="icon-btn" id="paramInfoCopyBtn" title="Copy Detail"></button>
            <button type="button" class="icon-btn" id="paramInfoCloseBtn" title="Close"></button>
        </div>
    </div>
    <div id="paramInfoBody" class="modal-body"></div>
</div></div>

<!-- Curl View Modal -->
<div id="curlViewModal" class="modal">
    <div class="modal-content" style="max-width:800px;margin:5% auto">
        <div class="modal-header">
            <h3 id="curlViewTitle">Curl</h3>
            <div class="modal-actions">
                <button type="button" class="icon-btn" id="curlViewCloseBtn" title="Close"></button>
            </div>
        </div>
        <div class="modal-body modal-card-grid vertical-stack" id="curlViewGrid">
            <div class="modal-card" id="curlViewOvrCard" style="display:none">
                <div class="modal-card-header"><h4>OVERRIDE PARAMETERS</h4><button type="button" class="icon-btn" id="curlViewOvrCopy" title="Copy Overrides"></button></div>
                <div class="modal-card-body"><div id="curlViewOvrContent" style="max-height:60vh;overflow-y:auto"></div></div>
            </div>
            <div class="modal-card" id="curlViewCard">
                <div class="modal-card-header"><h4>CURL COMMAND</h4><button type="button" class="icon-btn" id="curlViewCopy" title="Copy Curl"></button></div>
                <div class="modal-card-body"><div id="curlViewContent" style="max-height:60vh;overflow-y:auto"></div></div>
            </div>
            <div class="modal-card" id="curlViewResCard" style="display:none">
                <div class="modal-card-header"><h4>EXPECTED RESPONSE (200)</h4><button type="button" class="icon-btn" id="curlViewResCopy" title="Copy Expected Response"></button></div>
                <div class="modal-card-body"><div id="curlViewResContent" style="max-height:60vh;overflow-y:auto"></div></div>
            </div>
        </div>
    </div>
</div>

<!-- Storage Modal -->
<div id="storageModal" class="modal"><div class="modal-content" style="max-width:540px;margin:2% auto">
    <div class="modal-header">
        <h3>Local Storage</h3>
        <div class="modal-actions">
            <button type="button" class="icon-btn" id="storageCopyAll" title="Copy All State"></button>
            <button type="button" class="icon-btn delete" id="storageResetAll" title="Reset All State"></button>
            <button type="button" class="icon-btn" id="storageCloseBtn" title="Close"></button>
        </div>
    </div>
    <div class="modal-body">
        <div class="modal-card" id="storageCard">
            <div class="modal-card-body" style="padding:0">
                <div id="storageContent"></div>
            </div>
        </div>
    </div>
    </div>
</div>

<!-- Analytics Modal -->
<div id="analyticsModal" class="modal"><div class="modal-content" style="max-width:900px;margin:2% auto">
    <div class="modal-header">
        <h3>Analytics</h3>
        <div class="modal-actions">
            <button type="button" class="icon-btn" id="analyticsCloseBtn" title="Close"></button>
        </div>
    </div>
    <div id="analyticsContent" class="modal-body">
        <div id="analyticsGrid" class="analytics-grid"></div>
    </div>
    </div>
</div>

<!-- Popups -->
<div id="cellPop" class="cell-pop"><span id="cellPopTxt"></span><button class="cell-pop-copy" id="cellPopCopy" title="Copy"></button></div>
`;

/**
 * @description Injects the modal HTML templates into the document body.
 */
function injectModals() {
    const container = document.createElement('div');
    container.id = 'modalContainer';
    container.innerHTML = MODAL_HTML;
    document.body.appendChild(container);
}
