CREATE TABLE indexing_status (
                id INTEGER PRIMARY KEY,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                status TEXT DEFAULT 'running',
                folders_scanned INTEGER DEFAULT 0,
                files_processed INTEGER DEFAULT 0,
                patients_found INTEGER DEFAULT 0,
                errors INTEGER DEFAULT 0,
                current_folder TEXT
            );;
CREATE TABLE patient_studies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id TEXT NOT NULL,
                patient_name TEXT,
                patient_birth_date TEXT,
                patient_sex TEXT,
                study_date TEXT,
                study_description TEXT,
                modality TEXT,
                folder_path TEXT NOT NULL,
                dicom_file_count INTEGER DEFAULT 0,
                folder_size_mb REAL DEFAULT 0,
                last_indexed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(patient_id, folder_path)
            );;
CREATE TABLE sqlite_sequence(name,seq);;
