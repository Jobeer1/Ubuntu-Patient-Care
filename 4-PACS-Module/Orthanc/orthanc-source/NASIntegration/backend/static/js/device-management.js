/* Device Management Module - clean, single-source implementation
   - Normalizes ping results to prefer 'reachable' boolean
   - Avoids showing 'N/A' as online
   - Provides UI helpers for updating table rows */

'use strict';

// Normalize ping result into { reachable: bool, response_time: string|null }
function _normalizePingResult(result) {
    if (!result) return { reachable: false, response_time: null };

    let rt = result.response_time;
    if (typeof rt === 'number') rt = `${rt}ms`;
    rt = (rt || '').toString();
    const rtLower = rt.toLowerCase();

    // Treat these as invalid / unknown response times unless the backend indicates ARP
    const invalidRt = ['n/a', 'timeout', 'error', 'offline', ''].includes(rtLower);
    const rawReachable = !!result.reachable;
    // If backend omitted a reachable flag but returned a valid response_time, treat as reachable
    const hasValidResponseTime = !!rt && !invalidRt;
    const effectiveReachable = rawReachable || hasValidResponseTime;
    const display = effectiveReachable ? (rtLower === 'arp' ? 'OK' : (rt || 'OK')) : null;

    return { reachable: effectiveReachable, response_time: display };
}

function _updateResponseCell(ip, normalized) {
    try {
        const row = document.querySelector(`tr[data-ip="${ip}"]`);
        if (!row) return;
        const cell = row.querySelector('.response-cell');
        if (!cell) return;

        if (normalized.reachable) {
            cell.textContent = normalized.response_time || 'OK';
            cell.style.color = 'green';
            cell.style.fontWeight = 'bold';
        } else {
            cell.textContent = 'Offline';
            cell.style.color = 'red';
            cell.style.fontWeight = 'bold';
        }
    } catch (e) {
        // Non-fatal UI update error
    }
}

async function renameDevice(ip, currentHostname) {
    const newName = prompt(`Rename device ${currentHostname || ip}:`, currentHostname || '');
    if (!newName || newName.trim() === '') {
        window.NASIntegration.core.showMessage('Device name cannot be empty', 'warning');
        return;
    }
    if (newName === currentHostname) return;

    try {
        const row = document.querySelector(`tr[data-ip="${ip}"]`);
        let mac = null;
        if (row) {
            const macEl = row.querySelector('.mac-cell code');
            if (macEl) mac = macEl.textContent.trim();
        }

        const payload = { ip_address: ip, new_name: newName.trim() };
        if (mac && mac !== 'Unknown') payload.mac_address = mac;

        const res = await window.NASIntegration.core.makeAPIRequest('/api/nas/rename-device', { method: 'POST', body: JSON.stringify(payload) });
        if (res.success) {
            window.NASIntegration.core.showMessage(`✅ Device renamed to "${newName}"`, 'success');
            if (row) {
                const hostCell = row.querySelector('.hostname-cell');
                if (hostCell) hostCell.textContent = newName;
            }
        } else {
            window.NASIntegration.core.showMessage(`❌ Rename failed: ${res.error}`, 'error');
        }
    } catch (err) {
        window.NASIntegration.core.showMessage(`❌ Rename error: ${err.message}`, 'error');
    }
}

async function removeDevice(ip, hostname) {
    if (!confirm(`Remove device ${hostname || ip}?`)) return;
    try {
        const res = await window.NASIntegration.core.makeAPIRequest('/api/nas/remove-device', { method: 'POST', body: JSON.stringify({ ip_address: ip }) });
        if (res.success) {
            window.NASIntegration.core.showMessage(`✅ Removed ${hostname || ip}`, 'success');
            // Best-effort refresh
            try { if (window.NASIntegration.network && window.NASIntegration.core.getLastResultType) {
                const t = window.NASIntegration.core.getLastResultType();
                if (t === 'arp_table' && window.NASIntegration.network.getArpTable) await window.NASIntegration.network.getArpTable();
                else if (t === 'enhanced_discovery' && window.NASIntegration.network.enhancedDiscover) await window.NASIntegration.network.enhancedDiscover(true, false);
            }} catch (_) {}
        } else {
            window.NASIntegration.core.showMessage(`❌ Remove failed: ${res.error}`, 'error');
        }
    } catch (err) {
        window.NASIntegration.core.showMessage(`❌ Remove error: ${err.message}`, 'error');
    }
}

