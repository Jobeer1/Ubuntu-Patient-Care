(function(){
    window.NASIntegration = window.NASIntegration || {};
    window.NASIntegration._uiParts = window.NASIntegration._uiParts || {};

    // Small helper to safely access ports part
    function ports() { return window.NASIntegration._uiParts && window.NASIntegration._uiParts.ports ? window.NASIntegration._uiParts.ports : null; }
    function utils() { return window.NASIntegration._uiParts && window.NASIntegration._uiParts.utils ? window.NASIntegration._uiParts.utils : null; }

    function formatScanResult(scanResult, ip) {
        if (!scanResult) return '<p class="text-muted">❌ No scan result available</p>';
        const open = scanResult.open_ports || [];
        const meta = ports() ? ports().computeNasConfidence(open) : { score: 0, matches: [] };
        let html = `<div class="scan-result-card"><div class="d-flex justify-content-between align-items-center"><h4 class="mb-0">🔍 Scan Results: ${ip}</h4><div><span class="badge bg-secondary">Open ports: ${open.length}</span><span class="ms-2 ${meta.score>=60?'badge bg-success':meta.score>=30?'badge bg-warning text-dark':'badge bg-secondary'}">NAS Confidence: ${meta.score}%</span></div></div><div class="mt-2 table-responsive"><table class="table table-sm table-striped"><thead><tr><th>Port</th><th>Protocol</th><th>Service</th><th>Info</th></tr></thead><tbody>`;
        open.forEach(p => {
            const portNum = ports() ? ports().getPortNumber(p) : (p.port || p.port_number || p.number || '-');
            const portText = (typeof portNum !== 'undefined' && portNum !== null) ? portNum : '-';
            const protoText = p.protocol || 'tcp';
            const svcText = p.service || (ports() ? ports().getDefaultServiceName(portText) : '') || '';
            const infoText = p.info || '';
            html += `<tr><td>${portText}</td><td>${protoText}</td><td>${svcText}</td><td>${infoText}</td></tr>`;
        });
        html += `</tbody></table></div>${(open.length>0?`<p class="text-muted small">${open.map(p=>`${ports()?ports().getPortNumber(p)||'-':'-'} / ${p.protocol||'tcp'} ${p.service||''}`).join(', ')}</p>`:'')}${meta.matches.length?`<p class="small mt-2"><strong>Detected:</strong> ${meta.matches.join(', ')}</p>`:''}</div>`;
        return html;
    }

    function formatScanAccordion(scanResult, ip){
        const open = scanResult.open_ports || [];
        const meta = ports() ? ports().computeNasConfidence(open) : { score: 0, matches: [] };
        let html = `<tr class="scan-accordion-row" data-ip="${ip}-scan"><td colspan="7" class="scan-accordion-cell"><div class="scan-accordion"><div class="d-flex justify-content-between align-items-center mb-2"><div><strong>Scan Results for ${ip}</strong> - Open ports: ${open.length}</div><div><span class="badge bg-secondary">NAS Confidence: ${meta.score}%</span></div></div><div class="table-responsive"><table class="table table-sm table-striped mb-0"><thead><tr><th>Port</th><th>Protocol</th><th>Service</th><th>Info</th></tr></thead><tbody>`;
        open.forEach(p=>{
            const pnum = ports()?ports().getPortNumber(p):null;
            const portText = (typeof pnum!=='undefined' && pnum!==null)?pnum:'-';
            const protoText = p.protocol||'tcp';
            const svcText = p.service || (ports()?ports().getDefaultServiceName(portText):'') || '';
            const infoText = p.info||'';
            html += `<tr><td>${portText}</td><td>${protoText}</td><td>${svcText}</td><td>${infoText}</td></tr>`;
        });
        html += `</tbody></table></div></div></td></tr>`;
        return html;
    }

    // Small HTML escaper
    function esc(s){ if (s===null || typeof s === 'undefined') return ''; return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }

    function _normalizeDevice(d){
        return {
            ip: d.ip_address || d.ip || d.ipAddress || d.ipAddressV4 || '',
            hostname: d.hostname || d.name || d.host || 'Unknown',
            mac: d.mac_address || d.mac || d.hardware_address || 'Unknown',
            manufacturer: d.manufacturer || d.vendor || 'Unknown',
            response_time: (d.response_time || (d.ping_result && d.ping_result.response_time) || (d.reachable? 'OK' : 'Offline')),
            reachable: (typeof d.reachable !== 'undefined') ? !!d.reachable : !!(d.response_time || (d.ping_result && d.ping_result.response_time)),
            source: d.source || d.origin || ''
        };
    }

    function formatArpTable(devices, totalEntries) {
    try { console.debug('formatArpTable called, devices:', (devices||[]).length, 'totalEntries:', totalEntries); } catch(e){}
        devices = devices || [];
        const header = `<div class="d-flex justify-content-between align-items-center mb-2"><h4 class="mb-0">📋 ARP Table</h4><div class="text-muted">Total: ${totalEntries || devices.length}</div></div>`;
        let html = header + '<div class="table-responsive"><table class="table table-sm table-hover"><thead><tr><th>IP</th><th>Hostname</th><th>MAC</th><th>Vendor</th><th>Response</th><th>NAS</th><th>Actions</th></tr></thead><tbody>';
        devices.forEach(d => {
            const dev = _normalizeDevice(d);
            const confidenceMeta = ports() ? ports().computeNasConfidence(d.open_ports || d.ports || []) : { score: 0, matches: [] };
            const conf = confidenceMeta.score || 0;
            const confCls = conf >= 60 ? 'badge bg-success' : conf >= 30 ? 'badge bg-warning text-dark' : 'badge bg-secondary';
            html += `<tr class="device-row ${dev.reachable? 'online':'offline'}" data-ip="${esc(dev.ip)}"><td class="ip-cell"><code>${esc(dev.ip)}</code></td><td class="hostname-cell">${esc(dev.hostname)}</td><td class="mac-cell"><code>${esc(dev.mac)}</code></td><td class="vendor-cell">${esc(dev.manufacturer)}</td><td class="response-cell">${esc(dev.response_time || (dev.reachable? 'OK':'Offline'))}</td><td class="confidence-cell"><span class="${confCls}">${conf}%</span></td><td class="actions-cell"><button class="btn btn-sm btn-outline-primary" onclick="window.NASIntegration.devices.scanDevice('${esc(dev.ip)}')">Scan</button> <button class="btn btn-sm btn-outline-secondary" onclick="window.NASIntegration.devices.pingDevice('${esc(dev.ip)}')">Ping</button> <button class="btn btn-sm btn-outline-success" onclick="window.NASIntegration.devices.connectToDevice('${esc(dev.ip)}')">Connect</button> <button class="btn btn-sm btn-outline-warning" onclick="window.NASIntegration.devices.renameDevice('${esc(dev.ip)}', '${esc(dev.hostname)}')">Rename</button> <button class="btn btn-sm btn-outline-danger" onclick="window.NASIntegration.devices.removeDevice('${esc(dev.ip)}', '${esc(dev.hostname)}')">Remove</button></td></tr>`;
        });
        html += '</tbody></table></div>';
        return html;
    }

    function formatRangePingResults(results, statistics, range) {
    try { console.debug('formatRangePingResults called, results:', (results||[]).length, 'stats:', statistics); } catch(e){}
        const title = `<div class="d-flex justify-content-between align-items-center mb-2"><h4 class="mb-0">🎯 Ping Range ${esc(range || '')}</h4><div class="text-muted">Online: ${statistics? statistics.online_count : 0}</div></div>`;
        let html = title + '<div class="table-responsive"><table class="table table-sm table-striped"><thead><tr><th>IP</th><th>Hostname</th><th>Response</th><th>Source</th><th>Actions</th></tr></thead><tbody>';
        (results || []).forEach(r => {
            const dev = _normalizeDevice(r);
            html += `<tr class="device-row ${dev.reachable? 'online':'offline'}" data-ip="${esc(dev.ip)}"><td><code>${esc(dev.ip)}</code></td><td>${esc(dev.hostname)}</td><td class="response-cell">${esc(dev.response_time || (dev.reachable? 'OK':'Offline'))}</td><td>${esc(dev.source)}</td><td><button class="btn btn-sm btn-outline-primary" onclick="window.NASIntegration.devices.scanDevice('${esc(dev.ip)}')">Scan</button> <button class="btn btn-sm btn-outline-secondary" onclick="window.NASIntegration.devices.pingDevice('${esc(dev.ip)}')">Ping</button> <button class="btn btn-sm btn-outline-warning" onclick="window.NASIntegration.devices.renameDevice('${esc(dev.ip)}', '${esc(dev.hostname)}')">Rename</button> <button class="btn btn-sm btn-outline-danger" onclick="window.NASIntegration.devices.removeDevice('${esc(dev.ip)}', '${esc(dev.hostname)}')">Remove</button></td></tr>`;
        });
        html += '</tbody></table></div>';
        return html;
    }

    function formatPingResult(p) {
    try { console.debug('formatPingResult called for:', p && (p.ip_address||p.ip||p.ipAddress)); } catch(e){}
        if (!p) return '<p class="text-muted">No ping result</p>';
        const dev = _normalizeDevice(p);
        return `<div class="card"><div class="card-body"><h5 class="card-title">Ping Result for ${esc(dev.ip)}</h5><p class="card-text">Hostname: ${esc(dev.hostname)}<br>Response: ${esc(dev.response_time || (dev.reachable? 'OK':'Offline'))}</p></div></div>`;
    }

    function formatDiscoveredDevices(devices) {
    try { console.debug('formatDiscoveredDevices called, count:', (devices||[]).length); } catch(e){}
        devices = devices || [];
        const header = `<div class="d-flex justify-content-between align-items-center mb-2"><h4 class="mb-0">🔎 Discovered Devices</h4><div class="text-muted">Found: ${devices.length}</div></div>`;
        let html = header + '<div class="table-responsive"><table class="table table-sm table-hover"><thead><tr><th>IP</th><th>Hostname</th><th>MAC</th><th>Vendor</th><th>Response</th><th>NAS</th><th>Actions</th></tr></thead><tbody>';
        devices.forEach(d => {
            const dev = _normalizeDevice(d);
            const meta = ports() ? ports().computeNasConfidence(d.open_ports || d.ports || []) : { score:0, matches:[] };
            const conf = meta.score || 0;
            const confCls = conf >= 60 ? 'badge bg-success' : conf >= 30 ? 'badge bg-warning text-dark' : 'badge bg-secondary';
            html += `<tr class="device-row ${dev.reachable? 'online':'offline'}" data-ip="${esc(dev.ip)}"><td class="ip-cell"><code>${esc(dev.ip)}</code></td><td class="hostname-cell">${esc(dev.hostname)}</td><td class="mac-cell"><code>${esc(dev.mac)}</code></td><td class="vendor-cell">${esc(dev.manufacturer)}</td><td class="response-cell">${esc(dev.response_time || (dev.reachable? 'OK':'Offline'))}</td><td class="confidence-cell"><span class="${confCls}">${conf}%</span></td><td class="actions-cell"><button class="btn btn-sm btn-outline-primary" onclick="window.NASIntegration.devices.scanDevice('${esc(dev.ip)}')">Scan</button> <button class="btn btn-sm btn-outline-secondary" onclick="window.NASIntegration.devices.pingDevice('${esc(dev.ip)}')">Ping</button> <button class="btn btn-sm btn-outline-warning" onclick="window.NASIntegration.devices.renameDevice('${esc(dev.ip)}', '${esc(dev.hostname)}')">Rename</button> <button class="btn btn-sm btn-outline-danger" onclick="window.NASIntegration.devices.removeDevice('${esc(dev.ip)}', '${esc(dev.hostname)}')">Remove</button></td></tr>`;
        });
        html += '</tbody></table></div>';
        return html;
    }

    function formatStorageStatus(s) {
    try { console.debug('formatStorageStatus called', s); } catch(e){}
        if (!s) return '<p class="text-muted">No storage status</p>';
        const used = s.used_bytes || s.used || 0;
        const total = s.total_bytes || s.total || 0;
        const utilsPart = utils();
        const usedText = utilsPart ? utilsPart.formatBytes(used) : (used+ ' bytes');
        const totalText = utilsPart ? utilsPart.formatBytes(total) : (total + ' bytes');
        return `<div class="card"><div class="card-body"><h5 class="card-title">Storage Status</h5><p class="card-text">Used: ${usedText} / ${totalText}</p></div></div>`;
    }

    function formatIndexingStatus(s) {
        if (!s) return '<p class="text-muted">No indexing activity</p>';
        const state = s.state || s.status || 'unknown';
        const progress = typeof s.progress === 'number' ? s.progress : (s.percent || 0);
        const details = s.details || s.message || '';
        const bar = `<div class="progress"><div class="progress-bar" role="progressbar" style="width: ${Math.max(0, Math.min(100, progress))}%">${Math.round(progress)}%</div></div>`;
        return `<div class="indexing-status"><h5>Indexing: ${esc(state)}</h5>${bar}<p class="small text-muted">${esc(details)}</p></div>`;
    }

    // Expose formatters
    window.NASIntegration._uiParts.formatters = { formatScanResult, formatScanAccordion, formatArpTable, formatRangePingResults, formatPingResult, formatDiscoveredDevices, formatStorageStatus, formatIndexingStatus };
    console.log('ui-helpers/formatters loaded');
})();
