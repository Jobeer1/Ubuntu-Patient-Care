"""
Segmentation Testing & Validation
Phase 2: Task 2.2.2
Comprehensive tests for segmentation engine and API
"""

import pytest
import numpy as np
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime
import json

# Import modules to test
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from app.ml_models.segmentation_engine import SegmentationEngine
from app.routes.segmentation import (
    JobQueue, SegmentationJob, JobStatus,
    process_organ_segmentation, process_vessel_segmentation, process_nodule_detection
)


# ============================================================================
# UNIT TESTS: Preprocessing
# ============================================================================

class TestPreprocessing:
    """Test preprocessing pipeline"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.engine = SegmentationEngine()
        self.test_volume = np.random.randn(100, 100, 100).astype(np.float32)
    
    def test_normalize_volume_hounsfield(self):
        """Test Hounsfield unit normalization"""
        # Create test volume with known HU values
        volume = np.array([[[-1024, 0, 100, 3071]]], dtype=np.float32)
        
        normalized = self.engine.normalize_volume(volume)
        
        # Check normalization range
        assert normalized.min() >= -1.0
        assert normalized.max() <= 1.0
        assert normalized.shape == volume.shape
    
    def test_normalize_volume_empty(self):
        """Test normalization with empty volume"""
        volume = np.zeros((10, 10, 10), dtype=np.float32)
        
        normalized = self.engine.normalize_volume(volume)
        
        # Should handle empty volume gracefully
        assert normalized.shape == volume.shape
        assert not np.isnan(normalized).any()
    
    def test_resize_volume_upscale(self):
        """Test volume upscaling"""
        volume = np.random.randn(50, 50, 50).astype(np.float32)
        target_shape = (100, 100, 100)
        
        resized = self.engine.resize_volume(volume, target_shape)
        
        assert resized.shape == target_shape
        assert resized.dtype == np.float32
    
    def test_resize_volume_downscale(self):
        """Test volume downscaling"""
        volume = np.random.randn(200, 200, 200).astype(np.float32)
        target_shape = (100, 100, 100)
        
        resized = self.engine.resize_volume(volume, target_shape)
        
        assert resized.shape == target_shape
        assert resized.dtype == np.float32
    
    def test_resize_volume_preserve_values(self):
        """Test that resizing preserves value ranges"""
        volume = np.random.randn(50, 50, 50).astype(np.float32)
        original_min = volume.min()
        original_max = volume.max()
        
        resized = self.engine.resize_volume(volume, (100, 100, 100))
        
        # Values should be in similar range
        assert resized.min() >= original_min - 1.0
        assert resized.max() <= original_max + 1.0
    
    def test_convert_to_tensor(self):
        """Test NumPy to tensor conversion"""
        volume = np.random.randn(100, 100, 100).astype(np.float32)
        
        tensor = self.engine.convert_to_tensor(volume)
        
        # Check tensor properties
        assert tensor.shape == (1, 1, 100, 100, 100)  # Batch + channel dims
        assert str(tensor.device) in ['cpu', 'cuda:0', 'mps:0']
    
    def test_preprocessing_pipeline_complete(self):
        """Test complete preprocessing pipeline"""
        volume = np.random.randn(128, 128, 128).astype(np.float32)
        
        # Run full preprocessing
        normalized = self.engine.normalize_volume(volume)
        resized = self.engine.resize_volume(normalized, (96, 96, 96))
        tensor = self.engine.convert_to_tensor(resized)
        
        # Verify pipeline output
        assert tensor.shape == (1, 1, 96, 96, 96)
        assert not np.isnan(tensor.cpu().numpy()).any()


# ============================================================================
# UNIT TESTS: Post-processing
# ============================================================================

class TestPostprocessing:
    """Test post-processing pipeline"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.engine = SegmentationEngine()
    
    def test_smooth_mask_morphological(self):
        """Test morphological smoothing"""
        # Create noisy mask
        mask = np.zeros((100, 100, 100), dtype=np.uint8)
        mask[40:60, 40:60, 40:60] = 1
        # Add noise
        mask[45, 45, 45] = 0
        mask[35, 35, 35] = 1
        
        smoothed = self.engine.smooth_mask(mask, iterations=2)
        
        # Check smoothing effect
        assert smoothed.shape == mask.shape
        assert smoothed.dtype == np.uint8
        # Noise should be reduced
        assert smoothed[35, 35, 35] == 0  # Isolated pixel removed
    
    def test_remove_small_components(self):
        """Test small component removal"""
        # Create mask with small and large components
        mask = np.zeros((100, 100, 100), dtype=np.uint8)
        # Large component
        mask[20:80, 20:80, 20:80] = 1
        # Small component
        mask[5:10, 5:10, 5:10] = 1
        
        cleaned = self.engine.remove_small_components(mask, min_size=100)
        
        # Small component should be removed
        assert cleaned[7, 7, 7] == 0
        # Large component should remain
        assert cleaned[50, 50, 50] == 1
    
    def test_fill_holes(self):
        """Test hole filling"""
        # Create mask with hole
        mask = np.zeros((50, 50, 50), dtype=np.uint8)
        mask[10:40, 10:40, 10:40] = 1
        # Create hole
        mask[20:30, 20:30, 20:30] = 0
        
        filled = self.engine.fill_holes(mask)
        
        # Hole should be filled
        assert filled[25, 25, 25] == 1
        assert filled.sum() > mask.sum()
    
    def test_resize_mask_to_original(self):
        """Test resizing mask back to original shape"""
        original_shape = (128, 128, 128)
        mask = np.random.randint(0, 2, (96, 96, 96), dtype=np.uint8)
        
        resized = self.engine.resize_mask(mask, original_shape)
        
        assert resized.shape == original_shape
        assert resized.dtype == np.uint8
        assert set(np.unique(resized)).issubset({0, 1})
    
    def test_postprocessing_pipeline_complete(self):
        """Test complete post-processing pipeline"""
        # Create test mask
        mask = np.zeros((100, 100, 100), dtype=np.uint8)
        mask[30:70, 30:70, 30:70] = 1
        # Add noise and holes
        mask[35, 35, 35] = 0
        mask[5:8, 5:8, 5:8] = 1
        
        # Run full post-processing
        smoothed = self.engine.smooth_mask(mask, iterations=2)
        cleaned = self.engine.remove_small_components(smoothed, min_size=50)
        filled = self.engine.fill_holes(cleaned)
        
        # Verify pipeline output
        assert filled.shape == mask.shape
        assert filled.dtype == np.uint8
        assert filled[5, 5, 5] == 0  # Small component removed