async function testDeviceConnectivity(ip) {
    if (!ip) return window.NASIntegration.core.showMessage('No IP provided', 'warning');
    window.NASIntegration.core.showMessage(`🔍 Testing ${ip}...`, 'info');
    try {
        const res = await window.NASIntegration.core.makeAPIRequest('/api/nas/ping', { method: 'POST', body: JSON.stringify({ ip_address: ip, timeout: 5 }) });
        if (res.success && res.ping_result) {
            const n = _normalizePingResult(res.ping_result);
            if (n.reachable) window.NASIntegration.core.showMessage(`✅ ${ip} reachable (${n.response_time || 'OK'})`, 'success');
            else window.NASIntegration.core.showMessage(`❌ ${ip} unreachable`, 'error');
        } else {
            window.NASIntegration.core.showMessage(`❌ Test failed: ${res.error || 'Unknown'}`, 'error');
        }
    } catch (err) {
        window.NASIntegration.core.showMessage(`❌ Test error: ${err.message}`, 'error');
    }
}

async function pingDevice(ip) {
    if (!ip) return window.NASIntegration.core.showMessage('No IP provided', 'warning');
    window.NASIntegration.core.showMessage(`🏓 Pinging ${ip}...`, 'info');
    try {
        const res = await window.NASIntegration.core.makeAPIRequest('/api/nas/ping', { method: 'POST', body: JSON.stringify({ ip_address: ip, timeout: 3 }) });
        if (res.success && res.ping_result) {
            const n = _normalizePingResult(res.ping_result);
            if (n.reachable) window.NASIntegration.core.showMessage(`✅ Ping success: ${ip} (${n.response_time || 'OK'})`, 'success');
            else window.NASIntegration.core.showMessage(`❌ Ping failed: ${ip}`, 'error');
            _updateResponseCell(ip, n);
        } else {
            window.NASIntegration.core.showMessage(`❌ Ping error: ${res.error || 'Unknown'}`, 'error');
        }
    } catch (err) {
        window.NASIntegration.core.showMessage(`❌ Ping error: ${err.message}`, 'error');
    }
}

async function connectToDevice(ip) {
    if (!ip) return window.NASIntegration.core.showMessage('No IP provided', 'warning');
    window.NASIntegration.core.showMessage(`🔌 Connecting to ${ip}...`, 'info');
    try {
        // Allow optional credentials from indexing UI to be passed when connecting
        const username = document.getElementById('indexUsername')?.value || undefined;
        const password = document.getElementById('indexPassword')?.value || undefined;
        const sharePath = document.getElementById('indexPath')?.value || undefined;
        const payload = { ip_address: ip };
        if (username) payload.username = username;
        if (password) payload.password = password;
        if (sharePath) payload.share_path = sharePath;
        const res = await window.NASIntegration.core.makeAPIRequest('/api/nas/connect-device', { method: 'POST', body: JSON.stringify(payload) });
        if (res.success) {
            const info = res.connection_info || {};
            const protocols = info.protocols || [];
            const services = info.services || [];
            const modalHtml = `...`; // keep minimal - UI created elsewhere
            window.NASIntegration.core.showMessage(`✅ Connected to ${ip}`, 'success');
            try {
                // Mark device row as connected and add a badge
                const row = document.querySelector(`tr[data-ip="${ip}"]`);
                if (row) {
                    row.classList.add('nas-connected');
                    const actions = row.querySelector('.actions-cell');
                    if (actions) {
                        // remove existing connected badge if present
                        const existing = actions.querySelector('.nas-connected-badge');
                        if (existing) existing.remove();
                        const span = document.createElement('span');
                        span.className = 'badge bg-info ms-2 nas-connected-badge';
                        span.textContent = 'Connected';
                        actions.appendChild(span);
                    }
                }
                // Prefill indexing UI if backend returned share_path or credentials
                if (info && info.share_path) {
                    const ipath = document.getElementById('indexPath'); if (ipath) ipath.value = info.share_path;
                }
                if (info && info.username) {
                    const iuser = document.getElementById('indexUsername'); if (iuser) iuser.value = info.username;
                }
            } catch (e) {
                // non-fatal UI update
            }
        } else {
            window.NASIntegration.core.showMessage(`❌ Connect failed: ${res.error}`, 'error');
        }
    } catch (err) {
        window.NASIntegration.core.showMessage(`❌ Connect error: ${err.message}`, 'error');
    }
}

