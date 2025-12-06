import pytest
import numpy as np
import pydicom
from pydicom.dataset import FileDataset, Dataset
from pydicom.uid import ExplicitVRLittleEndian
import io
import sys
import os

# Add parent directory to path to import ai_triage modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dicom_processor import DicomSliceExtractor, DicomProcessorError

class TestDicomProcessor:
    
    @pytest.fixture
    def processor(self):
        return DicomSliceExtractor()

    @pytest.fixture
    def mock_dicom(self):
        # Create a dummy DICOM dataset
        file_meta = Dataset()
        file_meta.MediaStorageSOPClassUID = '1.2.840.10008.5.1.4.1.1.2' # CT Image Storage
        file_meta.MediaStorageSOPInstanceUID = '1.2.3'
        file_meta.ImplementationClassUID = '1.2.3.4'
        file_meta.TransferSyntaxUID = ExplicitVRLittleEndian

        # Create dataset
        ds = FileDataset("dummy.dcm", {}, file_meta=file_meta, preamble=b"\0" * 128)
        ds.PatientID = "TEST_PATIENT"
        ds.StudyInstanceUID = "1.2.3.4.5"
        ds.SeriesInstanceUID = "1.2.3.4.5.6"
        ds.Modality = "CT"
        ds.Rows = 10
        ds.Columns = 10
        ds.BitsAllocated = 16
        ds.BitsStored = 12
        ds.HighBit = 11
        ds.PixelRepresentation = 0 # unsigned
        ds.SamplesPerPixel = 1
        ds.PhotometricInterpretation = "MONOCHROME2"
        ds.RescaleIntercept = -1024
        ds.RescaleSlope = 1
        ds.WindowCenter = 40
        ds.WindowWidth = 400
        ds.NumberOfFrames = 1
        
        # Create dummy pixel data
        # 10x10 image
        data = np.zeros((10, 10), dtype=np.uint16)
        # Set some values for windowing test
        # Center (40 HU) -> 1064 raw
        data[0,0] = 1064 
        # Max (240 HU) -> 1264 raw
        data[0,1] = 1264
        # Min (-160 HU) -> 864 raw
        data[0,2] = 864
        
        ds.PixelData = data.tobytes()
        
        return ds

    def test_load_dicom_bytes(self, processor, mock_dicom):
        # Save to bytes
        with io.BytesIO() as buffer:
            mock_dicom.save_as(buffer)
            buffer.seek(0)
            ds = processor.load_dicom(buffer)
            assert ds.PatientID == "TEST_PATIENT"

    def test_metadata_extraction(self, processor, mock_dicom):
        meta = processor.get_metadata(mock_dicom)
        assert meta['PatientID'] == "TEST_PATIENT"
        assert meta['Modality'] == "CT"
        assert meta['StudyInstanceUID'] == "1.2.3.4.5"

    def test_windowing_normalization(self, processor, mock_dicom):
        # We need to ensure pixel_array returns the data we set.
        # pydicom reads PixelData and converts it.
        
        # Since we are not saving to file and reading back in this specific test (we pass ds directly),
        # we rely on pydicom's behavior.
        # However, ds.pixel_array might fail if TransferSyntax is not handled or if data is not consistent.
        # Let's save and reload to be safe, as that's how the processor works usually.
        
        with io.BytesIO() as buffer:
            mock_dicom.save_as(buffer)
            buffer.seek(0)
            ds = pydicom.dcmread(buffer)
            
            processed = processor.process_slice(ds)
            
            # Check values
            # 40 HU -> 0.5
            assert np.isclose(processed[0,0], 0.5, atol=0.01)
            # 240 HU -> 1.0
            assert np.isclose(processed[0,1], 1.0, atol=0.01)
            # -160 HU -> 0.0
            assert np.isclose(processed[0,2], 0.0, atol=0.01)

    def test_extract_frames_single(self, processor, mock_dicom):
        with io.BytesIO() as buffer:
            mock_dicom.save_as(buffer)
            buffer.seek(0)
            results = processor.extract_frames(buffer)
            
        assert len(results) == 1
        assert results[0]['pixel_data'].shape == (10, 10)
        assert results[0]['metadata']['PatientID'] == "TEST_PATIENT"

    def test_resize(self, processor, mock_dicom):
        with io.BytesIO() as buffer:
            mock_dicom.save_as(buffer)
            buffer.seek(0)
            # Resize to 5x5
            results = processor.extract_frames(buffer, target_size=(5, 5))
            
        assert results[0]['pixel_data'].shape == (5, 5)

    def test_multi_frame_handling(self, processor, mock_dicom):
        # Create multi-frame dataset
        mock_dicom.NumberOfFrames = 3
        # 3 frames of 10x10
        data = np.zeros((3, 10, 10), dtype=np.uint16)
        mock_dicom.PixelData = data.tobytes()
        mock_dicom.Rows = 10
        mock_dicom.Columns = 10
        
        # Need to update pixel data length tag? pydicom handles it on save usually.
        
        with io.BytesIO() as buffer:
            mock_dicom.save_as(buffer)
            buffer.seek(0)
            results = processor.extract_frames(buffer)
            
        assert len(results) == 3
        assert results[0]['metadata']['InstanceNumber'] == 1
        assert results[1]['metadata']['InstanceNumber'] == 2
        assert results[2]['metadata']['InstanceNumber'] == 3

