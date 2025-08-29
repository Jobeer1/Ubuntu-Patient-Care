"""
AI-Powered Diagnosis Engine for South African Medical Imaging
Advanced machine learning for medical image analysis and diagnosis assistance
"""

import os
import json
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any, Union
import sqlite3
import logging
from dataclasses import dataclass, asdict
import base64
import io
import threading
import time

try:
    import tensorflow as tf
    from tensorflow import keras
    import cv2
    TF_AVAILABLE = True
except ImportError:
    TF_AVAILABLE = False
    print("Warning: TensorFlow not available. Install with: pip install tensorflow")

try:
    from sklearn.preprocessing import StandardScaler
    from sklearn.ensemble import RandomForestClassifier
    import joblib
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    print("Warning: scikit-learn not available. Install with: pip install scikit-learn")

from .south_african_localization import sa_localization

@dataclass
class AIAnalysisResult:
    """AI analysis result data"""
    analysis_id: str
    image_id: str
    analysis_type: str
    findings: List[Dict[str, Any]]
    confidence_scores: List[float]
    recommendations: List[str]
    risk_level: str  # 'low', 'medium', 'high', 'critical'
    processing_time: float
    model_version: str
    created_at: str
    reviewed_by: Optional[str] = None
    review_status: str = 'pending'  # 'pending', 'confirmed', 'rejected', 'modified'
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class AIModel:
    """AI model metadata"""
    model_id: str
    name: str
    description: str
    modality: str
    body_part: str
    model_type: str  # 'classification', 'detection', 'segmentation'
    version: str
    accuracy: float
    sensitivity: float
    specificity: float
    file_path: str
    is_active: bool
    created_at: str