// Start indexing on the NAS share supplied in the UI
async function startIndexing() {
    const path = document.getElementById('indexPath')?.value;
    const username = document.getElementById('indexUsername')?.value || '';
    const password = document.getElementById('indexPassword')?.value || '';
    const mode = document.getElementById('indexOptions')?.value || 'scan_only';
    if (!path) return window.NASIntegration.core.showMessage('Please enter NAS share path', 'warning');
    window.NASIntegration.core.showMessage(`📢 Starting indexing on ${path}...`, 'info');
    try {
        const res = await window.NASIntegration.core.makeAPIRequest('/api/nas/start-indexing', { method: 'POST', body: JSON.stringify({ share_path: path, username, password, mode }) });
        if (res.success) {
            window.NASIntegration.core.showMessage('✅ DICOM indexing started successfully', 'success');
            // begin polling status
            pollIndexStatus();
        } else {
            window.NASIntegration.core.showMessage(`❌ Indexing failed: ${res.error}`, 'error');
            document.getElementById('indexResults').innerHTML = `❌ ${res.error || 'Indexing failed'}`;
        }
    } catch (err) {
        window.NASIntegration.core.showMessage(`❌ Indexing error: ${err.message}`, 'error');
        document.getElementById('indexResults').innerHTML = `❌ ${err.message}`;
    }
}

async function getIndexStatus() {
    try {
        const res = await window.NASIntegration.core.makeAPIRequest('/api/nas/indexing/status');
        if (res.success) {
            const s = res.status || res;
            document.getElementById('indexResults').innerHTML = window.NASIntegration.ui.formatIndexingStatus ? window.NASIntegration.ui.formatIndexingStatus(s) : JSON.stringify(s);
            return s;
        } else {
            document.getElementById('indexResults').innerHTML = `❌ ${res.error || 'Unknown'}`;
            return null;
        }
    } catch (err) {
        document.getElementById('indexResults').innerHTML = `❌ ${err.message}`;
        return null;
    }
}

// Polling helper
let _indexPollHandle = null;
async function pollIndexStatus(interval = 2000) {
    if (_indexPollHandle) clearTimeout(_indexPollHandle);
    const s = await getIndexStatus();
    if (!s) return;
    // stop polling when complete or idle
    if (s.state === 'running' || s.state === 'indexing' || s.progress < 100) {
        _indexPollHandle = setTimeout(()=>pollIndexStatus(interval), interval);
    } else {
        _indexPollHandle = null;
        window.NASIntegration.core.showMessage('✅ Indexing complete', 'success');
    }
}

async function getDeviceInfo(ip) {
    if (!ip) return window.NASIntegration.core.showMessage('No IP provided', 'warning');
    try {
        const res = await window.NASIntegration.core.makeAPIRequest(`/api/nas/device-info/${ip}`);
        if (res.success && res.device_info) {
            const info = res.device_info;
            const rt = info.response_time || (info.ping_result && _normalizePingResult(info.ping_result).response_time) || 'N/A';
            const html = `IP: ${ip}\nHostname: ${info.hostname || 'Unknown'}\nResponse: ${rt}`;
            window.NASIntegration.core.showMessage('✅ Device info retrieved', 'success');
            // Simple popup for now
            alert(html);
        } else {
            window.NASIntegration.core.showMessage(`❌ Device info failed: ${res.error || 'Unknown'}`, 'error');
        }
    } catch (err) {
        window.NASIntegration.core.showMessage(`❌ Device info error: ${err.message}`, 'error');
    }
}

