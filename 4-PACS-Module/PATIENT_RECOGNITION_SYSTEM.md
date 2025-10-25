# 🤖 Patient Recognition & Accessibility System

**Helping Patients Who Can't Communicate or Fill Forms**

---

## 🎯 Problem Statement

Many patients arrive at the clinic unable to:
- Fill out registration forms (stroke, dementia, severe illness)
- Communicate verbally (trauma, intubated, unconscious)
- Remember their details (memory loss, confusion)
- Write or type (physical disabilities, tremors)

**Current Impact:**
- Delays in treatment while searching for patient records
- Risk of duplicate records
- Errors in patient identification
- Staff frustration and wasted time
- Patient and family distress

**Solution:** Lightweight AI-powered patient recognition system that works offline

---

## 🏗️ TASK CATEGORY 10: PATIENT RECOGNITION SYSTEM

### Task 10.1: Facial Recognition for Patient Identification
**Priority:** 🔴 CRITICAL  
**Time:** 6 days  
**Goal:** Instantly identify returning patients using facial recognition

#### Problem
Patients who can't communicate or remember details cause delays and errors

#### Solution: Lightweight Facial Recognition with Privacy Protection

**10.1.1 Select Lightweight Face Recognition Model**

**Recommended Models:**

1. **FaceNet (MobileNet variant)** - Best balance
   - Size: 4 MB
   - Speed: 30ms per face on CPU
   - Accuracy: 99.2% on LFW dataset
   - Runs on: CPU, no GPU needed
   - Offline: ✅ Yes

2. **InsightFace (ArcFace-MobileNet)** - Most accurate
   - Size: 6 MB
   - Speed: 50ms per face on CPU
   - Accuracy: 99.5% on LFW dataset
   - Runs on: CPU/GPU
   - Offline: ✅ Yes

3. **DeepFace (VGG-Face lightweight)** - Easiest integration
   - Size: 8 MB
   - Speed: 80ms per face on CPU
   - Accuracy: 98.9% on LFW dataset
   - Runs on: CPU
   - Offline: ✅ Yes

**Recommendation: FaceNet-MobileNet** (best speed/accuracy/size)

**10.1.2 Implement Face Recognition System**

**Architecture:**
```
┌─────────────────────────────────────────────────────────────┐
│              Patient Recognition Workflow                    │
└─────────────────────────────────────────────────────────────┘

1. Patient Arrives
   ↓
2. Webcam Captures Face
   ↓
3. Face Detection (MTCNN - 20ms)
   ↓
4. Face Alignment & Preprocessing
   ↓
5. Extract Face Embedding (512-dim vector)
   ↓
6. Search Local Database (< 100ms for 10,000 patients)
   ↓
7. Match Found?
   ├─ YES → Load Patient Record (< 50ms)
   │         Show for Confirmation
   │         ↓
   │         Confirmed? → Start Workflow
   │
   └─ NO → New Patient Registration
             Capture Face + Details
             Store Embedding
```

**Database Schema:**
```sql
CREATE TABLE patient_face_embeddings (
    id INTEGER PRIMARY KEY,
    patient_id INTEGER NOT NULL,
    embedding BLOB NOT NULL,  -- 512-dim float32 vector
    photo_path VARCHAR(255),
    captured_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    quality_score FLOAT,  -- 0-1, higher is better
    capture_conditions JSON,  -- lighting, angle, etc.
    active BOOLEAN DEFAULT TRUE,
    
    FOREIGN KEY (patient_id) REFERENCES patients(id),
    INDEX idx_patient_id (patient_id),
    INDEX idx_active (active)
);

-- For fast similarity search
CREATE TABLE face_embedding_index (
    id INTEGER PRIMARY KEY,
    patient_id INTEGER NOT NULL,
    embedding_compressed BLOB,  -- Quantized for faster search
    last_seen TIMESTAMP,
    match_count INTEGER DEFAULT 0,
    
    INDEX idx_last_seen (last_seen)
);
```

