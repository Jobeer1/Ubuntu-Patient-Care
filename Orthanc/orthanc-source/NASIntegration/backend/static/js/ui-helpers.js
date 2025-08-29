/* ui-helpers.js (loader)
   Minimal loader/compatibility shim for UI helpers.
   Delegates to modular helpers in `ui-helpers/` under `window.NASIntegration._uiParts`
   with safe fallbacks so existing modules keep working.
*/

(function(){
    window.NASIntegration = window.NASIntegration || {};
    window.NASIntegration._uiParts = window.NASIntegration._uiParts || {};

    function parts() { return window.NASIntegration._uiParts; }

    // Safe delegators: if a part exists, call it; otherwise use a small fallback.
    const ui = {
        formatArpTable: function(devices, totalEntries){
            if (parts().formatters && parts().formatters.formatArpTable) return parts().formatters.formatArpTable(devices, totalEntries);
            return '<p class="text-muted">ARP table UI not loaded</p>';
        },
        formatRangePingResults: function(results, statistics, range){
            if (parts().formatters && parts().formatters.formatRangePingResults) return parts().formatters.formatRangePingResults(results, statistics, range);
            return '<p class="text-muted">Ping range UI not loaded</p>';
        },
        formatPingResult: function(p){ if (parts().formatters && parts().formatters.formatPingResult) return parts().formatters.formatPingResult(p); return '<p class="text-muted">Ping UI not loaded</p>'; },
        formatDiscoveredDevices: function(d){ if (parts().formatters && parts().formatters.formatDiscoveredDevices) return parts().formatters.formatDiscoveredDevices(d); return '<p class="text-muted">Discovery UI not loaded</p>'; },
        formatScanResult: function(s, ip){ if (parts().formatters && parts().formatters.formatScanResult) return parts().formatters.formatScanResult(s, ip); return '<p class="text-muted">Scan UI not loaded</p>'; },
        formatScanAccordion: function(s, ip){ if (parts().formatters && parts().formatters.formatScanAccordion) return parts().formatters.formatScanAccordion(s, ip); return '<tr class="scan-accordion-row"><td colspan="7">Scan UI not loaded</td></tr>'; },
        computeNasConfidence: function(openPorts){ return parts().ports && parts().ports.computeNasConfidence ? parts().ports.computeNasConfidence(openPorts) : { score:0, matches:[] }; },
        getPortNumber: function(p){ return parts().ports && parts().ports.getPortNumber ? parts().ports.getPortNumber(p) : null; },
        getDefaultServiceName: function(port){ return parts().ports && parts().ports.getDefaultServiceName ? parts().ports.getDefaultServiceName(port) : null; },
        formatStorageStatus: function(d){ return '<p class="text-muted">Storage UI not loaded</p>'; },
        formatIndexingStatus: function(i){ return '<p class="text-muted">Indexing UI not loaded</p>'; },
        formatPatientResults: function(p){ return '<p class="text-muted">Patients UI not loaded</p>'; },
        formatShareLink: function(s){ return '<p class="text-muted">Share UI not loaded</p>'; },
        formatOrthancStatus: function(s){ return '<p class="text-muted">Orthanc UI not loaded</p>'; },
        convertToCSV: function(rows){ if(!rows||!rows.length) return ''; const keys = Object.keys(rows[0]); const lines=[keys.join(',')]; rows.forEach(r=>lines.push(keys.map(k=>JSON.stringify(r[k]||'')).join(','))); return lines.join('\n'); },
        updateDeviceStatus: function(ip,status){ try{ const row=document.querySelector(`.device-row[data-ip="${ip}"]`); if(!row) return; row.classList.toggle('online', status==='online'); row.classList.toggle('offline', status==='offline'); }catch(e){} },
        highlightDevice: function(ip){ try{ const el=document.querySelector(`.device-row[data-ip="${ip}"]`); if(!el) return; el.style.transition='background-color 0.3s'; el.style.backgroundColor='#fff3cd'; setTimeout(()=>el.style.backgroundColor='',1200);}catch(e){} },
        showDeviceTooltip: function(el,t){ return parts().utils && parts().utils.showDeviceTooltip ? parts().utils.showDeviceTooltip(el,t) : null; },
        formatBytes: function(b){ return parts().utils && parts().utils.formatBytes ? parts().utils.formatBytes(b) : (b||0).toString(); },
        formatUptime: function(s){ return parts().utils && parts().utils.formatUptime ? parts().utils.formatUptime(s) : 'Unknown'; },
        toggleOfflineDevices: function(){ try{ const rows=document.querySelectorAll('.device-row.offline'); if(!rows||rows.length===0) return; const isHidden = rows[0].style.display==='none'; rows.forEach(r=>r.style.display = isHidden ? '' : 'none'); const btn=document.querySelector('.toggle-offline-btn'); if(btn) btn.textContent = isHidden ? '👁️ Hide Offline' : '👁️ Show Offline'; }catch(e){} }
    };

    window.NASIntegration.ui = ui;
    console.log('ui-helpers loader installed');
})();
