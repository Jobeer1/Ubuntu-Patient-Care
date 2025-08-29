#!/usr/bin/python

# Orthanc - A Lightweight, RESTful DICOM Store
# Copyright (C) 2012-2016 Sebastien Jodogne, Medical Physics
# Department, University Hospital of Liege, Belgium
# Copyright (C) 2017-2023 Osimis S.A., Belgium
# Copyright (C) 2024-2025 Orthanc Team SRL, Belgium
# Copyright (C) 2021-2025 Sebastien Jodogne, ICTEAM UCLouvain, Belgium
#
# This program is free software: you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.


import hashlib
import httplib2
import json
import os
import re
import signal
import subprocess
import tempfile
import threading
import sys
import time
import zipfile

from xml.dom import minidom

from PIL import Image, ImageChops
import math
import operator


if (sys.version_info >= (3, 0)):
    from urllib.parse import urlencode
    from io import StringIO
    from io import BytesIO
    from urllib.parse import unquote

else:
    from urllib import urlencode
    from urlparse import unquote

    # http://stackoverflow.com/a/1313868/881731
    try:
        from cStringIO import StringIO
    except:
        from StringIO import StringIO

    
def DecodeJson(s):
    t = s

    if (sys.version_info >= (3, 0)):
        try:
            t = s.decode()
        except:
            pass

    try:
        return json.loads(t)
    except:
        return t


def DefineOrthanc(server = 'localhost',
                  restPort = 8042,
                  username = None,
                  password = None,
                  aet = 'ORTHANC',
                  dicomPort = 4242):
    #m = re.match(r'(http|https)://([^:]+):([^@]+)@([^@]+)', url)
    #if m != None:
    #    url = m.groups()[0] + '://' + m.groups()[3]
    #    username = m.groups()[1]
    #    password = m.groups()[2]

    #if not url.endswith('/'):
    #    url += '/'

    return {
        'Server' : server,
        'Url' : 'http://%s:%d/' % (server, restPort),
        'Username' : username,
        'Password' : password,
        'DicomAet' : aet,
        'DicomPort' : dicomPort
        }


def _SetupCredentials(orthanc, http):
    if (orthanc['Username'] != None and 
        orthanc['Password'] != None):
        http.add_credentials(orthanc['Username'], orthanc['Password'])

def DoGetRaw(orthanc, uri, data = {}, body = None, headers = {}):
    d = ''
    if len(data.keys()) > 0:
        d = '?' + urlencode(data)

    http = httplib2.Http()
    http.follow_redirects = False
    _SetupCredentials(orthanc, http)

    resp, content = http.request(orthanc['Url'] + uri + d, 'GET', body = body,
                                 headers = headers)
    return (resp, content)


def DoGet(orthanc, uri, data = {}, body = None, headers = {}):
    (resp, content) = DoGetRaw(orthanc, uri, data = data, body = body, headers = headers)

    if not (resp.status in [ 200 ]):
        raise Exception(resp.status, resp)
    else:
        return DecodeJson(content)

def _DoPutOrPost(orthanc, uri, method, data, contentType, headers):
    http = httplib2.Http()
    http.follow_redirects = False
    _SetupCredentials(orthanc, http)

    if isinstance(data, (str, bytearray, bytes)):
        body = data
        if len(contentType) != 0:
            headers['content-type'] = contentType
    else:
        body = json.dumps(data)
        headers['content-type'] = 'application/json'
    
    headers['expect'] = ''

    resp, content = http.request(orthanc['Url'] + uri, method,
                                 body = body,
                                 headers = headers)
    return (resp, content)

def DoDeleteRaw(orthanc, uri, headers = {}):
    http = httplib2.Http()
    http.follow_redirects = False
    _SetupCredentials(orthanc, http)

    resp, content = http.request(orthanc['Url'] + uri, 'DELETE', headers = headers)
    return (resp, content)

def DoDelete(orthanc, uri, headers = {}):
    (resp, content) = DoDeleteRaw(orthanc, uri, headers)
    if not (resp.status in [ 200 ]):
        raise Exception(resp.status, resp)
    else:
        return DecodeJson(content)

def DoPutRaw(orthanc, uri, data = {}, contentType = '', headers = {}):
    return _DoPutOrPost(orthanc, uri, 'PUT', data, contentType, headers)

