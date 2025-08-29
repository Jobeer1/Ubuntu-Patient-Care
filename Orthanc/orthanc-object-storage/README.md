# README #

Orthanc object-storages plugin for main cloud providers (Google/Azure/AWS)

Check the [Orthanc book](https://orthanc.uclouvain.be/book/plugins/object-storage.html) for complete documentation.

## info for developers ##

Here's a sample configuration file of the `StorageEncryption` section of the plugins:

```
{
    "GoogleCloudStorage" : {
        "StorageEncryption" : {
            "Enable": true,
            "MasterKey": [3, "/path/to/master.key"], // key id - path to the base64 encoded key
            "PreviousMasterKeys" : [
                [ 1, "/path/to/previous1.key"],
                [ 2, "/path/to/previous2.key"]
            ],
            "MaxConcurrentInputSize" : 1024   // size in MB 
        }
    }
}
```

### Compile Google plugin ###

On Linux, with vcpkg version `2023.06.20`:

* `./vcpkg install google-cloud-cpp[storage]`
* `./vcpkg install cryptopp`
* `hg clone ...`
* `mkdir -p build/google`
* `cd build/google` 
* `cmake -DCMAKE_TOOLCHAIN_FILE=[vcpkg root]\scripts\buildsystems\vcpkg.cmake ../../orthanc-object-storage/Google`

### Google plugin configuration ###

```
    "GoogleCloudStorage" : {
        "ServiceAccountFile" : "/.../googleServiceAccountFile.json",
        "BucketName": "test-orthanc-storage-plugin",
        "RootPath": "",                 // optional: folder in which files are stored (ex: my/path/to/myfolder)
        "StorageEncryption" : {...},
        "StorageStructure" : "flat",
        "MigrationFromFileSystemEnabled" : false
    }

```

## Azure Blob Storage plugin ##

### Prerequisites ###

* Install [vcpkg](https://github.com/Microsoft/vcpkg) 

### Compile Azure plugin ###

On Linux, with vcpkg version `2023.06.20`:

* `./vcpkg install azure-core-cpp azure-storage-blobs-cpp`
* `./vcpkg install cryptopp`
* `hg clone ...`
* `mkdir -p build/azure`
* `cd build/azure` 
* `cmake -DCMAKE_TOOLCHAIN_FILE=[vcpkg root]\scripts\buildsystems\vcpkg.cmake ../../orthanc-object-storage/Azure`

On Windows, with vcpkg version `2023.06.20` :

* `.\vcpkg.exe install azure-storage-blobs-cpp:x64-windows-static`
* `.\vcpkg.exe install cryptopp:x64-windows-static`
* `hg clone ...`
* `mkdir -p build/azure`
* `cd build/azure` 
* `cmake -DCMAKE_TOOLCHAIN_FILE=[vcpkg root]\scripts\buildsystems\vcpkg.cmake -DVCPKG_TARGET_TRIPLET=x64-windows-static -DSTATIC_BUILD=ON -DCMAKE_BUILD_TYPE="Release" ../../orthanc-object-storage/Azure`
* `cmake --build . --config Release`


### Azure plugin configuration ###

```
    "AzureBlobStorage" : {
    	"ConnectionString": "DefaultEndpointsProtocol=https;AccountName=xxxxxxxxx;AccountKey=yyyyyyyy===;EndpointSuffix=core.windows.net",
    	"ContainerName" : "test-orthanc-storage-plugin",
        "CreateContainerIfNotExists": true,       // available from version 1.2.0
        "RootPath": "",                 // optional: folder in which files are stored (ex: my/path/to/myfolder)
        "StorageEncryption" : {...},
        "StorageStructure" : "flat",
        "MigrationFromFileSystemEnabled" : false
    }
```

## AWS S3 Storage plugin ##

### Prerequisites ###

* Install [vcpkg](https://github.com/Microsoft/vcpkg) 

* compile the AWS C++ SDK

```

mkdir ~/aws
cd ~/aws
git clone https://github.com/aws/aws-sdk-cpp.git

mkdir -p ~/aws/builds/aws-sdk-cpp
cd ~/aws/builds/aws-sdk-cpp
cmake -DBUILD_ONLY="s3;transfer" ~/aws/aws-sdk-cpp 
make -j 4 
make install
```

### Compile AWS S3 plugin ###

* `./vcpkg install cryptopp`
* `hg clone ...`
* `mkdir -p build/aws`
* `cd build/aws` 
* `cmake -DCMAKE_TOOLCHAIN_FILE=[vcpkg root]\scripts\buildsystems\vcpkg.cmake ../../orthanc-object-storage/Aws`

### AWS S3 plugin configuration ###

```
    "AwsS3Storage" : {
    	"BucketName": "test-orthanc-s3-plugin",
        "Region" : "eu-central-1",
        "AccessKey" : "AKXXX",          // optional: if not specified, the plugin will use the default credentials manager (from version 1.3.0)
        "SecretKey" : "RhYYYY",         // optional: if not specified, the plugin will use the default credentials manager (from version 1.3.0)
        "Endpoint": "",                 // optional: custom endpoint
        "ConnectionTimeout": 30,        // optional: connection timeout in seconds
        "RequestTimeout": 1200,         // optional: request timeout in seconds (max time to upload/download a file)
        "RootPath": "",                 // optional: folder in which files are stored (ex: my/path/to/myfolder)
        "StorageEncryption" : {...},    // optional
        "StorageStructure" : "flat",    // optional
        "MigrationFromFileSystemEnabled" : false, // optional (deprecated, is now equivalent to "HybridMode": "WriteToObjectStorage")
        "HybridMode": "WriteToDisk"     // "WriteToDisk", "WriteToObjectStorage", "Disabled"
    }
```

### Testing the S3 plugin with minio

```
docker run -p 9000:9000 -p 9001:9001 -e MINIO_REGION=eu-west-1 -e MINIO_ROOT_USER=minio -e MINIO_ROOT_PASSWORD=miniopwd minio/minio server /data --console-address ":9001"
```

config file:
```
    "AwsS3Storage" : {
        "BucketName": "orthanc",
        "Region": "eu-west-1",
        "Endpoint": "http://127.0.0.1:9000/",
        "AccessKey": "minio",
        "SecretKey": "miniopwd",
        "VirtualAddressing": false

        // "StorageEncryption" : {
        //     "Enable": true,
        //     "MasterKey": [1, "/home/test/encryption/test.key"],
        //     "MaxConcurrentInputSize": 1024,
        //     "Verbose": true         
        // }                  // optional: see the section related to encryption
      }

```

Test the hybrid mode
- start in "HybridMode": "WriteToFileSystem", 
  - upload instances 1 & 2
- restart in "HybridMode": "WriteToObjectStorage", 
  - check that you can read instance 1 and that you can delete it
  - upload instances 3 & 4
- restart in "HybridMode": "WriteToFileSystem",
  - check that you can read instance 3 and that you can delete it
- final check:
  - there should be only one file in the disk storage
  - there should be only one file in the S3 bucket

test moving a study to file-system storage
curl http://localhost:8043/move-storage -d '{"Resources": ["737c0c8d-ea890b4d-e36a43bb-fb8c8d41-aa0ed0a8"], "TargetStorage" : "file-system"}'
curl http://localhost:8043/move-storage -d '{"Resources": ["737c0c8d-ea890b4d-e36a43bb-fb8c8d41-aa0ed0a8"], "TargetStorage" : "object-storage"}'