set -ex

# CARDIAC
curl -s -u alice:orthanctest http://localhost:8042/dicom-web/servers/sample/stow -d '{"Resources":["6e2c0ec2-5d99c8ca-c1c21cee-79a09605-68391d12"],"Synchronous":true,"Debug":true}'