def DoPut(orthanc, uri, data = {}, contentType = '', headers = {}):
    (resp, content) = DoPutRaw(orthanc, uri, data, contentType, headers)
    if not (resp.status in [ 200, 201, 302 ]):
        raise Exception(resp.status, resp)
    else:
        return DecodeJson(content)

def DoPostRaw(orthanc, uri, data = {}, contentType = '', headers = {}):
    return _DoPutOrPost(orthanc, uri, 'POST', data, contentType, headers)
    
def DoPost(orthanc, uri, data = {}, contentType = '', headers = {}):
    (resp, content) = DoPostRaw(orthanc, uri, data, contentType, headers)
    if not (resp.status in [ 200, 201, 302 ]):
        raise Exception(resp.status, resp)
    else:
        return DecodeJson(content)

def GetDatabasePath(filename):
    return os.path.join(os.path.dirname(__file__), '..', 'Database', filename)

def UploadInstance(orthanc, filename):
    with open(GetDatabasePath(filename), 'rb') as f:
        d = f.read()

    return DoPost(orthanc, '/instances', d, 'application/dicom')

def UploadFolder(orthanc, path):
    for i in os.listdir(GetDatabasePath(path)):
        try:
            UploadInstance(orthanc, os.path.join(path, i))
        except:
            pass

def DropOrthanc(orthanc):
    # Reset the Lua callbacks
    DoPost(orthanc, '/tools/execute-script', 'function OnStoredInstance(instanceId, tags, metadata) end', 'application/lua')

    DoDelete(orthanc, '/exports')

    for s in DoGet(orthanc, '/patients'):
        DoDelete(orthanc, '/patients/%s' % s)

def InstallLuaScriptFromPath(orthanc, path):
    with open(GetDatabasePath(path), 'r') as f:
        InstallLuaScript(orthanc, f.read())
    
def InstallLuaScript(orthanc, script):
    DoPost(orthanc, '/tools/execute-script', script, 'application/lua')

def UninstallLuaCallbacks(orthanc):
    DoPost(orthanc, '/tools/execute-script', 'function OnStoredInstance() end', 'application/lua')
    InstallLuaScriptFromPath(orthanc, 'Lua/TransferSyntaxEnable.lua')


def ComputeMD5(data):
    m = hashlib.md5()
    m.update(data)
    return m.hexdigest()

def UncompressImage(data):
    if (sys.version_info >= (3, 0)):
        return Image.open(BytesIO(data))
    else:
        return Image.open(StringIO(data))

def GetImage(orthanc, uri, headers = {}):
    # http://www.pythonware.com/library/pil/handbook/introduction.htm
    return UncompressImage(DoGet(orthanc, uri, headers = headers))

def ParseArchive(s):
    # http://stackoverflow.com/a/1313868/881731
    if (sys.version_info >= (3, 0)):
        return zipfile.ZipFile(BytesIO(s), "r")
    else:
        return zipfile.ZipFile(StringIO(s), "r")

def GetArchive(orthanc, uri):
    (resp, content) = DoGetRaw(orthanc, uri)
    return ParseArchive(content), resp

def PostArchive(orthanc, uri, body):
    # http://stackoverflow.com/a/1313868/881731
    return ParseArchive(DoPost(orthanc, uri, body))

def IsDefinedInLua(orthanc, name):
    s = DoPost(orthanc, '/tools/execute-script', 'print(type(%s))' % name, 'application/lua')
    return (s.strip() != 'nil')

def WaitEmpty(orthanc):
    while True:
        if len(DoGet(orthanc, '/instances')) == 0:
            return
        time.sleep(0.01)

def WaitJobDone(orthanc, job):
    while True:
        s = DoGet(orthanc, '/jobs/%s' % job) ['State']

        if s == 'Success':
            return True
        elif s == 'Failure':
            return False
        
        time.sleep(0.01)

def MonitorJob(orthanc, func):  # "func" is a lambda
    a = set(DoGet(orthanc, '/jobs'))
    func()
    b = set(DoGet(orthanc, '/jobs'))
        
    diff = list(b - a)
    if len(diff) != 1:
        print('No job was created!')
        return False
    else:
        return WaitJobDone(orthanc, diff[0])

