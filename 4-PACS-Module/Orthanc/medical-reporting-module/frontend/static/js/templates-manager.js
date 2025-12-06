/* Simple templates manager client */
(function () {
  const listEl = document.getElementById('templates-list');
  const editName = document.getElementById('edit-name');
  const editContent = document.getElementById('edit-content');
  const saveBtn = document.getElementById('save-btn');
  const deleteBtn = document.getElementById('delete-btn');
  const createBtn = document.getElementById('create-btn');
  const newName = document.getElementById('new-name');
  const newDesc = document.getElementById('new-desc');
  const importFile = document.getElementById('import-file');
  const loadIntoReport = document.getElementById('load-into-report');
  const listSpinner = document.getElementById('list-spinner');
  const saveSpinner = document.getElementById('save-spinner');

  let templates = [];
  let current = null;

  function setLoading(el, on) {
    if (!el) return;
    el.classList.toggle('hidden', !on);
  }

  function setDisabled(...els) {
    els.forEach(e => { if (e) e.setAttribute('disabled','disabled'); });
  }
  function setEnabled(...els) {
    els.forEach(e => { if (e) e.removeAttribute('disabled'); });
  }

  function api(path, opts) {
    return fetch(path, Object.assign({credentials: 'same-origin'}, opts)).then(r => r.json());
  }

  function renderList() {
    listEl.innerHTML = '';
    templates.forEach(t => {
      const li = document.createElement('li');
      li.className = 'p-2 rounded hover:bg-gray-50 cursor-pointer border';
      li.innerHTML = `<div class="flex justify-between items-center"><div><strong>${escapeHtml(t.name)}</strong><div class="text-xs text-gray-600">${escapeHtml(t.description||'')}</div></div><div class="text-xs text-gray-500">${t.created_at?new Date(t.created_at).toLocaleDateString():''}</div></div>`;
      li.onclick = () => { selectTemplate(t.id); };
      listEl.appendChild(li);
    });
  }

  function escapeHtml(s) { return String(s||'').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'})[c]); }

  function loadTemplates() {
    setLoading(listSpinner, true);
    setDisabled(createBtn);
    api('/api/templates').then(res => {
      setLoading(listSpinner, false);
      setEnabled(createBtn);
      if (res && res.success) {
        templates = res.templates || [];
        renderList();
      } else {
        alert('Failed to load templates');
      }
    }).catch(e => { console.error(e); setLoading(listSpinner, false); setEnabled(createBtn); alert('Failed to load templates'); });
  }

  function selectTemplate(id) {
    current = templates.find(t => t.id === id) || null;
    if (!current) return;
    editName.value = current.name || '';
    editContent.value = current.content || '';
  }

  createBtn.onclick = () => {
    const name = newName.value && newName.value.trim();
    const description = newDesc.value && newDesc.value.trim();
    if (!name) { alert('Name required'); return; }
    setDisabled(createBtn);
    const form = new FormData();
    form.append('name', name);
    form.append('description', description || '');
    form.append('content', '');
    fetch('/api/templates', {method: 'POST', body: form, credentials: 'same-origin'})
      .then(r => r.json()).then(res => {
        setEnabled(createBtn);
        if (res && res.success) { loadTemplates(); newName.value=''; newDesc.value=''; }
        else alert('Failed to create');
      }).catch(e => { console.error(e); setEnabled(createBtn); alert('Failed to create'); });
  };

  saveBtn.onclick = () => {
    if (!current) { alert('No template selected'); return; }
    setDisabled(saveBtn, deleteBtn);
    setLoading(saveSpinner, true);
    const payload = { name: editName.value, content: editContent.value };
    fetch('/api/templates/' + current.id, {method: 'PUT', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(payload), credentials: 'same-origin'})
      .then(r => r.json()).then(res => { setLoading(saveSpinner, false); setEnabled(saveBtn, deleteBtn); if (res && res.success) { loadTemplates(); } else alert('Failed to save'); }).catch(e=>{ console.error(e); setLoading(saveSpinner, false); setEnabled(saveBtn, deleteBtn); alert('Failed to save'); });
  };

  deleteBtn.onclick = () => {
    if (!current) { alert('No template selected'); return; }
    if (!confirm('Delete this template?')) return;
    setDisabled(saveBtn, deleteBtn);
    fetch('/api/templates/' + current.id, {method: 'DELETE', credentials: 'same-origin'})
      .then(r => r.json()).then(res => { setEnabled(saveBtn, deleteBtn); if (res && res.success) { current = null; editName.value=''; editContent.value=''; loadTemplates(); } else alert('Failed to delete'); }).catch(e=>{ console.error(e); setEnabled(saveBtn, deleteBtn); alert('Failed to delete'); });
  };

  importFile.onchange = () => {
    const f = importFile.files && importFile.files[0];
    if (!f) return;
    const fd = new FormData();
    fd.append('file', f);
    setDisabled(createBtn);
    fetch('/api/templates', {method: 'POST', body: fd, credentials: 'same-origin'})
      .then(r => r.json()).then(res => { setEnabled(createBtn); if (res && res.success) { loadTemplates(); } else alert('Import failed'); }).catch(e=>{ console.error(e); setEnabled(createBtn); alert('Import failed'); });
  };

  loadIntoReport.onclick = () => {
    if (!current) { alert('No template selected'); return; }
    const evt = new CustomEvent('templates:load', {detail: {template: current}});
    window.dispatchEvent(evt);
    // small non-blocking toast instead of alert
    const toast = document.createElement('div');
    toast.textContent = 'Template dispatched to the app';
    toast.style.position='fixed'; toast.style.right='12px'; toast.style.bottom='12px'; toast.style.background='#002395'; toast.style.color='white'; toast.style.padding='8px 12px'; toast.style.borderRadius='6px';
    document.body.appendChild(toast);
    setTimeout(()=>toast.remove(),2500);
  };

  // Initial load
  loadTemplates();
})();
