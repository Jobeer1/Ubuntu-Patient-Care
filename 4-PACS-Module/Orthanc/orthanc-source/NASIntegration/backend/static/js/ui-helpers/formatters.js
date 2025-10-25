(function(){
    window.NASIntegration = window.NASIntegration || {};
    window.NASIntegration._uiParts = window.NASIntegration._uiParts || {};

    // Small helper to safely access ports part
    function ports() { return window.NASIntegration._uiParts && window.NASIntegration._uiParts.ports ? window.NASIntegration._uiParts.ports : null; }
    function utils() { return window.NASIntegration._uiParts && window.NASIntegration._uiParts.utils ? window.NASIntegration._uiParts.utils : null; }

    function formatScanResult(scanResult, ip) {
        if (!scanResult) return '<div class="alert alert-warning"><i class="fas fa-exclamation-triangle me-2"></i>No scan result available</div>';
        const open = scanResult.open_ports || [];
        // Prefer backend-provided NAS confidence score when present
        let meta = { score: 0, matches: [] };
        if (scanResult && (typeof scanResult.nas_confidence_score !== 'undefined' || typeof scanResult.nas_confidence !== 'undefined' || typeof scanResult.score !== 'undefined')) {
            const serverScore = (typeof scanResult.nas_confidence_score !== 'undefined') ? scanResult.nas_confidence_score :
                                (typeof scanResult.nas_confidence !== 'undefined') ? scanResult.nas_confidence :
                                scanResult.score;
            meta.score = Number(serverScore) || 0;
            // server may also include descriptive matches
            meta.matches = scanResult.nas_matches || scanResult.matches || [];
        } else {
            meta = ports() ? ports().computeNasConfidence(open) : meta;
        }
        
        let html = `<div class="card border-primary shadow-sm mb-3">
            <div class="card-header bg-primary text-white">
                <div class="d-flex justify-content-between align-items-center">
                    <h5 class="mb-0"><i class="fas fa-search me-2"></i>Scan Results: <code class="text-light">${ip}</code></h5>
                    <div>
                        <span class="badge bg-light text-primary me-2">
                            <i class="fas fa-door-open me-1"></i>${open.length} Open Ports
                        </span>
                        <span class="badge ${meta.score>=80?'bg-success':meta.score>=60?'bg-info':meta.score>=30?'bg-warning text-dark':'bg-secondary'}">
                            <i class="fas fa-stethoscope me-1"></i>${meta.score}% Medical Device
                        </span>
                    </div>
                </div>
            </div>
            <div class="card-body">`;
            
        if (open.length === 0) {
            html += '<div class="text-center text-muted py-3"><i class="fas fa-shield-alt fa-2x mb-2"></i><p>No open ports found</p></div>';
        } else {
            html += '<div class="table-responsive"><table class="table table-hover"><thead class="table-light"><tr><th><i class="fas fa-hashtag text-muted"></i> Port</th><th><i class="fas fa-exchange-alt text-muted"></i> Protocol</th><th><i class="fas fa-cogs text-muted"></i> Service</th><th><i class="fas fa-info-circle text-muted"></i> Details</th></tr></thead><tbody>';
            open.forEach(p => {
                const portNum = ports() ? ports().getPortNumber(p) : (p.port || p.port_number || p.number || '-');
                const portText = (typeof portNum !== 'undefined' && portNum !== null) ? portNum : '-';
                const protoText = p.protocol || 'tcp';
                const svcText = p.service || (ports() ? ports().getDefaultServiceName(portText) : '') || '';
                const infoText = p.info || '';
                const isMedical = [104, 11112, 8042, 80, 443].includes(parseInt(portText));
                const rowClass = isMedical ? 'table-warning' : '';
                
                html += `<tr class="${rowClass}">
                    <td><code class="text-primary fw-bold">${portText}</code></td>
                    <td><span class="badge bg-secondary">${protoText.toUpperCase()}</span></td>
                    <td>
                        ${svcText ? `<span class="badge bg-info">${svcText}</span>` : '<span class="text-muted">Unknown</span>'}
                        ${isMedical ? '<i class="fas fa-hospital text-success ms-1" title="Medical Device Port"></i>' : ''}
                    </td>
                    <td>${infoText || '<span class="text-muted">No details</span>'}</td>
                </tr>`;
            });
            html += '</tbody></table></div>';
        }
        
        if (meta.matches.length > 0) {
            html += `<div class="mt-3">
                <h6 class="text-success"><i class="fas fa-check-circle me-2"></i>Detected Services:</h6>
                <div class="d-flex flex-wrap gap-2">`;
            meta.matches.forEach(match => {
                html += `<span class="badge bg-success"><i class="fas fa-stethoscope me-1"></i>${match}</span>`;
            });
            html += '</div></div>';
        }
        
        html += '</div></div>';
        return html;
    }

    function formatScanAccordion(scanResult, ip){
        const open = scanResult.open_ports || [];
        // Prefer backend score
        let meta = { score: 0, matches: [] };
        if (scanResult && (typeof scanResult.nas_confidence_score !== 'undefined' || typeof scanResult.nas_confidence !== 'undefined' || typeof scanResult.score !== 'undefined')) {
            const serverScore = (typeof scanResult.nas_confidence_score !== 'undefined') ? scanResult.nas_confidence_score :
                                (typeof scanResult.nas_confidence !== 'undefined') ? scanResult.nas_confidence :
                                scanResult.score;
            meta.score = Number(serverScore) || 0;
            meta.matches = scanResult.nas_matches || scanResult.matches || [];
        } else {
            meta = ports() ? ports().computeNasConfidence(open) : meta;
        }
        let html = `<tr class="scan-accordion-row" data-ip="${ip}-scan">
            <td colspan="7" class="scan-accordion-cell">
                <div class="card border-info mb-0">
                    <div class="card-header bg-info text-white py-2">
                        <div class="d-flex justify-content-between align-items-center">
                            <h6 class="mb-0">
                                <i class="fas fa-search me-2"></i>
                                Scan Results: <code class="text-light">${ip}</code>
                            </h6>
                            <div>
                                <span class="badge bg-light text-info me-2">
                                    <i class="fas fa-door-open me-1"></i>${open.length} Ports
                                </span>
                                <span class="badge ${meta.score>=80?'bg-success':meta.score>=60?'bg-warning text-dark':'bg-secondary'}">
                                    <i class="fas fa-stethoscope me-1"></i>${meta.score}%
                                </span>
                            </div>
                        </div>
                    </div>
                    <div class="card-body p-2">`;
                    
        if (open.length === 0) {
            html += '<div class="text-center text-muted py-2"><i class="fas fa-shield-alt fa-lg mb-1"></i><small><br>No open ports found</small></div>';
        } else {
            html += '<div class="table-responsive"><table class="table table-sm table-hover mb-0"><thead class="table-light"><tr><th><i class="fas fa-hashtag text-muted"></i> Port</th><th><i class="fas fa-exchange-alt text-muted"></i> Protocol</th><th><i class="fas fa-cogs text-muted"></i> Service</th><th><i class="fas fa-info-circle text-muted"></i> Info</th></tr></thead><tbody>';
            open.forEach(p=>{
                const pnum = ports()?ports().getPortNumber(p):null;
                const portText = (typeof pnum!=='undefined' && pnum!==null)?pnum:'-';
                const protoText = p.protocol||'tcp';
                const svcText = p.service || (ports()?ports().getDefaultServiceName(portText):'') || '';
                const infoText = p.info||'';
                const isMedical = [104, 11112, 8042, 80, 443].includes(parseInt(portText));
                const rowClass = isMedical ? 'table-warning' : '';
                
                html += `<tr class="${rowClass}">
                    <td><code class="text-primary">${portText}</code></td>
                    <td><span class="badge bg-secondary">${protoText.toUpperCase()}</span></td>
                    <td>
                        ${svcText ? `<span class="badge bg-info">${svcText}</span>` : '<span class="text-muted">Unknown</span>'}
                        ${isMedical ? '<i class="fas fa-hospital text-success ms-1"></i>' : ''}
                    </td>
                    <td><small>${infoText || '<span class="text-muted">No details</span>'}</small></td>
                </tr>`;
            });
            html += '</tbody></table></div>';
        }
        
        if (meta.matches.length > 0) {
            html += `<div class="mt-2">
                <small class="text-success fw-bold"><i class="fas fa-check-circle me-1"></i>Detected:</small>
                <div class="d-flex flex-wrap gap-1 mt-1">`;
            meta.matches.forEach(match => {
                html += `<span class="badge bg-success"><i class="fas fa-stethoscope me-1"></i>${match}</span>`;
            });
            html += '</div></div>';
        }
        
        html += '</div></div></td></tr>';
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
        const header = `<div class="d-flex justify-content-between align-items-center mb-3">
            <h4 class="mb-0 text-primary"><i class="fas fa-network-wired me-2"></i>Network Devices</h4>
            <div class="text-muted small">Total: ${totalEntries || devices.length} devices</div>
        </div>`;
        let html = header + '<div class="table-responsive"><table class="table table-hover shadow-sm"><thead class="table-light"><tr><th><i class="fas fa-globe text-muted"></i> IP Address & Last Scan</th><th><i class="fas fa-server text-muted"></i> Device Info</th><th><i class="fas fa-clock text-muted"></i> Status & Scans</th><th><i class="fas fa-cogs text-muted"></i> Medical Device</th><th><i class="fas fa-tools text-muted"></i> Actions</th></tr></thead><tbody>';
        devices.forEach(d => {
            const dev = _normalizeDevice(d);
            const confidenceMeta = ports() ? ports().computeNasConfidence(d.open_ports || d.ports || []) : { score: 0, matches: [] };
            const conf = confidenceMeta.score || 0;
            const confCls = conf >= 80 ? 'badge bg-success' : conf >= 60 ? 'badge bg-info' : conf >= 30 ? 'badge bg-warning text-dark' : 'badge bg-secondary';
            const statusIcon = dev.reachable ? '<i class="fas fa-circle text-success me-1"></i>' : '<i class="fas fa-circle text-danger me-1"></i>';
            const statusText = dev.reachable ? (dev.response_time || 'Online') : 'Offline';
            const deviceIcon = conf >= 60 ? '<i class="fas fa-hospital text-primary me-1"></i>' : '<i class="fas fa-desktop text-muted me-1"></i>';
            
            // Get additional device info from database if available
            const manufacturer = d.manufacturer || d.vendor || 'Unknown';
            const deviceType = d.device_type || d.os_fingerprint || 'Unknown';
            const lastScan = d.last_updated ? new Date(d.last_updated).toLocaleString() : 'Never';
            const scanCount = d.scan_count || 0;
            
            html += `<tr class="device-row ${dev.reachable? 'table-success':'table-light'}" data-ip="${esc(dev.ip)}" style="border-left: 4px solid ${dev.reachable ? '#28a745' : '#dc3545'};">
                <td class="ip-cell">
                    <div class="d-flex align-items-center">
                        <i class="fas fa-network-wired text-primary me-2"></i>
                        <code class="text-primary fw-bold">${esc(dev.ip)}</code>
                    </div>
                    <small class="text-muted">${lastScan}</small>
                </td>
                <td class="hostname-cell">
                    <div class="d-flex align-items-center">
                        ${deviceIcon}
                        <div>
                            <div class="fw-bold">${esc(dev.hostname)}</div>
                            <small class="text-muted">${esc(manufacturer)}</small>
                            <br>
                            <small class="text-info">${esc(deviceType)}</small>
                        </div>
                    </div>
                </td>
                <td class="response-cell">
                    <div class="d-flex align-items-center">
                        ${statusIcon}
                        <span class="${dev.reachable ? 'text-success fw-bold' : 'text-danger'}">${statusText}</span>
                    </div>
                    <small class="text-muted">Scans: ${scanCount}</small>
                </td>
                <td class="confidence-cell">
                    <div class="d-flex align-items-center">
                        <span class="${confCls} me-2">
                            <i class="fas fa-stethoscope me-1"></i>${conf}%
                        </span>
                        ${conf >= 60 ? '<i class="fas fa-check-circle text-success"></i>' : '<i class="fas fa-question-circle text-muted"></i>'}
                    </div>
                </td>
                <td class="actions-cell">
                    <div class="btn-group btn-group-sm d-flex flex-wrap gap-1" role="group">
                                <button class="btn btn-outline-primary btn-action" onclick="window.NASIntegration.devices.scanDevice('${esc(dev.ip)}')" title="Scan" aria-label="Scan device">
                                    <i class="fas fa-search"></i>
                                </button>
                                <button class="btn btn-outline-secondary btn-action" onclick="window.NASIntegration.devices.pingDevice('${esc(dev.ip)}')" title="Ping" aria-label="Ping device">
                                    <i class="fas fa-wifi"></i>
                                </button>
                                <button class="btn btn-outline-success btn-action" onclick="window.NASIntegration.devices.connectToDevice('${esc(dev.ip)}')" title="Connect" aria-label="Connect to device">
                                    <i class="fas fa-plug"></i>
                                </button>
                                <button class="btn btn-outline-secondary btn-action" onclick="window.NASIntegration.devices.disconnectDevice('${esc(dev.ip)}')" title="Disconnect" aria-label="Disconnect device">
                                    <i class="fas fa-unlink"></i>
                                </button>
                                <button class="btn btn-outline-warning btn-action" onclick="window.NASIntegration.devices.renameDevice('${esc(dev.ip)}', '${esc(dev.hostname)}')" title="Rename" aria-label="Rename device">
                                    <i class="fas fa-pen"></i>
                                </button>
                                <button class="btn btn-outline-danger btn-action" onclick="window.NASIntegration.devices.removeDevice('${esc(dev.ip)}', '${esc(dev.hostname)}')" title="Remove" aria-label="Remove device">
                                    <i class="fas fa-trash"></i>
                                </button>
                    </div>
                </td>
            </tr>`;
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
            html += `<tr class="device-row ${dev.reachable? 'online':'offline'}" data-ip="${esc(dev.ip)}"><td><code>${esc(dev.ip)}</code></td><td>${esc(dev.hostname)}</td><td class="response-cell">${esc(dev.response_time || (dev.reachable? 'OK':'Offline'))}</td><td>${esc(dev.source)}</td><td><button class="btn btn-sm btn-outline-primary" onclick="window.NASIntegration.devices.scanDevice('${esc(dev.ip)}')"><i class=\"fas fa-search me-1\"></i>Scan</button> <button class="btn btn-sm btn-outline-secondary" onclick="window.NASIntegration.devices.pingDevice('${esc(dev.ip)}')"><i class=\"fas fa-broadcast-tower me-1\"></i>Ping</button> <button class="btn btn-sm btn-outline-warning" onclick="window.NASIntegration.devices.renameDevice('${esc(dev.ip)}', '${esc(dev.hostname)}')"><i class=\"fas fa-edit me-1\"></i>Rename</button> <button class="btn btn-sm btn-outline-danger" onclick="window.NASIntegration.devices.removeDevice('${esc(dev.ip)}', '${esc(dev.hostname)}')"><i class=\"fas fa-trash me-1\"></i>Remove</button></td></tr>`;
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
        let html = header + '<div class="table-responsive"><table class="table table-sm table-hover"><thead><tr><th>IP</th><th>Hostname</th><th>MAC</th><th>Vendor</th><th>Response</th><th>Medical Device</th><th>Actions</th></tr></thead><tbody>';
        devices.forEach(d => {
            const dev = _normalizeDevice(d);
            // Prefer server-provided confidence if present on device object
            const meta = (d && (typeof d.nas_confidence_score !== 'undefined' || typeof d.nas_confidence !== 'undefined' || typeof d.score !== 'undefined')) ?
                            { score: Number(d.nas_confidence_score || d.nas_confidence || d.score) || 0, matches: d.nas_matches || d.matches || [] } :
                            (ports() ? ports().computeNasConfidence(d.open_ports || d.ports || []) : { score:0, matches:[] });
            const conf = meta.score || 0;
            const confCls = conf >= 60 ? 'badge bg-success' : conf >= 30 ? 'badge bg-warning text-dark' : 'badge bg-secondary';
            html += `<tr class="device-row ${dev.reachable? 'online':'offline'}" data-ip="${esc(dev.ip)}"><td class="ip-cell"><code>${esc(dev.ip)}</code></td><td class="hostname-cell">${esc(dev.hostname)}</td><td class="mac-cell"><code>${esc(dev.mac)}</code></td><td class="vendor-cell">${esc(dev.manufacturer)}</td><td class="response-cell">${esc(dev.response_time || (dev.reachable? 'OK':'Offline'))}</td><td class="confidence-cell"><span class="${confCls}">${conf}%</span></td><td class="actions-cell"><button class="btn btn-sm btn-outline-primary" onclick="window.NASIntegration.devices.scanDevice('${esc(dev.ip)}')"><i class=\"fas fa-search me-1\"></i>Scan</button> <button class="btn btn-sm btn-outline-secondary" onclick="window.NASIntegration.devices.pingDevice('${esc(dev.ip)}')"><i class=\"fas fa-broadcast-tower me-1\"></i>Ping</button> <button class="btn btn-sm btn-outline-warning" onclick="window.NASIntegration.devices.renameDevice('${esc(dev.ip)}', '${esc(dev.hostname)}')"><i class=\"fas fa-edit me-1\"></i>Rename</button> <button class="btn btn-sm btn-outline-danger" onclick="window.NASIntegration.devices.removeDevice('${esc(dev.ip)}', '${esc(dev.hostname)}')"><i class=\"fas fa-trash me-1\"></i>Remove</button></td></tr>`;
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
        const usedText = utilsPart ? utilsPart.formatBytes(used) : (used + ' bytes');
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