def MonitorJob2(orthanc, func):  # "func" is a lambda
    a = set(DoGet(orthanc, '/jobs'))
    job = func()
    b = set(DoGet(orthanc, '/jobs'))
        
    diff = list(b - a)
    if len(diff) != 1:
        print('No job was created!')
        return None
    elif (not 'ID' in job or
          diff[0] != job['ID']):
        print('Mismatch in the job ID')
        return None
    elif WaitJobDone(orthanc, diff[0]):
        return diff[0]
    else:
        print('Error while executing the job')
        return None

def WaitAllNewJobsDone(orthanc, func):  # "func" is a lambda
    a = set(DoGet(orthanc, '/jobs'))
    func()

    first = True

    while True:
        b = set(DoGet(orthanc, '/jobs'))
        
        diff = list(b - a)
        if len(diff) == 0:
            if first:
                raise Exception('No job was created')
            else:
                return  # We're done
        else:
            first = False

            if WaitJobDone(orthanc, diff[0]):
                a.add(diff[0])
            else:
                raise Exception('Error while executing the job')


def GetDockerHostAddress():
    route = subprocess.check_output([ '/sbin/ip', 'route' ])
    m = re.search(r'default via ([0-9.]+)', route)
    if m == None:
        return 'localhost'
    else:
        return m.groups()[0]

def FindExecutable(name):
    p = os.path.join('/usr/local/bin', name)
    if os.path.isfile(p):
        return p

    p = os.path.join('/usr/local/sbin', name)
    if os.path.isfile(p):
        return p

    return name

def IsOrthancVersionAbove(orthanc, major, minor, revision):
    v = DoGet(orthanc, '/system')['Version']

    if v.startswith('mainline'):
        return True
    else:
        tmp = v.split('.')
        a = int(tmp[0])
        b = int(tmp[1])
        c = int(tmp[2])
        return (a > major or
                (a == major and b > minor) or
                (a == major and b == minor and c >= revision))


def HasExtendedFind(orthanc):
    v = DoGet(orthanc, '/system')

    if 'Capabilities' in v and 'HasExtendedFind' in v['Capabilities']:
        return v['Capabilities']['HasExtendedFind']
    return False


def HasExtendedChanges(orthanc):
    v = DoGet(orthanc, '/system')

    if 'Capabilities' in v and 'HasExtendedChanges' in v['Capabilities']:
        return v['Capabilities']['HasExtendedChanges']
    return False


def GetStorageAccessesCount(orthanc):
    mm = DoGetRaw(orthanc, "/tools/metrics-prometheus")[1]

    if (sys.version_info >= (3, 0)):
        try:
            mm = mm.decode()
        except:
            pass

    mm = [x.split(" ") for x in mm.split("\n")]

    count = 0
    for m in mm:
        if m[0] == 'orthanc_storage_cache_hit_count':
            count += int(m[1])
        if m[0] == 'orthanc_storage_cache_miss_count':
            count += int(m[1])

    # print("storage access count = %s" % count)
    return count


def IsPluginVersionAtLeast(orthanc, plugin, major, minor, revision):
    v = DoGet(orthanc, '/plugins/%s' % plugin)['Version']

    if v.startswith('mainline'):
        return True
    else:
        tmp = v.split('.')
        if len(tmp) >= 3:
            a = int(tmp[0])
            b = int(tmp[1])
            c = int(tmp[2])
            return (a > major or
                    (a == major and b > minor) or
                    (a == major and b == minor and c >= revision))
        elif len(tmp) >= 2:
            a = int(tmp[0])
            b = int(tmp[1])
            return (a > major or
                    (a == major and b >= minor))
        else:
            return False

class ExternalCommandThread:
    @staticmethod
    def ExternalCommandFunction(arg, stop_event, command, env):
        with open(os.devnull, 'w') as devnull:
            external = subprocess.Popen(command, env = env, stderr = devnull)

            while (not stop_event.is_set()):
                error = external.poll()
                if error != None:
                    # http://stackoverflow.com/a/1489838/881731
                    os._exit(-1)
                stop_event.wait(0.1)

        print('Stopping the external command')
        external.terminate()
        external.communicate()  # Wait for the command to stop

    def __init__(self, command, env = None):
        self.thread_stop = threading.Event()
        self.thread = threading.Thread(target = self.ExternalCommandFunction, 
                                       args = (10, self.thread_stop, command, env))
        #self.daemon = True
        self.thread.start()

    def stop(self):
        self.thread_stop.set()
        self.thread.join()


