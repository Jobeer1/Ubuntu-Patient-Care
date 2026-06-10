// Contacts Logic

window.loadContacts = async function() {
    try {
        const res = await window.fetchWithAuth(`/contacts`);
        if (!res) return;
        const contacts = await res.json();
        renderContacts(contacts);
    } catch (e) {
        console.error(e);
    }
}

function renderContacts(contacts) {
    const container = document.getElementById('groups-list');
    // Check if contacts section already exists
    let catContent = document.getElementById('contacts-list');
    
    if (!catContent) {
        // Create Header
        const catHeader = document.createElement('div');
        catHeader.className = 'category-header';
        catHeader.innerHTML = `
            <span><span class="category-arrow">></span> Contacts</span> 
            <span>
                <button onclick="event.stopPropagation(); window.promptAddContact()" style="background:none; border:none; color:var(--highlight); cursor:pointer; font-weight:bold; font-size:14px" title="Add Contact">+</button>
                (${contacts.length})
            </span>`;
        catHeader.onclick = () => {
            window.toggleCategory('contacts-list');
            catHeader.querySelector('.category-arrow').classList.toggle('expanded');
        };
        
        catContent = document.createElement('div');
        catContent.id = 'contacts-list';
        catContent.className = 'category-content';
        
        container.appendChild(catHeader);
        container.appendChild(catContent);
    } else {
        // Update count in header (simplified)
        const header = catContent.previousElementSibling;
        header.innerHTML = `
            <span><span class="category-arrow expanded">></span> Contacts</span> 
            <span>
                <button onclick="event.stopPropagation(); window.promptAddContact()" style="background:none; border:none; color:var(--highlight); cursor:pointer; font-weight:bold; font-size:14px" title="Add Contact">+</button>
                (${contacts.length})
            </span>`;
        header.onclick = () => {
            window.toggleCategory('contacts-list');
            header.querySelector('.category-arrow').classList.toggle('expanded');
        };
    }
    
    catContent.innerHTML = '';
    contacts.forEach(c => {
        const div = document.createElement('div');
        div.className = 'group-item';
        const unread = window.unreadCounts && window.unreadCounts[c.user_id];
        div.innerHTML = `
            <div style="display:flex; align-items:center">
                <span class="online-dot" style="background:${unread ? 'var(--red)' : (c.is_online ? '#00ff00' : '#666')}; box-shadow:${unread ? '0 0 5px var(--red)' : 'none'}"></span>
                <span style="${unread ? 'font-weight:bold' : ''}">${c.alias} ${unread ? '🔴' : ''}</span>
            </div>
            <span style="font-size:10px; color:#666">${unread ? 'NEW MSG' : 'DM'}</span>
        `;
        div.onclick = () => window.openContactChat(c.user_id);
        catContent.appendChild(div);
    });
}

window.promptAddContact = async function() {
    const target = prompt("Enter Username or User ID to add:");
    if (!target) return;
    
    try {
        const res = await fetch(`${window.API_BASE}/contacts/add`, {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${window.token}`
            },
            body: JSON.stringify({ target })
        });
        
        const data = await res.json();
        if (res.ok) {
            alert('Contact added!');
            window.loadContacts();
        } else {
            alert(data.error);
        }
    } catch (e) {
        alert('Error adding contact');
    }
}

window.openContactChat = async function(contactId) {
    if (window.unreadCounts) {
        delete window.unreadCounts[contactId];
    }
    
    try {
        const res = await fetch(`${window.API_BASE}/contacts/${contactId}/chat`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${window.token}` }
        });
        
        if (res.ok) {
            const group = await res.json();
            // Normalize group object to match what openChat expects
            const groupObj = {
                id: group.group_id,
                name: group.name,
                is_private: true,
                max_members: 2,
                member_count: 2
            };
            openChat(groupObj);
        } else {
            const data = await res.json();
            alert(data.error);
        }
    } catch (e) {
        console.error(e);
    }
}

// Global Exports
window.loadContacts = loadContacts;
window.renderContacts = renderContacts;
window.promptAddContact = promptAddContact;
window.openContactChat = openContactChat;
