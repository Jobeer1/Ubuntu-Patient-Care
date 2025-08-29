This is a sample JavaScript/jQuery application that makes a QIDO-RS request.

To use it without facing the cross-domain restrictions, you will need
to serve this folder using the "ServeFolder" plugin from the Orthanc
source distribution:
https://bitbucket.org/sjodogne/orthanc/src/default/Plugins/Samples/ServeFolders/

Your Orthanc configuration file will have to contain the following
instruction to serve this folder as "http://localhost:8042/test/":

  "ServeFolders" : {
    "/dicom-web-test" : "<...>/Resources/Samples/JavaScript"
  }

Where "<...>" is the path to the root of this repository.

Once Orthanc is running with the adapted configuration, open Firefox
or Chrome at the following URL:
http://localhost:8042/dicom-web-test/index.html
