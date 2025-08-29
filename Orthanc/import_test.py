import sys
sys.path.insert(0, r'c:\Users\parkh\OneDrive\Desktop\05i_DEMO_Reinforcement\Ubuntu Patient Sorg\Ubuntu-Patient-Care\Orthanc\orthanc-source\NASIntegration')
try:
    import backend.device_management as dm
    print('OK', getattr(dm,'DeviceManager',None), getattr(dm,'device_manager',None), getattr(dm,'MedicalDevice',None))
except Exception as e:
    print('IMPORT_ERROR', e)
