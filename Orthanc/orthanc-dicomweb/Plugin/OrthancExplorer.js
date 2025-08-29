function ChooseDicomWebServer(callback)
{
  var clickedModality = '';
  var clickedPeer = '';
  var items = $('<ul>')
    .attr('data-divider-theme', 'd')
    .attr('data-role', 'listview');

  $.ajax({
    url: '../${DICOMWEB_ROOT}/servers',
    type: 'GET',
    dataType: 'json',
    async: false,
    cache: false,
    success: function(servers) {
      var name, item;
      
      if (servers.length > 0)
      {
        items.append('<li data-role="list-divider">DICOMweb servers</li>');

        for (var i = 0; i < servers.length; i++) {
          name = servers[i];
          item = $('<li>')
            .html('<a href="#" rel="close">' + name + '</a>')
            .attr('name', name)
            .click(function() { 
              clickedModality = $(this).attr('name');
            });
          items.append(item);
        }
      }

      // Launch the dialog
      $(document).simpledialog2({
        mode: 'blank',
        animate: false,
        headerText: 'Choose target',
        headerClose: true,
        forceInput: false,
        width: '100%',
        blankContent: items,
        callbackClose: function() {
          var timer;
          function WaitForDialogToClose() {
            if (!$('#dialog').is(':visible')) {
              clearInterval(timer);
              callback(clickedModality, clickedPeer);
            }
          }
          timer = setInterval(WaitForDialogToClose, 100);
        }
      });
    }
  });
}


function ConfigureDicomWebStowClient(resourceId, buttonId, positionOnPage)
{
  $('#' + buttonId).remove();

  var b = $('<a>')
      .attr('id', buttonId)
      .attr('data-role', 'button')
      .attr('href', '#')
      .attr('data-icon', 'forward')
      .attr('data-theme', 'e')
      .text('Send to DICOMweb server')
      .button();

  b.insertAfter($('#' + positionOnPage));

  b.click(function() {
    if ($.mobile.pageData) {
      ChooseDicomWebServer(function(server) {
        if (server != '' && resourceId != '') {
          var query = {
            'Resources' : [ resourceId ],
            'Synchronous' : false
          };
          
          $.ajax({
            url: '../${DICOMWEB_ROOT}/servers/' + server + '/stow',
            type: 'POST',
            dataType: 'json',
            data: JSON.stringify(query),
            async: false,
            error: function() {
              alert('Cannot submit job');
            },
            success: function(job) {
            }
          });
        }
      });
    }
  });
}


$('#patient').live('pagebeforeshow', function() {
  ConfigureDicomWebStowClient($.mobile.pageData.uuid, 'stow-patient', 'patient-info');
});

$('#study').live('pagebeforeshow', function() {
  ConfigureDicomWebStowClient($.mobile.pageData.uuid, 'stow-study', 'study-info');
});

$('#series').live('pagebeforeshow', function() {
  ConfigureDicomWebStowClient($.mobile.pageData.uuid, 'stow-series', 'series-info');
});

$('#instance').live('pagebeforeshow', function() {
  ConfigureDicomWebStowClient($.mobile.pageData.uuid, 'stow-instance', 'instance-info');
});

$('#lookup').live('pagebeforeshow', function() {
  $('#open-dicomweb-client').remove();
  
  var b = $('<fieldset>')
      .attr('id', 'open-dicomweb-client')
      .addClass('ui-grid-b')
      .append($('<div>')
              .addClass('ui-block-a'))
      .append($('<div>')
              .addClass('ui-block-b')
              .append($('<a>')
                      .attr('data-role', 'button')
                      .attr('href', '#')
                      .attr('data-icon', 'forward')
                      .attr('data-theme', 'a')
                      .text('Open DICOMweb client')
                      .button()
                      .click(function(e) {
                        window.open('../${DICOMWEB_ROOT}/app/client/index.html');
                      })));
  
  b.insertAfter($('#lookup-result'));
});

