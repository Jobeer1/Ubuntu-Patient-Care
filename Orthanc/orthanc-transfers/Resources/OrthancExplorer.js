function TransfersAcceleratorSelectPeer(callback)
{
  var items = $('<ul>')
    .attr('data-divider-theme', 'd')
    .attr('data-role', 'listview');

  $.ajax({
    url: '../transfers/peers',
    type: 'GET',
    dataType: 'json',
    async: false,
    cache: false,
    success: function(peers) {
      console.log(peers);
      var clickedPeer = null;
      
      for (var name in peers) {
        if (peers.hasOwnProperty(name)) {
          var item = $('<li>')
              .html('<a href="#" rel="close">' + name + '</a>')
              .attr('name', name)
              .click(function() { 
                clickedPeer = $(this).attr('name');
              });

          if (peers[name] != 'installed' &&
              peers[name] != 'bidirectional') {
            item.addClass('ui-disabled');
          }

          items.append(item);          
        }
      }

      // Launch the dialog
      $('#dialog').simpledialog2({
        mode: 'blank',
        animate: false,
        headerText: 'Choose Orthanc peer',
        headerClose: true,
        forceInput: false,
        width: '100%',
        blankContent: items,
        callbackClose: function() {
          var timer;
          function WaitForDialogToClose() {
            if (!$('#dialog').is(':visible')) {
              clearInterval(timer);
              if (clickedPeer !== null) {
                callback(clickedPeer);
              }
            }
          }
          timer = setInterval(WaitForDialogToClose, 100);
        }
      });
    }
  });
}


function TransfersAcceleratorAddSendButton(level, siblingButton)
{
  var b = $('<a>')
    .attr('data-role', 'button')
    .attr('href', '#')
    .attr('data-icon', 'search')
    .attr('data-theme', 'e')
    .text('Transfers accelerator');

  b.insertBefore($(siblingButton).parent().parent());

  b.click(function() {
    if ($.mobile.pageData) {
      var uuid = $.mobile.pageData.uuid;
      TransfersAcceleratorSelectPeer(function(peer) {
        console.log('Sending ' + level + ' ' + uuid + ' to peer ' + peer);

        var query = {
          'Resources' : [
            {
              'Level' : level,
              'ID' : uuid
            }
          ], 
          'Compression' : 'gzip',
          'Peer' : peer
        };

        $.ajax({
          url: '../transfers/send',
          type: 'POST',
          dataType: 'json',
          data: JSON.stringify(query),
          success: function(job) {
            if (!(typeof job.ID === 'undefined')) {
              $.mobile.changePage('#job?uuid=' + job.ID);
            }
          },
          error: function() {
            alert('Error while creating the transfer job');
          }
        });  
      });
    }
  });
}



$('#patient').live('pagebeforecreate', function() {
  TransfersAcceleratorAddSendButton('Patient', '#patient-delete');
});

$('#study').live('pagebeforecreate', function() {
  TransfersAcceleratorAddSendButton('Study', '#study-delete');
});

$('#series').live('pagebeforecreate', function() {
  TransfersAcceleratorAddSendButton('Series', '#series-delete');
});
