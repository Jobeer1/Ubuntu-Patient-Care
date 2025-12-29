// Contacts Logic

async function loadContacts() {
    try {
        const res = await fetchWithAuth(`/contacts`);
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
                <button onclick="event.stopPropagation(); promptAddContact()" style="background:none; border:none; color:var(--highlight); cursor:pointer; font-weight:bold; font-size:14px" title="Add Contact">+</button>
                (${contacts.length})
            </span>`;
        catHeader.onclick = () => {
            toggleCategory('contacts-list');
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
                <button onclick="event.stopPropagation(); promptAddContact()" style="background:none; border:none; color:var(--highlight); cursor:pointer; font-weight:bold; font-size:14px" title="Add Contact">+</button>
                (${contacts.length})
            </span>`;
        header.onclick = () => {
            toggleCategory('contacts-list');
            header.querySelector('.category-arrow').classList.toggle('expanded');
        };
    }
    
    catContent.innerHTML = '';
    contacts.forEach(c => {
        const div = document.createElement('div');
        div.className = 'group-item';
        div.innerHTML = `
            <div style="display:flex; align-items:center">
                <span class="online-dot" style="background:${c.is_online ? '#00ff00' : '#666'}"></span>
                <span>${c.alias}</span>
            </div>
            <span style="font-size:10px; color:#666">DM</span>
        `;
        div.onclick = () => openContactChat(c.user_id);
        catContent.appendChild(div);
    });
}

async function promptAddContact() {
    const target = prompt("Enter Username or User ID to add:");
    if (!target) return;
    
    try {
        const res = await fetch(`${API_BASE}/contacts/add`, {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({ target })
        });
        
        const data = await res.json();
        if (res.ok) {
            alert('Contact added!');
            loadContacts();
        } else {
            alert(data.error);
        }
    } catch (e) {
        alert('Error adding contact');
    }
}

async function openContactChat(contactId) {
    try {
        const res = await fetch(`${API_BASE}/contacts/${contactId}/chat`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}` }
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
