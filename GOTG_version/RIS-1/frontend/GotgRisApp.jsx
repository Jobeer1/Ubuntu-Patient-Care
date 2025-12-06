/**
 * GOTG-RIS Frontend: React PWA with offline-first, instant sync
 * Optimized for low-bandwidth, low-end devices
 * 
 * Core features:
 * - Service Worker for offline capability
 * - IndexedDB for local persistence
 * - Real-time sync status
 * - Minimal bundle size
 */

import React, { useState, useEffect, useContext, createContext } from 'react';

// =============================================
// Offline Sync Context
// =============================================

const OfflineSyncContext = createContext();

export const useSyncContext = () => {
  const context = useContext(OfflineSyncContext);
  if (!context) {
    throw new Error('useSyncContext must be used within OfflineSyncProvider');
  }
  return context;
};

export const OfflineSyncProvider = ({ children }) => {
  const [isOnline, setIsOnline] = useState(navigator.onLine);
  const [syncStatus, setSyncStatus] = useState('idle');
  const [pendingItems, setPendingItems] = useState(0);
  const [lastSyncTime, setLastSyncTime] = useState(null);

  // Detect online/offline
  useEffect(() => {
    const handleOnline = () => setIsOnline(true);
    const handleOffline = () => setIsOnline(false);

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  // Sync when online
  useEffect(() => {
    if (isOnline && syncStatus !== 'syncing') {
      triggerSync();
    }
  }, [isOnline]);

  const triggerSync = async () => {
    setSyncStatus('syncing');
    try {
      const response = await fetch('/api/sync/status', {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
      });
      const data = await response.json();
      setPendingItems(data.queue_stats?.pending || 0);
      setLastSyncTime(new Date());
      setSyncStatus('idle');
    } catch (error) {
      console.error('Sync error:', error);
      setSyncStatus('error');
    }
  };

  return (
    <OfflineSyncContext.Provider
      value={{
        isOnline,
        syncStatus,
        pendingItems,
        lastSyncTime,
        triggerSync
      }}
    >
      {children}
    </OfflineSyncContext.Provider>
  );
};

// =============================================
// IndexedDB Manager
// =============================================

class IndexedDBManager {
  constructor(dbName = 'GOTG_RIS', version = 1) {
    this.dbName = dbName;
    this.version = version;
    this.db = null;
  }

  async init() {
    return new Promise((resolve, reject) => {
      const request = indexedDB.open(this.dbName, this.version);

      request.onerror = () => reject(request.error);
      request.onsuccess = () => {
        this.db = request.result;
        resolve(this.db);
      };

      request.onupgradeneeded = (event) => {
        const db = event.target.result;

        // Create object stores
        if (!db.objectStoreNames.contains('patients')) {
          db.createObjectStore('patients', { keyPath: 'id' });
        }
        if (!db.objectStoreNames.contains('studies')) {
          db.createObjectStore('studies', { keyPath: 'id' });
        }
        if (!db.objectStoreNames.contains('reports')) {
          db.createObjectStore('reports', { keyPath: 'id' });
        }
        if (!db.objectStoreNames.contains('syncQueue')) {
          db.createObjectStore('syncQueue', { keyPath: 'id', autoIncrement: true });
        }
      };
    });
  }

  async save(storeName, data) {
    const transaction = this.db.transaction([storeName], 'readwrite');
    const store = transaction.objectStore(storeName);
    return new Promise((resolve, reject) => {
      const request = store.put(data);
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
  }

  async get(storeName, key) {
    const transaction = this.db.transaction([storeName], 'readonly');
    const store = transaction.objectStore(storeName);
    return new Promise((resolve, reject) => {
      const request = store.get(key);
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
  }

  async getAll(storeName) {
    const transaction = this.db.transaction([storeName], 'readonly');
    const store = transaction.objectStore(storeName);
    return new Promise((resolve, reject) => {
      const request = store.getAll();
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
  }

  async delete(storeName, key) {
    const transaction = this.db.transaction([storeName], 'readwrite');
    const store = transaction.objectStore(storeName);
    return new Promise((resolve, reject) => {
      const request = store.delete(key);
      request.onsuccess = () => resolve();
      request.onerror = () => reject(request.error);
    });
  }
}

// =============================================
// Patient Management Component
// =============================================

export const PatientManager = () => {
  const [patients, setPatients] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [newPatient, setNewPatient] = useState({
    first_name: '',
    last_name: '',
    phone: '',
    id_number: ''
  });
  const { isOnline, pendingItems } = useSyncContext();
  const dbManager = new IndexedDBManager();

  useEffect(() => {
    loadPatients();
  }, []);

  const loadPatients = async () => {
    setLoading(true);
    try {
      // Try to load from API
      const response = await fetch('/api/patients', {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
      });
      
      if (response.ok) {
        const data = await response.json();
        setPatients(data);
        // Cache locally
        await dbManager.init();
        for (const patient of data) {
          await dbManager.save('patients', patient);
        }
      } else {
        throw new Error('Failed to load patients');
      }
    } catch (error) {
      console.log('Using cached patients');
      // Fall back to cached data
      const cached = await dbManager.getAll('patients');
      setPatients(cached);
      setError('Offline mode: showing cached data');
    }
    setLoading(false);
  };

  const handleAddPatient = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      // Save locally immediately
      const patient = {
        ...newPatient,
        id: `local_${Date.now()}`,
        created_at: new Date().toISOString(),
        sync_status: 'pending'
      };

      await dbManager.init();
      await dbManager.save('patients', patient);
      setPatients([patient, ...patients]);

      // Try to sync
      if (isOnline) {
        try {
          const response = await fetch('/api/patients', {
            method: 'POST',
            headers: {
              'Authorization': `Bearer ${localStorage.getItem('token')}`,
              'Content-Type': 'application/json'
            },
            body: JSON.stringify(newPatient)
          });

          if (response.ok) {
            const result = await response.json();
            patient.sync_status = 'synced';
            patient.id = result.id;
            patient.patient_id = result.patient_id;
          }
        } catch (syncError) {
          console.log('Will sync when online');
        }
      }

      await dbManager.save('patients', patient);
      setNewPatient({ first_name: '', last_name: '', phone: '', id_number: '' });
    } catch (error) {
      setError(error.message);
    }

    setLoading(false);
  };

  return (
    <div className="patient-manager">
      <div className="header">
        <h2>Patient Management</h2>
        <div className="status">
          {isOnline ? (
            <span className="badge online">🟢 Online</span>
          ) : (
            <span className="badge offline">🔴 Offline</span>
          )}
          {pendingItems > 0 && (
            <span className="badge pending">⏱️ {pendingItems} pending</span>
          )}
        </div>
      </div>

      {error && <div className="alert error">{error}</div>}

      <form onSubmit={handleAddPatient} className="form">
        <h3>Register New Patient</h3>
        <input
          type="text"
          placeholder="First Name"
          value={newPatient.first_name}
          onChange={(e) => setNewPatient({...newPatient, first_name: e.target.value})}
          required
        />
        <input
          type="text"
          placeholder="Last Name"
          value={newPatient.last_name}
          onChange={(e) => setNewPatient({...newPatient, last_name: e.target.value})}
          required
        />
        <input
          type="tel"
          placeholder="Phone"
          value={newPatient.phone}
          onChange={(e) => setNewPatient({...newPatient, phone: e.target.value})}
        />
        <input
          type="text"
          placeholder="ID Number"
          value={newPatient.id_number}
          onChange={(e) => setNewPatient({...newPatient, id_number: e.target.value})}
        />
        <button type="submit" disabled={loading}>
          {loading ? 'Saving...' : 'Save Patient'}
        </button>
      </form>

      <div className="patients-list">
        <h3>Patients ({patients.length})</h3>
        {loading ? (
          <p>Loading...</p>
        ) : patients.length === 0 ? (
          <p>No patients found</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Phone</th>
                <th>ID Number</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {patients.map((patient) => (
                <tr key={patient.id}>
                  <td>{patient.first_name} {patient.last_name}</td>
                  <td>{patient.phone}</td>
                  <td>{patient.id_number}</td>
                  <td>
                    <span className={`status ${patient.sync_status}`}>
                      {patient.sync_status === 'pending' ? '⏱️' : '✓'} {patient.sync_status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
};

// =============================================
// Study Management Component
// =============================================

export const StudyManager = () => {
  const [studies, setStudies] = useState([]);
  const [patients, setPatients] = useState([]);
  const [loading, setLoading] = useState(false);
  const [newStudy, setNewStudy] = useState({
    patient_id: '',
    modality: 'CR',
    description: '',
    referring_physician: ''
  });
  const { isOnline } = useSyncContext();
  const dbManager = new IndexedDBManager();

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/studies', {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
      });

      if (response.ok) {
        const data = await response.json();
        setStudies(data.studies);
        await dbManager.init();
        for (const study of data.studies) {
          await dbManager.save('studies', study);
        }
      }
    } catch (error) {
      console.log('Using cached studies');
    }
    setLoading(false);
  };

  const handleAddStudy = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      const study = {
        ...newStudy,
        id: `local_${Date.now()}`,
        created_at: new Date().toISOString(),
        sync_status: 'pending'
      };

      await dbManager.init();
      await dbManager.save('studies', study);
      setStudies([study, ...studies]);

      // Try to sync
      if (isOnline) {
        try {
          const response = await fetch('/api/studies', {
            method: 'POST',
            headers: {
              'Authorization': `Bearer ${localStorage.getItem('token')}`,
              'Content-Type': 'application/json'
            },
            body: JSON.stringify(newStudy)
          });

          if (response.ok) {
            const result = await response.json();
            study.sync_status = 'synced';
            study.id = result.id;
          }
        } catch (syncError) {
          console.log('Will sync when online');
        }
      }

      await dbManager.save('studies', study);
      setNewStudy({patient_id: '', modality: 'CR', description: '', referring_physician: ''});
    } catch (error) {
      console.error(error);
    }

    setLoading(false);
  };

  return (
    <div className="study-manager">
      <h2>Study Management</h2>

      <form onSubmit={handleAddStudy} className="form">
        <h3>Create New Study</h3>
        <select
          value={newStudy.modality}
          onChange={(e) => setNewStudy({...newStudy, modality: e.target.value})}
        >
          <option value="CR">Radiography (CR)</option>
          <option value="DX">Digital X-Ray (DX)</option>
          <option value="CT">CT Scan</option>
          <option value="MR">MRI</option>
          <option value="US">Ultrasound</option>
          <option value="XC">Other</option>
        </select>
        <input
          type="text"
          placeholder="Description"
          value={newStudy.description}
          onChange={(e) => setNewStudy({...newStudy, description: e.target.value})}
        />
        <button type="submit" disabled={loading}>
          {loading ? 'Creating...' : 'Create Study'}
        </button>
      </form>

      <div className="studies-list">
        <h3>Studies ({studies.length})</h3>
        {loading ? (
          <p>Loading...</p>
        ) : studies.length === 0 ? (
          <p>No studies found</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Accession</th>
                <th>Modality</th>
                <th>Description</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {studies.map((study) => (
                <tr key={study.id}>
                  <td>{study.accession_number}</td>
                  <td>{study.modality}</td>
                  <td>{study.description}</td>
                  <td>{study.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
};

// =============================================
// Sync Status Component
// =============================================

export const SyncStatus = () => {
  const { isOnline, syncStatus, pendingItems, lastSyncTime, triggerSync } = useSyncContext();
  const [stats, setStats] = useState(null);

  useEffect(() => {
    const loadStats = async () => {
      try {
        const response = await fetch('/api/stats', {
          headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
        });
        if (response.ok) {
          setStats(await response.json());
        }
      } catch (error) {
        console.error('Failed to load stats');
      }
    };

    loadStats();
    const interval = setInterval(loadStats, 30000); // Every 30 seconds

    return () => clearInterval(interval);
  }, []);

  return (
    <div className="sync-status">
      <div className="status-indicator">
        {isOnline ? (
          <div className="online">
            <span className="dot">🟢</span>
            <span>Online</span>
          </div>
        ) : (
          <div className="offline">
            <span className="dot">🔴</span>
            <span>Offline</span>
          </div>
        )}
      </div>

      <div className="sync-info">
        <p>Sync Status: {syncStatus}</p>
        {pendingItems > 0 && (
          <p className="warning">⏱️ {pendingItems} items waiting to sync</p>
        )}
        {lastSyncTime && (
          <p>Last Sync: {new Date(lastSyncTime).toLocaleTimeString()}</p>
        )}
      </div>

      <div className="statistics">
        {stats && (
          <>
            <div className="stat">
              <span className="label">Patients:</span>
              <span className="value">{stats.patients}</span>
            </div>
            <div className="stat">
              <span className="label">Studies:</span>
              <span className="value">{stats.studies}</span>
            </div>
            <div className="stat">
              <span className="label">Reports:</span>
              <span className="value">{stats.reports}</span>
            </div>
          </>
        )}
      </div>

      {isOnline && pendingItems > 0 && (
        <button onClick={triggerSync} disabled={syncStatus === 'syncing'}>
          {syncStatus === 'syncing' ? '⏳ Syncing...' : '↻ Sync Now'}
        </button>
      )}
    </div>
  );
};

// =============================================
// Main App Component
// =============================================

export default function GotgRisApp() {
  const [user, setUser] = useState(null);
  const [activeTab, setActiveTab] = useState('patients');

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (token) {
      const user = JSON.parse(localStorage.getItem('user') || '{}');
      setUser(user);
    } else {
      window.location.href = '/login';
    }
  }, []);

  if (!user) {
    return <div>Loading...</div>;
  }

  return (
    <OfflineSyncProvider>
      <div className="gotg-ris-app">
        <nav className="navbar">
          <h1>GOTG-RIS</h1>
          <div className="nav-items">
            <button
              className={`nav-button ${activeTab === 'patients' ? 'active' : ''}`}
              onClick={() => setActiveTab('patients')}
            >
              👥 Patients
            </button>
            <button
              className={`nav-button ${activeTab === 'studies' ? 'active' : ''}`}
              onClick={() => setActiveTab('studies')}
            >
              🔬 Studies
            </button>
            <button
              className={`nav-button ${activeTab === 'sync' ? 'active' : ''}`}
              onClick={() => setActiveTab('sync')}
            >
              ↻ Sync
            </button>
            <div className="user-info">
              {user.full_name} ({user.role})
            </div>
          </div>
        </nav>

        <div className="main-content">
          {activeTab === 'patients' && <PatientManager />}
          {activeTab === 'studies' && <StudyManager />}
          {activeTab === 'sync' && <SyncStatus />}
        </div>
      </div>
    </OfflineSyncProvider>
  );
}