def AssertAlmostEqualRecursive(self, a, b, places = 7, ignoreKeys = []):
    if type(a) is dict:
        self.assertTrue(type(b) is dict)
        self.assertEqual(a.keys(), b.keys())
        for key, value in a.items():
            if not key in ignoreKeys:
                AssertAlmostEqualRecursive(self, a[key], b[key], places)

    elif type(a) is list:
        self.assertTrue(type(b) is list)
        self.assertEqual(len(a), len(b))
        for i in range(len(a)):
            AssertAlmostEqualRecursive(self, a[i], b[i], places)

    else:
        self.assertAlmostEqual(a, b, places = places)


def GetTransferSyntax(dicom, encoding='utf-8'):
    with tempfile.NamedTemporaryFile(delete = True) as f:
        f.write(dicom)
        f.flush()

        with open(os.devnull, 'w') as devnull:
            data = subprocess.check_output([ FindExecutable('dcm2xml'), f.name ],
                                           stderr = devnull)
    return re.search('<data-set xfer="(.*?)"', data.decode(encoding)).group(1)


def HasGdcmPlugin(orthanc):
    plugins = DoGet(orthanc, '/plugins')
    return ('gdcm' in plugins)

def HasPostgresIndexPlugin(orthanc):
    plugins = DoGet(orthanc, '/plugins')
    return ('postgresql-index' in plugins)


def _GetMaxImageDifference(im1, im2):
    h = ImageChops.difference(im1, im2).histogram()

    if len(h) < 256:
        raise Exception()

    i = len(h) - 1
    while h[i] == 0:
        i -= 1

    return i
    

def GetMaxImageDifference(im1, im2):
    if im1.mode != im2.mode:
        raise Exception('Incompatible image modes')

    if im1.mode == 'RGB':
        red1, green1, blue1 = im1.split()
        red2, green2, blue2 = im2.split()
        return max([ _GetMaxImageDifference(red1, red2), 
                     _GetMaxImageDifference(green1, green2),
                     _GetMaxImageDifference(blue1, blue2) ])
    else:
        return _GetMaxImageDifference(im1, im2)


def DoPropFind(orthanc, uri, depth):
    http = httplib2.Http()
    http.follow_redirects = False
    _SetupCredentials(orthanc, http)

    resp, content = http.request(orthanc['Url'] + uri, 'PROPFIND', headers = { 'Depth' : str(depth) })

    if not (resp.status in [ 207 ]):
        raise Exception(resp.status, resp)
    else:
        xml = minidom.parseString(content)

        if (xml.documentElement.nodeName != 'D:multistatus' or
            xml.documentElement.attributes['xmlns:D'].value != 'DAV:'):
            raise Exception()

        result = {}
        
        for i in xml.documentElement.childNodes:
            if i.nodeType == minidom.Node.ELEMENT_NODE:
                if i.nodeName != 'D:response':
                    raise Exception()
                href = None
                prop = None
                for j in i.childNodes:
                    if j.nodeType == minidom.Node.ELEMENT_NODE:
                        if j.nodeName == 'D:href':
                            if href == None:
                                href = unquote(j.firstChild.nodeValue)
                            else:
                                raise Exception()
                        elif j.nodeName == 'D:propstat':
                            for k in j.childNodes:
                                if k.nodeName == 'D:status':
                                    if k.firstChild.nodeValue != 'HTTP/1.1 200 OK':
                                        raise Exception()
                                elif k.nodeType == minidom.Node.ELEMENT_NODE:
                                    if (k.nodeName != 'D:prop' or
                                        prop != None):
                                        raise Exception()
                                    prop = k
                        else:
                            raise Exception()
                if href == None or prop == None:
                    raise Exception()

                info = {}

                for j in prop.childNodes:
                    if j.nodeType == minidom.Node.ELEMENT_NODE:
                        if j.nodeName == 'D:displayname':
                            info['displayname'] = j.firstChild.nodeValue if j.firstChild != None else ''
                        elif j.nodeName == 'D:creationdate':
                            info['creationdate'] = j.firstChild.nodeValue
                        elif j.nodeName == 'D:getlastmodified':
                            info['lastmodified'] = j.firstChild.nodeValue
                        elif j.nodeName == 'D:resourcetype':
                            k = j.getElementsByTagName('D:collection')
                            info['folder'] = (len(k) == 1)

                result[href] = info
            elif i.nodeType != minidom.Node.TEXT_NODE:
                raise Exception()
        
        return result