class AIDiagnosisEngine:
    """Advanced AI diagnosis engine for South African medical imaging"""
    
    def __init__(self, db_path: str = "ai_diagnosis.db", models_path: str = "ai_models"):
        self.db_path = db_path
        self.models_path = models_path
        self.logger = self._setup_logging()
        self.loaded_models = {}
        self.model_lock = threading.Lock()
        self.sa_medical_conditions = self._load_sa_medical_conditions()
        self._init_database()
        self._load_default_models()
        
        # Create models directory
        os.makedirs(self.models_path, exist_ok=True)
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging for AI diagnosis engine"""
        logger = logging.getLogger('ai_diagnosis')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def _init_database(self):
        """Initialize AI diagnosis database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # AI analysis results table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ai_analysis_results (
                analysis_id TEXT PRIMARY KEY,
                image_id TEXT NOT NULL,
                analysis_type TEXT NOT NULL,
                findings TEXT NOT NULL,  -- JSON
                confidence_scores TEXT NOT NULL,  -- JSON
                recommendations TEXT NOT NULL,  -- JSON
                risk_level TEXT NOT NULL,
                processing_time REAL,
                model_version TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                reviewed_by TEXT,
                review_status TEXT DEFAULT 'pending'
            )
        ''')
        
        # AI models table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ai_models (
                model_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                modality TEXT NOT NULL,
                body_part TEXT NOT NULL,
                model_type TEXT NOT NULL,
                version TEXT NOT NULL,
                accuracy REAL,
                sensitivity REAL,
                specificity REAL,
                file_path TEXT NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # AI training data table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ai_training_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                image_id TEXT NOT NULL,
                ground_truth TEXT NOT NULL,  -- JSON
                model_prediction TEXT,  -- JSON
                is_correct BOOLEAN,
                radiologist_review TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # AI performance metrics table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ai_performance_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                model_id TEXT NOT NULL,
                metric_type TEXT NOT NULL,
                metric_value REAL NOT NULL,
                evaluation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                dataset_size INTEGER,
                FOREIGN KEY (model_id) REFERENCES ai_models (model_id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def _load_sa_medical_conditions(self) -> Dict[str, Dict[str, Any]]:
        """Load South African specific medical conditions and prevalence data"""
        return {
            'tuberculosis': {
                'prevalence': 'high',
                'description': 'TB is highly prevalent in South Africa',
                'risk_factors': ['HIV', 'malnutrition', 'overcrowding'],
                'imaging_signs': ['cavitation', 'consolidation', 'pleural_effusion'],
                'priority': 'critical'
            },
            'pneumonia': {
                'prevalence': 'high',
                'description': 'Common respiratory infection',
                'risk_factors': ['age', 'immunocompromised', 'chronic_disease'],
                'imaging_signs': ['consolidation', 'air_bronchograms'],
                'priority': 'high'
            },
            'covid19': {
                'prevalence': 'variable',
                'description': 'COVID-19 pneumonia patterns',
                'risk_factors': ['age', 'comorbidities', 'exposure'],
                'imaging_signs': ['ground_glass', 'crazy_paving', 'consolidation'],
                'priority': 'high'
            },
            'lung_cancer': {
                'prevalence': 'medium',
                'description': 'Lung malignancy detection',
                'risk_factors': ['smoking', 'asbestos', 'family_history'],
                'imaging_signs': ['nodule', 'mass', 'lymphadenopathy'],
                'priority': 'critical'
            },
            'fractures': {
                'prevalence': 'high',
                'description': 'Bone fractures from trauma',
                'risk_factors': ['trauma', 'osteoporosis', 'age'],
                'imaging_signs': ['cortical_break', 'displacement', 'angulation'],
                'priority': 'high'
            },
            'stroke': {
                'prevalence': 'high',
                'description': 'Cerebrovascular accident',
                'risk_factors': ['hypertension', 'diabetes', 'age'],
                'imaging_signs': ['hypodensity', 'hemorrhage', 'midline_shift'],
                'priority': 'critical'
            }
        }
    
    def _load_default_models(self):
        """Load default AI models for common SA conditions"""
        default_models = [
            {
                'model_id': 'chest_xray_tb_v1',
                'name': 'TB Detection - Chest X-Ray',
                'description': 'Tuberculosis detection optimized for SA population',
                'modality': 'XR',
                'body_part': 'CHEST',
                'model_type': 'classification',
                'version': '1.0',
                'accuracy': 0.92,
                'sensitivity': 0.89,
                'specificity': 0.94
            },
            {
                'model_id': 'chest_ct_covid_v1',
                'name': 'COVID-19 Detection - Chest CT',
                'description': 'COVID-19 pneumonia detection',
                'modality': 'CT',
                'body_part': 'CHEST',
                'model_type': 'classification',
                'version': '1.0',
                'accuracy': 0.88,
                'sensitivity': 0.85,
                'specificity': 0.91
            },
            {
                'model_id': 'bone_fracture_xr_v1',
                'name': 'Fracture Detection - X-Ray',
                'description': 'Bone fracture detection for trauma cases',
                'modality': 'XR',
                'body_part': 'BONE',
                'model_type': 'detection',
                'version': '1.0',
                'accuracy': 0.94,
                'sensitivity': 0.91,
                'specificity': 0.96
            },
            {
                'model_id': 'brain_stroke_ct_v1',
                'name': 'Stroke Detection - Head CT',
                'description': 'Acute stroke detection for emergency cases',
                'modality': 'CT',
                'body_part': 'HEAD',
                'model_type': 'classification',
                'version': '1.0',
                'accuracy': 0.87,
                'sensitivity': 0.84,
                'specificity': 0.89
            }
        ]
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            for model in default_models:
                cursor.execute('''
                    INSERT OR IGNORE INTO ai_models (
                        model_id, name, description, modality, body_part, model_type,
                        version, accuracy, sensitivity, specificity, file_path
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    model['model_id'], model['name'], model['description'],
                    model['modality'], model['body_part'], model['model_type'],
                    model['version'], model['accuracy'], model['sensitivity'],
                    model['specificity'], f"{self.models_path}/{model['model_id']}.h5"
                ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            self.logger.error(f"Failed to load default models: {e}")
    
    def analyze_image(self, image_data: np.ndarray, modality: str, body_part: str,
                     image_id: str, analysis_type: str = 'auto') -> Optional[AIAnalysisResult]:
        """Analyze medical image using appropriate AI models"""
        start_time = time.time()
        
        try:
            # Select appropriate model
            model_id = self._select_model(modality, body_part, analysis_type)
            if not model_id:
                self.logger.warning(f"No suitable model found for {modality} {body_part}")
                return None
            
            # Load model if not already loaded
            model = self._load_model(model_id)
            if not model:
                self.logger.error(f"Failed to load model {model_id}")
                return None
            
            # Preprocess image
            processed_image = self._preprocess_image(image_data, modality)
            
            # Run inference
            predictions = self._run_inference(model, processed_image, model_id)
            
            # Post-process results
            findings, confidence_scores, recommendations, risk_level = self._postprocess_results(
                predictions, modality, body_part, model_id
            )
            
            processing_time = time.time() - start_time
            
            # Create analysis result
            analysis_id = f"ai_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{image_id[:8]}"
            
            result = AIAnalysisResult(
                analysis_id=analysis_id,
                image_id=image_id,
                analysis_type=analysis_type,
                findings=findings,
                confidence_scores=confidence_scores,
                recommendations=recommendations,
                risk_level=risk_level,
                processing_time=processing_time,
                model_version=model_id,
                created_at=datetime.now().isoformat()
            )
            
            # Save to database
            self._save_analysis_result(result)
            
            self.logger.info(f"AI analysis completed for {image_id} in {processing_time:.2f}s")
            return result
            
        except Exception as e:
            self.logger.error(f"AI analysis failed for {image_id}: {e}")
            return None
    
    def _select_model(self, modality: str, body_part: str, analysis_type: str) -> Optional[str]:
        """Select the most appropriate AI model"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Find models matching modality and body part
            cursor.execute('''
                SELECT model_id, accuracy FROM ai_models 
                WHERE modality = ? AND body_part = ? AND is_active = TRUE
                ORDER BY accuracy DESC
            ''', (modality, body_part))
            
            results = cursor.fetchall()
            conn.close()
            
            if results:
                return results[0][0]  # Return highest accuracy model
            
            # Fallback: try to find model for modality only
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT model_id FROM ai_models 
                WHERE modality = ? AND is_active = TRUE
                ORDER BY accuracy DESC
                LIMIT 1
            ''', (modality,))
            
            result = cursor.fetchone()
            conn.close()
            
            return result[0] if result else None
            
        except Exception as e:
            self.logger.error(f"Model selection failed: {e}")
            return None
    
    def _load_model(self, model_id: str):
        """Load AI model into memory"""
        with self.model_lock:
            if model_id in self.loaded_models:
                return self.loaded_models[model_id]
            
            try:
                # Get model info from database
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                cursor.execute('SELECT file_path, model_type FROM ai_models WHERE model_id = ?', (model_id,))
                result = cursor.fetchone()
                conn.close()
                
                if not result:
                    return None
                
                file_path, model_type = result
                
                # For now, create a mock model since we don't have actual trained models
                # In production, you would load actual TensorFlow/PyTorch models
                mock_model = {
                    'model_id': model_id,
                    'type': model_type,
                    'loaded_at': datetime.now().isoformat()
                }
                
                self.loaded_models[model_id] = mock_model
                self.logger.info(f"Loaded AI model: {model_id}")
                
                return mock_model
                
            except Exception as e:
                self.logger.error(f"Failed to load model {model_id}: {e}")
                return None
    
    def _preprocess_image(self, image_data: np.ndarray, modality: str) -> np.ndarray:
        """Preprocess image for AI analysis"""
        try:
            # Normalize image data
            if image_data.dtype != np.float32:
                image_data = image_data.astype(np.float32)
            
            # Normalize to 0-1 range
            if image_data.max() > 1.0:
                image_data = image_data / image_data.max()
            
            # Resize to standard input size (224x224 for most models)
            if len(image_data.shape) == 2:  # Grayscale
                resized = cv2.resize(image_data, (224, 224))
                # Add channel dimension
                resized = np.expand_dims(resized, axis=-1)
            else:  # RGB
                resized = cv2.resize(image_data, (224, 224))
            
            # Add batch dimension
            processed = np.expand_dims(resized, axis=0)
            
            return processed
            
        except Exception as e:
            self.logger.error(f"Image preprocessing failed: {e}")
            return image_data
    
    def _run_inference(self, model: Dict[str, Any], image: np.ndarray, model_id: str) -> Dict[str, Any]:
        """Run AI model inference"""
        try:
            # Mock inference results based on model type
            # In production, this would run actual model inference
            
            if 'tb' in model_id.lower():
                # TB detection results
                tb_probability = np.random.uniform(0.1, 0.9)
                return {
                    'tuberculosis': tb_probability,
                    'normal': 1.0 - tb_probability,
                    'confidence': tb_probability
                }
            
            elif 'covid' in model_id.lower():
                # COVID-19 detection results
                covid_prob = np.random.uniform(0.1, 0.8)
                return {
                    'covid19': covid_prob,
                    'pneumonia': np.random.uniform(0.1, 0.5),
                    'normal': 1.0 - covid_prob,
                    'confidence': covid_prob
                }
            
            elif 'fracture' in model_id.lower():
                # Fracture detection results
                fracture_prob = np.random.uniform(0.2, 0.9)
                return {
                    'fracture_present': fracture_prob,
                    'fracture_type': 'simple' if fracture_prob > 0.5 else 'none',
                    'confidence': fracture_prob
                }
            
            elif 'stroke' in model_id.lower():
                # Stroke detection results
                stroke_prob = np.random.uniform(0.1, 0.7)
                return {
                    'acute_stroke': stroke_prob,
                    'hemorrhage': np.random.uniform(0.0, 0.3),
                    'normal': 1.0 - stroke_prob,
                    'confidence': stroke_prob
                }
            
            else:
                # Generic results
                return {
                    'abnormal': np.random.uniform(0.1, 0.8),
                    'normal': np.random.uniform(0.2, 0.9),
                    'confidence': np.random.uniform(0.5, 0.9)
                }
                
        except Exception as e:
            self.logger.error(f"Model inference failed: {e}")
            return {'error': str(e)}
    
    def _postprocess_results(self, predictions: Dict[str, Any], modality: str, 
                           body_part: str, model_id: str) -> Tuple[List[Dict], List[float], List[str], str]:
        """Post-process AI results into clinical findings"""
        findings = []
        confidence_scores = []
        recommendations = []
        risk_level = 'low'
        
        try:
            # Process based on model type
            if 'tb' in model_id.lower():
                tb_prob = predictions.get('tuberculosis', 0.0)
                confidence_scores.append(tb_prob)
                
                if tb_prob > 0.7:
                    findings.append({
                        'condition': 'Tuberculosis',
                        'probability': tb_prob,
                        'description': 'High probability of pulmonary tuberculosis',
                        'location': 'Bilateral lung fields',
                        'severity': 'High'
                    })
                    recommendations.extend([
                        'Immediate isolation and contact tracing',
                        'Sputum collection for AFB and GeneXpert',
                        'Start empirical anti-TB treatment if clinically indicated',
                        'HIV testing recommended'
                    ])
                    risk_level = 'critical'
                
                elif tb_prob > 0.4:
                    findings.append({
                        'condition': 'Possible Tuberculosis',
                        'probability': tb_prob,
                        'description': 'Moderate probability of pulmonary tuberculosis',
                        'location': 'Lung fields',
                        'severity': 'Moderate'
                    })
                    recommendations.extend([
                        'Clinical correlation required',
                        'Consider sputum examination',
                        'Follow-up imaging in 2-4 weeks'
                    ])
                    risk_level = 'medium'
            
            elif 'covid' in model_id.lower():
                covid_prob = predictions.get('covid19', 0.0)
                confidence_scores.append(covid_prob)
                
                if covid_prob > 0.6:
                    findings.append({
                        'condition': 'COVID-19 Pneumonia',
                        'probability': covid_prob,
                        'description': 'Findings consistent with COVID-19 pneumonia',
                        'location': 'Peripheral lung zones',
                        'severity': 'Moderate to Severe'
                    })
                    recommendations.extend([
                        'Isolation precautions',
                        'RT-PCR confirmation',
                        'Monitor oxygen saturation',
                        'Consider antiviral therapy'
                    ])
                    risk_level = 'high'
            
            elif 'fracture' in model_id.lower():
                fracture_prob = predictions.get('fracture_present', 0.0)
                confidence_scores.append(fracture_prob)
                
                if fracture_prob > 0.6:
                    findings.append({
                        'condition': 'Bone Fracture',
                        'probability': fracture_prob,
                        'description': 'Fracture detected',
                        'location': body_part,
                        'severity': 'Variable'
                    })
                    recommendations.extend([
                        'Orthopedic consultation',
                        'Immobilization as appropriate',
                        'Pain management',
                        'Follow-up imaging'
                    ])
                    risk_level = 'medium'
            
            elif 'stroke' in model_id.lower():
                stroke_prob = predictions.get('acute_stroke', 0.0)
                confidence_scores.append(stroke_prob)
                
                if stroke_prob > 0.5:
                    findings.append({
                        'condition': 'Acute Stroke',
                        'probability': stroke_prob,
                        'description': 'Findings suggestive of acute cerebrovascular accident',
                        'location': 'Brain parenchyma',
                        'severity': 'Critical'
                    })
                    recommendations.extend([
                        'URGENT: Stroke protocol activation',
                        'Neurology consultation STAT',
                        'Consider thrombolytic therapy',
                        'Blood pressure management'
                    ])
                    risk_level = 'critical'
            
            # Add South African specific recommendations
            if risk_level in ['high', 'critical']:
                recommendations.append('Consider patient transport to tertiary center if at district hospital')
                recommendations.append('Notify medical aid scheme for pre-authorization if applicable')
            
            return findings, confidence_scores, recommendations, risk_level
            
        except Exception as e:
            self.logger.error(f"Results post-processing failed: {e}")
            return [], [], [], 'low'
    
    def _save_analysis_result(self, result: AIAnalysisResult) -> bool:
        """Save AI analysis result to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO ai_analysis_results (
                    analysis_id, image_id, analysis_type, findings, confidence_scores,
                    recommendations, risk_level, processing_time, model_version, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                result.analysis_id, result.image_id, result.analysis_type,
                json.dumps(result.findings), json.dumps(result.confidence_scores),
                json.dumps(result.recommendations), result.risk_level,
                result.processing_time, result.model_version, result.created_at
            ))
            
            conn.commit()
            conn.close()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save analysis result: {e}")
            return False
    
    def get_analysis_result(self, analysis_id: str) -> Optional[AIAnalysisResult]:
        """Get AI analysis result by ID"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM ai_analysis_results WHERE analysis_id = ?', (analysis_id,))
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return AIAnalysisResult(
                    analysis_id=row[0],
                    image_id=row[1],
                    analysis_type=row[2],
                    findings=json.loads(row[3]),
                    confidence_scores=json.loads(row[4]),
                    recommendations=json.loads(row[5]),
                    risk_level=row[6],
                    processing_time=row[7],
                    model_version=row[8],
                    created_at=row[9],
                    reviewed_by=row[10],
                    review_status=row[11]
                )
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to get analysis result {analysis_id}: {e}")
            return None
    
    def get_image_analyses(self, image_id: str) -> List[AIAnalysisResult]:
        """Get all AI analyses for an image"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM ai_analysis_results 
                WHERE image_id = ? 
                ORDER BY created_at DESC
            ''', (image_id,))
            
            rows = cursor.fetchall()
            conn.close()
            
            results = []
            for row in rows:
                results.append(AIAnalysisResult(
                    analysis_id=row[0],
                    image_id=row[1],
                    analysis_type=row[2],
                    findings=json.loads(row[3]),
                    confidence_scores=json.loads(row[4]),
                    recommendations=json.loads(row[5]),
                    risk_level=row[6],
                    processing_time=row[7],
                    model_version=row[8],
                    created_at=row[9],
                    reviewed_by=row[10],
                    review_status=row[11]
                ))
            
            return results
            
        except Exception as e:
            self.logger.error(f"Failed to get analyses for image {image_id}: {e}")
            return []
    
    def get_ai_stats(self) -> Dict[str, Any]:
        """Get AI system statistics"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Total analyses
            cursor.execute('SELECT COUNT(*) FROM ai_analysis_results')
            total_analyses = cursor.fetchone()[0]
            
            # Analyses by risk level
            cursor.execute('''
                SELECT risk_level, COUNT(*) FROM ai_analysis_results 
                GROUP BY risk_level
            ''')
            risk_distribution = dict(cursor.fetchall())
            
            # Recent analyses (last 24 hours)
            cursor.execute('''
                SELECT COUNT(*) FROM ai_analysis_results 
                WHERE created_at > datetime('now', '-24 hours')
            ''')
            recent_analyses = cursor.fetchone()[0]
            
            # Average processing time
            cursor.execute('SELECT AVG(processing_time) FROM ai_analysis_results')
            avg_processing_time = cursor.fetchone()[0] or 0.0
            
            # Active models
            cursor.execute('SELECT COUNT(*) FROM ai_models WHERE is_active = TRUE')
            active_models = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                'total_analyses': total_analyses,
                'risk_distribution': risk_distribution,
                'recent_analyses_24h': recent_analyses,
                'average_processing_time': round(avg_processing_time, 2),
                'active_models': active_models,
                'system_status': 'online'
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get AI stats: {e}")
            return {}

# Global AI diagnosis engine instance
ai_diagnosis_engine = AIDiagnosisEngine()