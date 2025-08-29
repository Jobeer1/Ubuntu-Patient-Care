/**
 * Orthanc - A Lightweight, RESTful DICOM Store
 * Copyright (C) 2012-2016 Sebastien Jodogne, Medical Physics
 * Department, University Hospital of Liege, Belgium
 * Copyright (C) 2017-2023 Osimis S.A., Belgium
 * Copyright (C) 2024-2025 Orthanc Team SRL, Belgium
 * Copyright (C) 2021-2025 Sebastien Jodogne, ICTEAM UCLouvain, Belgium
 *
 * This program is free software: you can redistribute it and/or
 * modify it under the terms of the GNU Affero General Public License
 * as published by the Free Software Foundation, either version 3 of
 * the License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful, but
 * WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Affero General Public License for more details.
 * 
 * You should have received a copy of the GNU Affero General Public License
 * along with this program. If not, see <http://www.gnu.org/licenses/>.
 **/



// http://www.artandlogic.com/blog/2013/11/jquery-ajax-blobs-and-array-buffers/




var BOUNDARY = 'BOUNDARY_123456789';


function StringToArrayBuffer(str) 
{
  // http://updates.html5rocks.com/2012/06/How-to-convert-ArrayBuffer-to-and-from-String
  var bufView = new Uint8Array(str.length);

  for (var i=0, strLen=str.length; i < strLen; i++) {
    bufView[i] = str.charCodeAt(i);
  }

  return bufView;
}


function ConstructMultipart(body, contentType) 
{
  var header = '--' + BOUNDARY + '\r\nContent-Type: ' + contentType + '\r\n\r\n';
  var trailer = '\r\n--' + BOUNDARY + '--\r\n';
  
  header = StringToArrayBuffer(header);
  trailer = StringToArrayBuffer(trailer);

  // Concatenate the header, the body and the trailer
  // http://stackoverflow.com/a/14071518/881731
  var b = new Uint8Array(header.byteLength + body.byteLength + trailer.byteLength);
  b.set(header);
  b.set(new Uint8Array(body), header.byteLength);
  b.set(trailer, header.byteLength + body.byteLength);

  return b;
}


$(document).ready(function() {
  // STOW-RS to upload one DICOM file
  $('#stow').submit(function() {

    var fileInput = document.getElementById('stow-file');
    var file = fileInput.files[0];
    reader = new FileReader();
    reader.onload = function() {
      $.ajax({
        type: 'POST',
        headers: {
          'Accept' : 'application/json',
          'Content-type' : 'multipart/related; type=application/dicom; boundary=' + BOUNDARY,
        },
        url: '../dicom-web/studies',
        data: ConstructMultipart(reader.result, 'application/dicom'),
        processData: false, // Very important!
        dataType: 'json',
        success: function(resp) {
          count = resp['00081199'].Value.length;
          alert('Upload was a success! ' + count + ' instance was uploaded.');
        },
        error: function() {
          alert('Cannot process this query');
        }
      });
    };

    reader.readAsArrayBuffer(file);

    // Prevent default action
    return false;
  });
});
