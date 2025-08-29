(function(){
    window.NASIntegration = window.NASIntegration || {};
    window.NASIntegration._uiParts = window.NASIntegration._uiParts || {};

    function formatBytes(bytes){ if (bytes === 0) return '0 Bytes'; const k=1024; const sizes=['Bytes','KB','MB','GB','TB']; const i = Math.floor(Math.log(bytes)/Math.log(k)); return parseFloat((bytes/Math.pow(k,i)).toFixed(2)) + ' ' + sizes[i]; }
    function formatUptime(seconds){ if (!seconds) return 'Unknown'; const days=Math.floor(seconds/86400); const hours=Math.floor((seconds%86400)/3600); const minutes=Math.floor((seconds%3600)/60); if(days>0) return `${days}d ${hours}h ${minutes}m`; if(hours>0) return `${hours}h ${minutes}m`; return `${minutes}m`; }
    function showDeviceTooltip(element, text){ try{ const tooltip=document.createElement('div'); tooltip.className='device-tooltip'; tooltip.textContent=text; document.body.appendChild(tooltip); const rect=element.getBoundingClientRect(); tooltip.style.left=rect.left+'px'; tooltip.style.top=(rect.top-tooltip.offsetHeight-5)+'px'; setTimeout(()=>{ if(tooltip.parentNode) tooltip.parentNode.removeChild(tooltip); },3000);}catch(e){} }

    window.NASIntegration._uiParts.utils = { formatBytes, formatUptime, showDeviceTooltip };
    console.log('ui-helpers/utils loaded');
})();
