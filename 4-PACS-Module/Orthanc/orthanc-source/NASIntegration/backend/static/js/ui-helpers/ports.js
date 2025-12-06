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
            // Medical Imaging Device Ports (High Priority)
            104: 50,      // DICOM (primary medical imaging protocol)
            11112: 45,    // DICOM C-MOVE (common in PACS)
            8104: 40,     // DICOM C-FIND (query/retrieve)
            2762: 35,     // DICOM TLS (secure DICOM)
            4006: 35,     // DICOM over TLS
            2575: 30,     // DICOM Web Services
            
            // PACS and Medical System Ports
            80: 25,       // HTTP (web interface for medical devices)
            443: 30,      // HTTPS (secure web interface)
            22: 15,       // SSH (remote management)
            23: 10,       // Telnet (legacy management)
            161: 20,      // SNMP (network monitoring)
            
            // File Sharing (for image storage)
            445: 20,      // SMB/CIFS
            139: 15,      // NetBIOS/SMB
            2049: 20,     // NFS
            21: 15,       // FTP
            
            // Database and Application Ports
            3306: 15,     // MySQL (common in medical systems)
            1433: 15,     // SQL Server
            1521: 15,     // Oracle
            5432: 15,     // PostgreSQL
            
            // Web Services
            8080: 20,     // HTTP Alt (medical device web interfaces)
            8443: 25,     // HTTPS Alt
            9000: 20,     // Common medical device management
            9090: 20,     // Common medical device management
            
            // Specialized Medical Ports
            2575: 35,     // DICOM Web Services
            4242: 30,     // DICOM TLS alternative
            2761: 30,     // DICOM TLS alternative
            11113: 35,    // DICOM C-STORE (storage)
            11114: 35,    // DICOM C-GET (retrieve)
            
            // Network Services
            53: 5,        // DNS
            67: 10,       // DHCP
            68: 10,       // DHCP
            123: 5,       // NTP
            514: 10       // Syslog
        };
        
        let weightSum = 0; 
        const matches = [];
        
        (openPorts || []).forEach(p => {
            const port = parseInt(getPortNumber(p),10);
            if (!isNaN(port)) {
                const w = portWeights[port] || 0;
                weightSum += w;
                
                // Medical device indicators
                if (port === 104) matches.push('DICOM Protocol');
                else if (port === 11112) matches.push('DICOM C-MOVE');
                else if (port === 8104) matches.push('DICOM C-FIND');
                else if (port === 2762 || port === 4006) matches.push('DICOM TLS');
                else if (port === 2575) matches.push('DICOM Web Services');
                else if (port === 80 || port === 443) matches.push('Web Interface');
                else if (port === 445 || port === 139) matches.push('File Sharing');
                else if (port === 2049) matches.push('NFS Storage');
                else if (port === 3306 || port === 1433) matches.push('Database');
                else if (port === 8080 || port === 8443) matches.push('Web Management');
                else if (w >= 15) matches.push(`Port ${port}`);
            }
            
            // Banner-based detection for medical devices
            const banner = ((p && (p.service||'')) + ' ' + (p && (p.info||''))).toLowerCase();
            if (/dicom|pacs|medical|imaging|ct|mri|x-ray|ultrasound/i.test(banner)) { 
                weightSum += 40; 
                matches.push('Medical Imaging Service'); 
            }
            if (/orthanc|dcm4chee|pacs|ris|his/i.test(banner)) { 
                weightSum += 45; 
                matches.push('PACS System'); 
            }
            if (/philips|ge healthcare|siemens|toshiba|hitachi/i.test(banner)) { 
                weightSum += 35; 
                matches.push('Medical Vendor Software'); 
            }
            if (/hl7|dicomweb|wado/i.test(banner)) { 
                weightSum += 30; 
                matches.push('Medical Standards'); 
            }
        });
        
        // Bonus scoring for medical device combinations
        const portSet = new Set((openPorts || []).map(p => parseInt(getPortNumber(p),10)).filter(p => !isNaN(p)));
        
        // DICOM protocol suite bonus
        if (portSet.has(104) && (portSet.has(11112) || portSet.has(8104))) {
            weightSum += 25;
            matches.push('DICOM Protocol Suite');
        }
        
        // PACS system indicators
        if ((portSet.has(80) || portSet.has(443)) && (portSet.has(3306) || portSet.has(1433))) {
            weightSum += 20;
            matches.push('Database + Web (PACS Pattern)');
        }
        
        // Medical imaging device bonus
        const medicalPorts = [104, 11112, 8104, 2762, 4006, 2575];
        const medicalPortCount = medicalPorts.filter(p => portSet.has(p)).length;
        if (medicalPortCount >= 2) {
            weightSum += medicalPortCount * 10;
            matches.push(`${medicalPortCount} Medical Ports`);
        }
        
        // Storage + medical protocols
        if ((portSet.has(445) || portSet.has(2049)) && portSet.has(104)) {
            weightSum += 15;
            matches.push('Storage + DICOM');
        }
        
        const openCount = (openPorts || []).length;
        
        // Calculate final score with medical device focus
        let raw = Math.round(Math.min(100, weightSum * 1.2 + (openCount >= 5 ? 15 : 0)));
        raw = Math.max(raw, Math.round(Math.min(100, weightSum * 1.0)));
        const score = Math.max(0, Math.min(100, raw));
        
        const uniq = [...new Set(matches)].slice(0,6);
        return { score, matches: uniq };
    }

    window.NASIntegration._uiParts.ports = { getPortNumber, getDefaultServiceName, computeNasConfidence };
    console.log('ui-helpers/ports loaded');
})();
