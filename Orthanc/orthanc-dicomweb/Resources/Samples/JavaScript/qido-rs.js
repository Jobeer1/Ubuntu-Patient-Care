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


function GetTag(answer, tag)
{
  if (!(tag in answer) ||
      !("Value" in answer[tag]) ||
      answer[tag].length == 0) {
    return '';
  } else {
    return answer[tag]["Value"][0];
  }
}


$(document).ready(function() {
  // QIDO-RS to search for series
  $('#qido-series').submit(function() {
    var data = {};
    $('input[name]', this).each(function() {
      data[$(this).attr('name')] = $(this).val();
    });

    $.ajax({
      headers: {
        'Accept' : 'application/json'
      },
      data: data,
      cache: true,  // If set to false, the "_" GET argument is added, resulting in a bad QIDO-RS request
      dataType: 'json',
      url: '../dicom-web/series',
      success: function(answer) {
        $('#qido-series-results').empty();
        for (var i = 0; i < answer.length; i++) {
          var patientId = GetTag(answer[i], '00100020');
          var patientName = GetTag(answer[i], '00100010');
          var studyDescription = GetTag(answer[i], '00081030');
          var seriesDescription = GetTag(answer[i], '0008103E');
          var url = GetTag(answer[i], '00081190');
          $('#qido-series-results').append(
            '<li>' + patientId + ' - ' + patientName + ' - ' +
              studyDescription + ' - ' + seriesDescription +
              ' - ' + '<a href="' + url + '">WADO-RS URL</a></li>');
        }
      },
      error: function() {
        alert('Cannot process this query');
      }
    });

    // Prevent default action
    return false;
  });
});
