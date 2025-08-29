set -ex

# CARDIAC
curl -s -u alice:orthanctest http://localhost:8042/dicom-web/servers/sample/wado -d '{"Uri":"/studies/1.3.51.0.1.1.192.168.29.133.1681753.1681732","Synchronous":true,"Debug":true}'
