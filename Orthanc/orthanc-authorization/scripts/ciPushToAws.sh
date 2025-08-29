#!/usr/bin/env bash
# Builds the MSSQL Orthanc plugin Docker image
# Arguments:
#   $1 - Git branch name

set -e # Stop on error
set -u # Stop on uninitialized variable
set -x # Trace execution

branchName=${1:-$(hg branch)} #if no argument defined, get the branch name from git
commitId=$(hg identify --id)

if [[ $branchName == "default" ]]; then
    releaseTag=$commitId
else
    releaseTag=$branchName
fi

docker run --rm -e AWS_ACCESS_KEY_ID -e AWS_SECRET_ACCESS_KEY --entrypoint bash osimis/orthanc-authorization-plugin -c \
  "aws s3 --region eu-west-1 cp /usr/local/share/orthanc/plugins/libOrthancAuthorization.so s3://orthanc.osimis.io/docker-so/orthanc-authorization/$releaseTag/ --cache-control max-age=1"