set -ex

CURL="curl -s -u alice:orthanctest"

# CARDIAC
job=`${CURL} http://localhost:8042/dicom-web/servers/sample/wado -d '{"Uri":"/studies/1.3.51.0.1.1.192.168.29.133.1681753.1681732","Debug":true}' | jq -r .ID`

sleep 1

${CURL} http://localhost:8042/jobs/${job} | jq .
${CURL} http://localhost:8042/jobs/${job}/cancel -d '{}'

sleep 1

${CURL} http://localhost:8042/jobs/${job} | jq .

sleep 2

${CURL} http://localhost:8042/jobs/${job}/resubmit -d '{}'


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