**Implementation:**
```python
import cv2
import numpy as np
from facenet_pytorch import MTCNN, InceptionResnetV1
import sqlite3
from sklearn.metrics.pairwise import cosine_similarity

class PatientFaceRecognition:
    def __init__(self, db_path='patient_faces.db'):
        # Load lightweight models
        self.face_detector = MTCNN(
            keep_all=False,
            device='cpu',
            min_face_size=40,
            thresholds=[0.6, 0.7, 0.7]
        )
        
        self.face_encoder = InceptionResnetV1(
            pretrained='vggface2',
            device='cpu'
        ).eval()
        
        self.db = sqlite3.connect(db_path)
        self.similarity_threshold = 0.6  # Adjust based on testing
        
    def capture_and_identify(self, image_or_camera=0):
        """
        Capture face from camera and identify patient
        
        Args:
            image_or_camera: Image array or camera index
            
        Returns:
            dict: Patient info if found, None if new patient
        """
        # Capture image
        if isinstance(image_or_camera, int):
            cap = cv2.VideoCapture(image_or_camera)
            ret, frame = cap.read()
            cap.release()
            if not ret:
                return {'error': 'Failed to capture image'}
        else:
            frame = image_or_camera
        
        # Detect face
        face, prob = self.face_detector(frame, return_prob=True)
        
        if face is None:
            return {'error': 'No face detected', 'suggestion': 'Please face the camera'}
        
        if prob < 0.9:
            return {'error': 'Face detection confidence too low', 'confidence': prob}
        
        # Extract embedding
        embedding = self.face_encoder(face.unsqueeze(0)).detach().numpy()[0]
        
        # Search database
        matches = self.search_similar_faces(embedding)
        
        if matches:
            best_match = matches[0]
            if best_match['similarity'] > self.similarity_threshold:
                # Load patient details
                patient = self.get_patient_details(best_match['patient_id'])
                return {
                    'found': True,
                    'patient': patient,
                    'similarity': best_match['similarity'],
                    'confidence': 'high' if best_match['similarity'] > 0.8 else 'medium',
                    'last_visit': best_match['last_seen'],
                    'embedding': embedding  # For updating
                }
        
        return {
            'found': False,
            'embedding': embedding,
            'message': 'New patient - please register'
        }
    
    def search_similar_faces(self, query_embedding, top_k=5):
        """
        Search for similar faces in database
        Fast cosine similarity search
        """
        cursor = self.db.cursor()
        
        # Get all embeddings (optimized with indexing)
        cursor.execute("""
            SELECT patient_id, embedding, last_seen 
            FROM patient_face_embeddings 
            WHERE active = TRUE
        """)
        
        results = []
        for row in cursor.fetchall():
            patient_id, embedding_blob, last_seen = row
            stored_embedding = np.frombuffer(embedding_blob, dtype=np.float32)
            
            # Calculate cosine similarity
            similarity = cosine_similarity(
                query_embedding.reshape(1, -1),
                stored_embedding.reshape(1, -1)
            )[0][0]
            
            results.append({
                'patient_id': patient_id,
                'similarity': float(similarity),
                'last_seen': last_seen
            })
        
        # Sort by similarity
        results.sort(key=lambda x: x['similarity'], reverse=True)
        return results[:top_k]
    
    def register_new_patient(self, patient_id, embedding, photo_path, quality_score):
        """
        Register new patient face embedding
        """
        cursor = self.db.cursor()
        
        # Store embedding
        embedding_blob = embedding.astype(np.float32).tobytes()
        
        cursor.execute("""
            INSERT INTO patient_face_embeddings 
            (patient_id, embedding, photo_path, quality_score)
            VALUES (?, ?, ?, ?)
        """, (patient_id, embedding_blob, photo_path, quality_score))
        
        self.db.commit()
        
        return cursor.lastrowid
    
    def update_embedding(self, patient_id, new_embedding):
        """
        Update patient embedding (aging, appearance changes)
        Uses exponential moving average to adapt
        """
        cursor = self.db.cursor()
        
        # Get current embedding
        cursor.execute("""
            SELECT embedding FROM patient_face_embeddings 
            WHERE patient_id = ? AND active = TRUE
            ORDER BY captured_date DESC LIMIT 1
        """, (patient_id,))
        
        row = cursor.fetchone()
        if row:
            old_embedding = np.frombuffer(row[0], dtype=np.float32)
            
            # Exponential moving average (70% old, 30% new)
            updated_embedding = 0.7 * old_embedding + 0.3 * new_embedding
            
            # Store updated embedding
            embedding_blob = updated_embedding.astype(np.float32).tobytes()
            cursor.execute("""
                INSERT INTO patient_face_embeddings 
                (patient_id, embedding, quality_score)
                VALUES (?, ?, ?)
            """, (patient_id, embedding_blob, 0.9))
            
            self.db.commit()
    
    def get_patient_details(self, patient_id):
        """
        Retrieve patient details from main database
        """
        cursor = self.db.cursor()
        cursor.execute("""
            SELECT p.*, 
                   COUNT(v.id) as visit_count,
                   MAX(v.visit_date) as last_visit
            FROM patients p
            LEFT JOIN visits v ON p.id = v.patient_id
            WHERE p.id = ?
            GROUP BY p.id
        """, (patient_id,))
        
        row = cursor.fetchone()
        if row:
            return {
                'id': row[0],
                'id_number': row[1],
                'first_name': row[2],
                'surname': row[3],
                'date_of_birth': row[4],
                'medical_aid': row[5],
                'member_number': row[6],
                'visit_count': row[7],
                'last_visit': row[8]
            }
        return None
```

