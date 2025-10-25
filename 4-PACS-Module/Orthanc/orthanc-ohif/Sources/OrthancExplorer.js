/**
 * SPDX-FileCopyrightText: 2023-2025 Sebastien Jodogne, ICTEAM UCLouvain, Belgium
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

/**
 * OHIF plugin for Orthanc
 * Copyright (C) 2023-2025 Sebastien Jodogne, ICTEAM UCLouvain, Belgium
 *
 * This program is free software: you can redistribute it and/or
 * modify it under the terms of the GNU General Public License as
 * published by the Free Software Foundation, either version 3 of the
 * License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful, but
 * WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
 * General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program. If not, see <http://www.gnu.org/licenses/>.
 **/


function AddOhifViewer(target, name, callback) {
  var li = $('<li>', {
    name: name,
  }).click(callback);

  li.append($('<a>', {
    href: '#',
    rel: 'close',
    text: name
  }));

  target.append(li);
}


$('#study').live('pagebeforeshow', function() {
  var studyId = $.mobile.pageData.uuid;

  $.ajax({
    url: '../studies/' + studyId,
    dataType: 'json',
    success: function(s) {
      var studyInstanceUid = s.MainDicomTags.StudyInstanceUID;
      
      $('#ohif-button').remove();

      var b = $('<a>')
          .attr('id', 'ohif-button')
          .attr('data-role', 'button')
          .attr('href', '#')
          .attr('data-icon', 'search')
          .attr('data-theme', 'e')
          .text('Open OHIF viewer')
          .button();
      
      b.insertAfter($('#study-info'));
      
      b.click(function() {
        var viewers = $('<ul>')
            .attr('data-divider-theme', 'd')
            .attr('data-role', 'listview');

        // The list of OHIF viewers can be found at: https://docs.ohif.org/

        AddOhifViewer(viewers, 'Basic viewer', function() {
          if (${USE_DICOM_WEB}) {
            window.open('../ohif/viewer?StudyInstanceUIDs=' + studyInstanceUid);
          } else  {
            window.open('../ohif/viewer?url=../studies/' + studyId + '/ohif-dicom-json');
          }
        });

        AddOhifViewer(viewers, 'Volume rendering', function() {
          if (${USE_DICOM_WEB}) {
            window.open('../ohif/viewer?hangingprotocolId=mprAnd3DVolumeViewport&StudyInstanceUIDs=' + studyInstanceUid);
          } else  {
            window.open('../ohif/viewer?hangingprotocolId=mprAnd3DVolumeViewport&url=../studies/' + studyId + '/ohif-dicom-json');
          }
        });

        AddOhifViewer(viewers, 'Total metabolic tumor volume', function() {
          if (${USE_DICOM_WEB}) {
            window.open('../ohif/tmtv?StudyInstanceUIDs=' + studyInstanceUid);
          } else  {
            window.open('../ohif/tmtv?url=../studies/' + studyId + '/ohif-dicom-json');
          }
        });

        AddOhifViewer(viewers, 'Segmentation', function() {
          if (${USE_DICOM_WEB}) {
            window.open('../ohif/segmentation?StudyInstanceUIDs=' + studyInstanceUid);
          } else  {
            window.open('../ohif/segmentation?url=../studies/' + studyId + '/ohif-dicom-json');
          }
        });

        AddOhifViewer(viewers, 'Microscopy', function() {
          if (${USE_DICOM_WEB}) {
            window.open('../ohif/microscopy?StudyInstanceUIDs=' + studyInstanceUid);
          } else  {
            window.open('../ohif/microscopy?url=../studies/' + studyId + '/ohif-dicom-json');
          }
        });

        // Launch the dialog
        $('#dialog').simpledialog2({
          mode: 'blank',
          animate: false,
          headerText: 'Choose OHIF viewer',
          headerClose: true,
          forceInput: false,
          width: '100%',
          blankContent: viewers
        });
      });
    }
  });
});


if (${USE_DICOM_WEB}) {
  $('#lookup').live('pagebeforeshow', function() {
    $('#open-ohif-study-list').remove();
    
    var b = $('<fieldset>')
        .attr('id', 'open-ohif-study-list')
        .addClass('ui-grid-b')
        .append($('<div>')
                .addClass('ui-block-a'))
        .append($('<div>')
                .addClass('ui-block-b')
                .append($('<a>')
                        .attr('id', 'coucou')
                        .attr('data-role', 'button')
                        .attr('href', '#')
                        .attr('data-icon', 'forward')
                        .attr('data-theme', 'a')
                        .text('Open OHIF study list')
                        .button()
                        .click(function(e) {
                          window.open('../ohif/');
                        })));
    
    b.insertAfter($('#lookup-result'));
  });
}
