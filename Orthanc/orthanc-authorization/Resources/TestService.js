var port = 8000;

var http = require('http');
var url = require('url');

function GrantAccess(response, granted, validity) {
  var answer = {
    granted: granted
  }

  if (typeof validity == 'number') {
    answer.validity = validity;
  }
  
  response.writeHead(200, { 'Content-Type' : 'application/json' });
  response.end(JSON.stringify(answer));
}

var server = http.createServer(function(request, response) {
  if (request.method == 'POST') {
    var body = '';

    request.on('data', function (data) {
      body += data;
    });

    request.on('end', function () {
      console.log('Received authorization request: ' + body);
      console.log('HTTP headers: ' + JSON.stringify(request.headers));

      var query = JSON.parse(body);

      //GrantAccess(response, query["level"] != "system", 5);
      GrantAccess(response, true, 5);
      //GrantAccess(response, false, 5);
    });
    
  } else {
    response.writeHead(405);
    response.end();
  }
});


console.log('The demo is running at http://localhost:' + port + '/');
server.listen(port);
