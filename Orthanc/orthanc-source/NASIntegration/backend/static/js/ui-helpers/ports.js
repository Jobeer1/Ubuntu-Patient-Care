(function(){
    // Ports and NAS heuristic helpers
    window.NASIntegration = window.NASIntegration || {};
    window.NASIntegration._uiParts = window.NASIntegration._uiParts || {};

    function getPortNumber(p) {
        if (!p && p !== 0) return null;
        if (typeof p === 'number' && Number.isFinite(p)) return p;
        if (typeof p === 'string') {
            const m = p.match(/^(\d+)/);
            if (m) return parseInt(m[1], 10);
            return null;
        }
        const keys = ['port','port_number','number','port_no','p'];
        for (let k of keys) {
            if (Object.prototype.hasOwnProperty.call(p, k)) {
                const v = p[k];
                if (v && typeof v === 'object') {
                    if (Object.prototype.hasOwnProperty.call(v, 'port')) {
                        const nv = v.port;
                        if (typeof nv === 'number' && Number.isFinite(nv)) return nv;
                        if (typeof nv === 'string') { const m2 = nv.match(/^(\d+)/); if (m2) return parseInt(m2[1],10); }
                    }
                    if (Object.prototype.hasOwnProperty.call(v, 'portid')) {
                        const nv = v.portid;
                        if (typeof nv === 'number' && Number.isFinite(nv)) return nv;
                        if (typeof nv === 'string') { const m2 = nv.match(/^(\d+)/); if (m2) return parseInt(m2[1],10); }
                    }
                }
                if (typeof v === 'number' && Number.isFinite(v)) return v;
                if (typeof v === 'string') {
                    const m = v.match(/^(\d+)/);
                    if (m) return parseInt(m[1], 10);
                }
            }
        }
        if (Array.isArray(p) && p.length) return getPortNumber(p[0]);
        for (const k in p) {
            if (!Object.prototype.hasOwnProperty.call(p,k)) continue;
            const v = p[k];
            if (typeof v === 'number' && Number.isFinite(v)) return v;
            if (typeof v === 'string') { const m = v.match(/^(\d+)/); if (m) return parseInt(m[1],10); }
        }
        return null;
    }

    function getDefaultServiceName(port) {
        if (!port && port !== 0) return null;
        const p = parseInt(port,10);
        if (isNaN(p)) return null;
        const map = {
            21: 'FTP',22:'SSH',23:'Telnet',25:'SMTP',53:'DNS',67:'DHCP',68:'DHCP',80:'HTTP',81:'HTTP-alt',110:'POP3',139:'NetBIOS',143:'IMAP',161:'SNMP',1900:'SSDP',443:'HTTPS',445:'SMB',548:'AFP',631:'IPP',873:'rsync',2049:'NFS',3306:'MySQL',5000:'DSM',5001:'DSM-SSL',8080:'HTTP-alt',8081:'HTTP-alt',8082:'HTTP-alt',8888:'HTTP-alt',9000:'Web UI',9001:'Web UI'
        };
        return map[p] || null;
    }

    function computeNasConfidence(openPorts) {
        const portWeights = {
            21:2,22:1,80:1,443:1,445:4,139:3,548:3,2049:3,873:1,5000:6,5001:6,8080:3,8081:3,8082:2,8088:2,8888:2,9000:2,9001:2,8000:1,8001:1,1900:1,5357:1,3690:1,111:1,631:1
        };
        let weightSum = 0; const matches = [];
        (openPorts || []).forEach(p => {
            const port = parseInt(getPortNumber(p),10);
            if (!isNaN(port)) {
                const w = portWeights[port] || 0;
                weightSum += w;
                if (w >= 3) matches.push(`port ${port}`);
            }
            const banner = ((p && (p.service||'')) + ' ' + (p && (p.info||''))).toLowerCase();
            if (/synology|diskstation|dsm/i.test(banner)) { weightSum += 8; matches.push('Synology'); }
            if (/qnap|qts|qubs|qum|quwe/i.test(banner)) { weightSum += 9; matches.push('QNAP'); }
            if (/(nas\b|network attached storage)/i.test(banner)) { weightSum += 6; matches.push('NAS banner'); }
            if (/samba|smb|cifs/i.test(banner)) { weightSum += 4; matches.push('SMB'); }
            if (/minidlna|upnp|ssdp|dlna/i.test(banner)) { weightSum += 2; matches.push('UPnP/DLNA'); }
        });
        const openCount = (openPorts || []).length;
        let raw = Math.round(Math.min(100, weightSum * 12 + (openCount >= 8 ? 20 : 0)));
        raw = Math.max(raw, Math.round(Math.min(100, weightSum * 10)));
        const score = Math.max(0, Math.min(100, raw));
        const uniq = [...new Set(matches)].slice(0,6);
        return { score, matches: uniq };
    }

    window.NASIntegration._uiParts.ports = { getPortNumber, getDefaultServiceName, computeNasConfidence };
    console.log('ui-helpers/ports loaded');
})();
