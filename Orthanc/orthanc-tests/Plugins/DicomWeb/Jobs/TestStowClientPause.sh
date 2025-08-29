set -ex

CURL="curl -s -u alice:orthanctest"

# CARDIAC
job=`${CURL} http://localhost:8042/dicom-web/servers/sample/stow -d '{"Resources":["6e2c0ec2-5d99c8ca-c1c21cee-79a09605-68391d12"],"Synchronous":false,"Debug":true}' | jq -r .ID`

sleep 1

${CURL} http://localhost:8042/jobs/${job} | jq .
${CURL} http://localhost:8042/jobs/${job}/pause -d '{}'

sleep 1

${CURL} http://localhost:8042/jobs/${job} | jq .

sleep 2

${CURL} http://localhost:8042/jobs/${job}/resume -d '{}'


set +x

while true
do
    info=`${CURL} http://localhost:8042/jobs/${job}`
    state=`echo $info | jq -r .State`

    echo $info | jq .
    echo $state
    if [ $state != "Running" ]; then
        break
    else
        sleep 1
    fi
done

