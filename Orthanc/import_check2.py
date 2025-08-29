import sys
sys.path.insert(0, r'c:\Users\parkh\OneDrive\Desktop\05i_DEMO_Reinforcement\Ubuntu Patient Sorg\Ubuntu-Patient-Care\Orthanc\orthanc-source\NASIntegration')
results = {}
modules = ['backend.device_management','backend.core','backend.repository','backend.discovery_service','backend.connectivity_service']
for m in modules:
    try:
        mod = __import__(m, fromlist=['*'])
        results[m] = 'OK'
    except Exception as e:
        results[m] = f'ERROR: {e}'
with open('import_check2_out.txt','w') as f:
    for k,v in results.items():
        f.write(f"{k}: {v}\n")
print('done')