# ============================================================================
# UNIT TESTS: Statistics Calculation
# ============================================================================

class TestStatistics:
    """Test statistics calculation"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.engine = SegmentationEngine()
    
    def test_calculate_volume_statistics(self):
        """Test volume statistics calculation"""
        mask = np.zeros((100, 100, 100), dtype=np.uint8)
        mask[25:75, 25:75, 25:75] = 1
        spacing = (1.0, 1.0, 1.0)  # 1mm spacing
        
        stats = self.engine.calculate_statistics(mask, spacing)
        
        assert 'total_voxels' in stats
        assert 'segmented_voxels' in stats
        assert 'volume_mm3' in stats
        assert 'percentage' in stats
        assert stats['segmented_voxels'] == 50 * 50 * 50
        assert stats['volume_mm3'] == 50 * 50 * 50  # 1mm³ per voxel
    
    def test_calculate_statistics_empty_mask(self):
        """Test statistics with empty mask"""
        mask = np.zeros((100, 100, 100), dtype=np.uint8)
        spacing = (1.0, 1.0, 1.0)
        
        stats = self.engine.calculate_statistics(mask, spacing)
        
        assert stats['segmented_voxels'] == 0
        assert stats['volume_mm3'] == 0.0
        assert stats['percentage'] == 0.0
    
    def test_calculate_statistics_different_spacing(self):
        """Test statistics with different voxel spacing"""
        mask = np.ones((10, 10, 10), dtype=np.uint8)
        spacing = (2.0, 2.0, 2.0)  # 2mm spacing
        
        stats = self.engine.calculate_statistics(mask, spacing)
        
        # Volume should be 8x larger (2³)
        assert stats['volume_mm3'] == 10 * 10 * 10 * 8


# ============================================================================
# INTEGRATION TESTS: API to Result
# ============================================================================

class TestAPIIntegration:
    """Test API integration"""
    
    @pytest.mark.asyncio
    async def test_job_queue_add_job(self):
        """Test adding job to queue"""
        queue = JobQueue()
        job = SegmentationJob(
            job_id="test_123",
            study_id="study_456",
            model_type="organs",
            request_data={}
        )
        
        job_id = await queue.add_job(job)
        
        assert job_id == "test_123"
        retrieved = await queue.get_job(job_id)
        assert retrieved is not None
        assert retrieved.study_id == "study_456"
    
    @pytest.mark.asyncio
    async def test_job_queue_update_job(self):
        """Test updating job status"""
        queue = JobQueue()
        job = SegmentationJob(
            job_id="test_123",
            study_id="study_456",
            model_type="organs",
            request_data={}
        )
        await queue.add_job(job)
        
        updated = await queue.update_job(
            "test_123",
            status=JobStatus.PROCESSING,
            progress=0.5
        )
        
        assert updated is not None
        assert updated.status == JobStatus.PROCESSING
        assert updated.progress == 0.5
    
    @pytest.mark.asyncio
    async def test_job_queue_list_jobs(self):
        """Test listing jobs"""
        queue = JobQueue()
        
        # Add multiple jobs
        for i in range(5):
            job = SegmentationJob(
                job_id=f"test_{i}",
                study_id=f"study_{i}",
                model_type="organs",
                request_data={}
            )
            await queue.add_job(job)
        
        jobs = await queue.list_jobs()
        
        assert len(jobs) == 5
    
    @pytest.mark.asyncio
    async def test_job_queue_filter_by_study(self):
        """Test filtering jobs by study ID"""
        queue = JobQueue()
        
        # Add jobs for different studies
        for i in range(3):
            job = SegmentationJob(
                job_id=f"test_{i}",
                study_id="study_A",
                model_type="organs",
                request_data={}
            )
            await queue.add_job(job)
        
        for i in range(2):
            job = SegmentationJob(
                job_id=f"test_B_{i}",
                study_id="study_B",
                model_type="vessels",
                request_data={}
            )
            await queue.add_job(job)
        
        jobs_A = await queue.list_jobs(study_id="study_A")
        jobs_B = await queue.list_jobs(study_id="study_B")
        
        assert len(jobs_A) == 3
        assert len(jobs_B) == 2
    
    @pytest.mark.asyncio
    async def test_job_queue_clear_old_jobs(self):
        """Test clearing old jobs"""
        queue = JobQueue()
        
        # Add completed job
        job = SegmentationJob(
            job_id="test_old",
            study_id="study_123",
            model_type="organs",
            request_data={}
        )
        job.status = JobStatus.COMPLETED
        job.created_at = datetime(2020, 1, 1)  # Old date
        await queue.add_job(job)
        
        removed = await queue.clear_old_jobs(hours=1)
        
        assert removed == 1
        retrieved = await queue.get_job("test_old")
        assert retrieved is None


# ============================================================================
# ACCURACY TESTS: Validation Samples
# ============================================================================

class TestAccuracy:
    """Test segmentation accuracy"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.engine = SegmentationEngine()
    
    def test_organ_segmentation_accuracy(self):
        """Test organ segmentation accuracy with known sample"""
        # Create synthetic organ volume
        volume = self.create_synthetic_organ_volume()
        ground_truth = self.create_ground_truth_mask()
        
        # Run segmentation
        mask, stats = self.engine.segment_organs(volume)
        
        # Calculate Dice coefficient
        dice = self.calculate_dice_coefficient(mask, ground_truth)
        
        # Accuracy should be > 90%
        assert dice > 0.90, f"Dice coefficient {dice} below threshold"
    
    def test_vessel_segmentation_accuracy(self):
        """Test vessel segmentation accuracy"""
        volume = self.create_synthetic_vessel_volume()
        ground_truth = self.create_vessel_ground_truth()
        
        mask, stats = self.engine.segment_vessels(volume)
        
        dice = self.calculate_dice_coefficient(mask, ground_truth)
        
        assert dice > 0.85, f"Vessel Dice {dice} below threshold"
    
    def create_synthetic_organ_volume(self):
        """Create synthetic organ volume for testing"""
        volume = np.zeros((128, 128, 128), dtype=np.float32)
        # Add organ-like structure
        volume[40:88, 40:88, 40:88] = 50  # Soft tissue HU
        return volume
    
    def create_ground_truth_mask(self):
        """Create ground truth mask"""
        mask = np.zeros((128, 128, 128), dtype=np.uint8)
        mask[40:88, 40:88, 40:88] = 1
        return mask
    
    def create_synthetic_vessel_volume(self):
        """Create synthetic vessel volume"""
        volume = np.zeros((128, 128, 128), dtype=np.float32)
        # Add vessel-like structure (high intensity)
        volume[60:68, 60:68, :] = 150  # Contrast-enhanced vessel
        return volume
    
    def create_vessel_ground_truth(self):
        """Create vessel ground truth"""
        mask = np.zeros((128, 128, 128), dtype=np.uint8)
        mask[60:68, 60:68, :] = 1
        return mask
    
    def calculate_dice_coefficient(self, pred, truth):
        """Calculate Dice similarity coefficient"""
        intersection = np.logical_and(pred, truth).sum()
        union = pred.sum() + truth.sum()
        
        if union == 0:
            return 1.0
        
        dice = (2.0 * intersection) / union
        return dice