**10.1.3 Create Patient Recognition UI**

```
┌─────────────────────────────────────────────────────────────┐
│  Patient Recognition - Quick Check-In                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │                                                      │    │
│  │         [Live Camera Feed]                          │    │
│  │                                                      │    │
│  │         Please look at the camera                   │    │
│  │         Detecting face...                           │    │
│  │                                                      │    │
│  └────────────────────────────────────────────────────┘    │
│                                                              │
│  Status: 🔍 Searching database...                           │
│                                                              │
│  [📷 Capture] [🔄 Retry] [⌨️ Manual Entry]                  │
│                                                              │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  Patient Found! ✅                                           │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────┐  John Smith                                   │
│  │  Photo   │  ID: 8001015009087                            │
│  │  [Image] │  DOB: 1980-01-01 (45 years)                   │
│  └──────────┘  Medical Aid: Discovery Health                │
│                Member: 1234567890                            │
│                                                              │
│  Last Visit: 2024-12-10 (5 weeks ago)                       │
│  Total Visits: 12                                            │
│                                                              │
│  Previous Conditions:                                        │
│  • Hypertension (controlled)                                │
│  • Type 2 Diabetes                                           │
│                                                              │
│  Confidence: ⭐⭐⭐⭐⭐ 95% match                              │
│                                                              │
│  Is this correct?                                            │
│  [✅ Yes, Continue] [❌ No, Try Again] [⌨️ Manual Search]    │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

**10.1.4 Add Privacy & Security Features**

```python
class FaceRecognitionSecurity:
    """
    POPI Act compliant face recognition
    """
    
    def __init__(self):
        self.consent_required = True
        self.retention_days = 365 * 7  # 7 years
        self.encryption_key = self.load_encryption_key()
    
    def get_patient_consent(self, patient_id):
        """
        Check if patient consented to facial recognition
        """
        cursor = self.db.cursor()
        cursor.execute("""
            SELECT consent_given, consent_date 
            FROM patient_consents 
            WHERE patient_id = ? 
            AND consent_type = 'facial_recognition'
            AND (withdrawal_date IS NULL OR withdrawal_date > CURRENT_DATE)
        """, (patient_id,))
        
        result = cursor.fetchone()
        return result is not None and result[0] == True
    
    def encrypt_embedding(self, embedding):
        """
        Encrypt face embedding before storage
        """
        from cryptography.fernet import Fernet
        f = Fernet(self.encryption_key)
        
        embedding_bytes = embedding.astype(np.float32).tobytes()
        encrypted = f.encrypt(embedding_bytes)
        return encrypted
    
    def log_face_recognition_access(self, patient_id, user_id, action):
        """
        Log all face recognition access for audit
        """
        cursor = self.db.cursor()
        cursor.execute("""
            INSERT INTO face_recognition_audit_log 
            (patient_id, user_id, action, timestamp, workstation_id)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP, ?)
        """, (patient_id, user_id, action, self.get_workstation_id()))
        
        self.db.commit()
    
    def delete_old_embeddings(self):
        """
        Delete embeddings older than retention period
        POPI Act compliance
        """
        cursor = self.db.cursor()
        cursor.execute("""
            DELETE FROM patient_face_embeddings 
            WHERE captured_date < DATE('now', '-{} days')
        """.format(self.retention_days))
        
        self.db.commit()
```

**Acceptance Criteria:**
- ✅ Identify patient in < 2 seconds
- ✅ 95%+ accuracy on returning patients
- ✅ Works offline (no internet needed)
- ✅ Runs on CPU (no GPU required)
- ✅ POPI Act compliant
- ✅ Encrypted storage
- ✅ Complete audit trail

---


### Task 10.2: Lightweight OCR for Forms & Documents
**Priority:** 🔴 CRITICAL  
**Time:** 4 days  
**Goal:** Extract text from documents with minimal typing

#### Problem
Staff must manually type information from ID documents, medical cards, referral letters

#### Solution: Fast, Accurate OCR with Smart Field Detection

**10.2.1 Select Lightweight OCR Engine**

**Recommended OCR Engines:**

1. **Tesseract 5.x** - Best for general text
   - Size: 30 MB (with English + Afrikaans models)
   - Speed: 200ms per page on