async function scanDevice(ip) {
    if (!ip) return window.NASIntegration.core.showMessage('No IP provided', 'warning');
    window.NASIntegration.core.showMessage(`🔍 Scanning ${ip}...`, 'info');
    try {
        const res = await window.NASIntegration.core.makeAPIRequest('/api/nas/scan-device', { method: 'POST', body: JSON.stringify({ ip_address: ip }) });
        if (res.success && res.scan_result) {
            const openPorts = (res.scan_result.open_ports || []).length;
            window.NASIntegration.core.showMessage(`✅ Scan complete - ${openPorts} open ports`, 'success');
            try {
                // Insert inline accordion after the device row so user can inspect details inline
                const row = document.querySelector(`tr[data-ip="${ip}"]`);
                const existingAccordion = document.querySelector(`tr.scan-accordion-row[data-ip="${ip}-scan"]`);
                if (existingAccordion) {
                    // Toggle visibility: remove if present
                    existingAccordion.parentNode.removeChild(existingAccordion);
                } else if (row) {
                    const accordionHtml = window.NASIntegration.ui.formatScanAccordion(res.scan_result, ip);
                    // Insert after the device row
                    row.insertAdjacentHTML('afterend', accordionHtml);
                } else {
                    // Fallback: render to discoveryResults if row not found
                    const resultsHtml = window.NASIntegration.ui.formatScanResult(res.scan_result, ip);
                    const el = document.getElementById('discoveryResults');
                    if (el) el.innerHTML = resultsHtml;
                }
                // Optionally update the device's response cell to show scan count
                const rowAfter = document.querySelector(`tr[data-ip="${ip}"]`);
                if (rowAfter) {
                    const respCell = rowAfter.querySelector('.response-cell');
                    if (respCell) {
                        respCell.innerHTML = `${respCell.textContent || ''} <br><small class="text-muted">Scanned: ${openPorts} open</small>`;
                    }
                    // Update NAS confidence cell if present
                    const confCell = row.querySelector('.confidence-cell');
                    try {
                        const confidence = (res.scan_result.nas_confidence_score || res.scan_result.score || res.scan_result.nas_confidence);
                        if (confCell) {
                            let display = '<span class="text-muted">N/A</span>';
                            if (typeof confidence !== 'undefined' && confidence !== null) {
                                const pct = Math.max(0, Math.min(100, parseInt(confidence, 10) || 0));
                                const cls = pct >= 60 ? 'badge bg-success' : pct >= 30 ? 'badge bg-warning text-dark' : 'badge bg-secondary';
                                display = `<span class="${cls}">${pct}%</span>`;
                            } else if (res.scan_result.open_ports && res.scan_result.open_ports.length >= 0) {
                                // compute using client-side heuristic if backend didn't provide
                                const meta = window.NASIntegration.ui && typeof window.NASIntegration.ui.computeNasConfidence === 'function' ? window.NASIntegration.ui.computeNasConfidence(res.scan_result.open_ports) : null;
                                if (meta) {
                                    const pct = meta.score;
                                    const cls = pct >= 60 ? 'badge bg-success' : pct >= 30 ? 'badge bg-warning text-dark' : 'badge bg-secondary';
                                    display = `<span class="${cls}">${pct}%</span>`;
                                }
                            }
                            confCell.innerHTML = display;
                        }
                    } catch (e) {
                        // ignore UI confidence update errors
                    }
                }
            } catch (e) {
                // Non-fatal UI render error
            }
        } else {
            window.NASIntegration.core.showMessage(`❌ Scan failed: ${res.error || 'Unknown'}`, 'error');
        }
    } catch (err) {
        window.NASIntegration.core.showMessage(`❌ Scan error: ${err.message}`, 'error');
    }
}

function handleDeviceAction(action, ip, hostname) {
    switch (action) {
        case 'ping': pingDevice(ip); break;
        case 'connect': connectToDevice(ip); break;
        case 'rename': renameDevice(ip, hostname); break;
        case 'remove': removeDevice(ip, hostname); break;
        case 'info': getDeviceInfo(ip); break;
        case 'scan': scanDevice(ip); break;
        case 'test': testDeviceConnectivity(ip); break;
        default: window.NASIntegration.core.showMessage(`Unknown action: ${action}`, 'warning');
    }
}

async function clearDeviceList() {
    if (!confirm('Clear entire device list?')) return;
    try {
        const res = await window.NASIntegration.core.makeAPIRequest('/api/nas/clear-devices', { method: 'POST' });
        if (res.success) {
            const el = document.getElementById('discoveryResults'); if (el) el.innerHTML = '<p class="text-muted">Device list cleared. Run a new scan to discover devices.</p>';
            window.NASIntegration.core.showMessage('✅ Device list cleared', 'success');
            window.NASIntegration.lastDiscoveryResults = null;
        } else {
            window.NASIntegration.core.showMessage(`❌ Clear failed: ${res.error}`, 'error');
        }
    } catch (err) { window.NASIntegration.core.showMessage(`❌ Clear error: ${err.message}`, 'error'); }
}

async function exportDeviceList() {
    try {
        const res = await window.NASIntegration.core.makeAPIRequest('/api/nas/export-devices');
        if (res.success && res.devices) {
            const csv = window.NASIntegration.ui.convertToCSV(res.devices);
            const blob = new Blob([csv], { type: 'text/csv' });
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a'); a.href = url; a.download = `network_devices_${new Date().toISOString().split('T')[0]}.csv`; document.body.appendChild(a); a.click(); document.body.removeChild(a); window.URL.revokeObjectURL(url);
            window.NASIntegration.core.showMessage('✅ Exported device list', 'success');
        } else {
            window.NASIntegration.core.showMessage(`❌ Export failed: ${res.error}`, 'error');
        }
    } catch (err) { window.NASIntegration.core.showMessage(`❌ Export error: ${err.message}`, 'error'); }
}

// Public API
window.NASIntegration = window.NASIntegration || {};
window.NASIntegration.devices = {
    renameDevice,
    testDeviceConnectivity,
    removeDevice,
    pingDevice,
    connectToDevice,
    getDeviceInfo,
    scanDevice,
    handleDeviceAction,
    clearDeviceList,
    exportDeviceList
};

console.log('✅ Device Management module loaded successfully');