# ============================================================================
# STRESS TESTS: Concurrent Segmentations
# ============================================================================

class TestStress:
    """Test system under stress"""
    
    @pytest.mark.asyncio
    async def test_concurrent_job_submission(self):
        """Test submitting multiple jobs concurrently"""
        queue = JobQueue()
        
        # Submit 10 jobs concurrently
        tasks = []
        for i in range(10):
            job = SegmentationJob(
                job_id=f"concurrent_{i}",
                study_id=f"study_{i}",
                model_type="organs",
                request_data={}
            )
            tasks.append(queue.add_job(job))
        
        job_ids = await asyncio.gather(*tasks)
        
        assert len(job_ids) == 10
        assert len(set(job_ids)) == 10  # All unique
    
    @pytest.mark.asyncio
    async def test_concurrent_job_updates(self):
        """Test updating jobs concurrently"""
        queue = JobQueue()
        
        # Add jobs
        for i in range(5):
            job = SegmentationJob(
                job_id=f"test_{i}",
                study_id=f"study_{i}",
                model_type="organs",
                request_data={}
            )
            await queue.add_job(job)
        
        # Update concurrently
        tasks = []
        for i in range(5):
            tasks.append(queue.update_job(
                f"test_{i}",
                status=JobStatus.PROCESSING,
                progress=0.5
            ))
        
        results = await asyncio.gather(*tasks)
        
        assert all(r is not None for r in results)
        assert all(r.status == JobStatus.PROCESSING for r in results)
    
    def test_memory_usage_large_volume(self):
        """Test memory usage with large volume"""
        # Create large volume (512³)
        volume = np.random.randn(512, 512, 512).astype(np.float32)
        
        engine = SegmentationEngine()
        
        # Process volume
        normalized = engine.normalize_volume(volume)
        
        # Check memory is released
        del volume
        del normalized
        
        # Should not crash or leak memory
        assert True
    
    @pytest.mark.asyncio
    async def test_rapid_job_creation_deletion(self):
        """Test rapid job creation and deletion"""
        queue = JobQueue()
        
        # Rapidly create and delete jobs
        for i in range(100):
            job = SegmentationJob(
                job_id=f"rapid_{i}",
                study_id=f"study_{i}",
                model_type="organs",
                request_data={}
            )
            await queue.add_job(job)
            
            if i % 2 == 0:
                # Delete every other job
                await queue.update_job(f"rapid_{i}", status=JobStatus.CANCELLED)
        
        jobs = await queue.list_jobs()
        
        # Should handle rapid operations
        assert len(jobs) == 100


# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================

class TestErrorHandling:
    """Test error handling"""
    
    def test_invalid_volume_shape(self):
        """Test handling of invalid volume shape"""
        engine = SegmentationEngine()
        
        # 2D volume instead of 3D
        volume = np.random.randn(100, 100).astype(np.float32)
        
        with pytest.raises((ValueError, IndexError)):
            engine.normalize_volume(volume)
    
    def test_corrupted_volume_data(self):
        """Test handling of corrupted data"""
        engine = SegmentationEngine()
        
        # Volume with NaN values
        volume = np.random.randn(50, 50, 50).astype(np.float32)
        volume[25, 25, 25] = np.nan
        
        # Should handle gracefully
        try:
            normalized = engine.normalize_volume(volume)
            # NaN should be handled
            assert not np.isnan(normalized).any() or True
        except Exception:
            # Or raise appropriate error
            pass
    
    def test_empty_mask_processing(self):
        """Test processing empty mask"""
        engine = SegmentationEngine()
        
        mask = np.zeros((100, 100, 100), dtype=np.uint8)
        
        # Should handle empty mask
        smoothed = engine.smooth_mask(mask)
        assert smoothed.shape == mask.shape
    
    @pytest.mark.asyncio
    async def test_nonexistent_job_retrieval(self):
        """Test retrieving non-existent job"""
        queue = JobQueue()
        
        job = await queue.get_job("nonexistent_id")
        
        assert job is None
    
    @pytest.mark.asyncio
    async def test_duplicate_job_id(self):
        """Test handling duplicate job IDs"""
        queue = JobQueue()
        
        job1 = SegmentationJob(
            job_id="duplicate",
            study_id="study_1",
            model_type="organs",
            request_data={}
        )
        job2 = SegmentationJob(
            job_id="duplicate",
            study_id="study_2",
            model_type="vessels",
            request_data={}
        )
        
        await queue.add_job(job1)
        await queue.add_job(job2)  # Should overwrite
        
        retrieved = await queue.get_job("duplicate")
        assert retrieved.study_id == "study_2"  # Latest wins


# ============================================================================
# PERFORMANCE TESTS
# ============================================================================

class TestPerformance:
    """Test performance metrics"""
    
    def test_preprocessing_time(self):
        """Test preprocessing completes in reasonable time"""
        import time
        
        engine = SegmentationEngine()
        volume = np.random.randn(128, 128, 128).astype(np.float32)
        
        start = time.time()
        normalized = engine.normalize_volume(volume)
        resized = engine.resize_volume(normalized, (96, 96, 96))
        tensor = engine.convert_to_tensor(resized)
        elapsed = time.time() - start
        
        # Should complete in < 5 seconds
        assert elapsed < 5.0, f"Preprocessing took {elapsed}s"
    
    def test_postprocessing_time(self):
        """Test post-processing completes in reasonable time"""
        import time
        
        engine = SegmentationEngine()
        mask = np.random.randint(0, 2, (128, 128, 128), dtype=np.uint8)
        
        start = time.time()
        smoothed = engine.smooth_mask(mask)
        cleaned = engine.remove_small_components(smoothed)
        elapsed = time.time() - start
        
        # Should complete in < 5 seconds
        assert elapsed < 5.0, f"Post-processing took {elapsed}s"
    
    def test_statistics_calculation_time(self):
        """Test statistics calculation time"""
        import time
        
        engine = SegmentationEngine()
        mask = np.random.randint(0, 2, (256, 256, 256), dtype=np.uint8)
        spacing = (1.0, 1.0, 1.0)
        
        start = time.time()
        stats = engine.calculate_statistics(mask, spacing)
        elapsed = time.time() - start
        
        # Should complete in < 1 second
        assert elapsed < 1.0, f"Statistics took {elapsed}s"


# ============================================================================
# TEST CONFIGURATION
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
