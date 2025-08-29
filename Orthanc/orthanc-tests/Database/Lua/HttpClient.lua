-- for these tests, we issue HTTP requests to httpbin.org that performs smart echo (it returns all data/headers it has received + some extra data)
-- since these tests to httpbin.org fails a lot, we have added 10 retries
testSucceeded = true

local payload = {}
payload['stringMember'] = 'toto'
payload['intMember'] = 2

local httpHeaders = {}
httpHeaders['Content-Type'] = 'application/json'
httpHeaders['Toto'] = 'Tutu'

-- Issue HttpPost with body
retry = 10
response = nil
while retry > 0 and response == nil do
	print("HttpClient test: POST with body to httpbin.org")
	response = ParseJson(HttpPost('http://httpbin.org/post', DumpJson(payload), httpHeaders))
end
testSucceeded = testSucceeded and (response['headers']['Content-Type'] == 'application/json' and response['headers']['Toto'] == 'Tutu')
testSucceeded = testSucceeded and (response['json']['intMember'] == 2 and response['json']['stringMember'] == 'toto')
if not testSucceeded then print('Failed in HttpPost with body') PrintRecursive(response) end

-- Issue HttpPost without body
retry = 10
response = nil
while retry > 0 and response == nil do
	print("HttpClient test: POST without body to httpbin.org")
	response = ParseJson(HttpPost('http://httpbin.org/post', nil, httpHeaders))
end
testSucceeded = testSucceeded and (response['headers']['Content-Type'] == 'application/json' and response['headers']['Toto'] == 'Tutu')
testSucceeded = testSucceeded and (response['data'] == '')
if not testSucceeded then print('Failed in HttpPost without body') PrintRecursive(response) end

-- Issue HttpPut with body
retry = 10
response = nil
while retry > 0 and response == nil do
	print("HttpClient test: PUT with body to httpbin.org")
	response = ParseJson(HttpPut('http://httpbin.org/put', DumpJson(payload), httpHeaders))
end
testSucceeded = testSucceeded and (response['headers']['Content-Type'] == 'application/json' and response['headers']['Toto'] == 'Tutu')
testSucceeded = testSucceeded and (response['json']['intMember'] == 2 and response['json']['stringMember'] == 'toto')
if not testSucceeded then print('Failed in HttpPut with body') PrintRecursive(response) end

-- Issue HttpPut without body
retry = 10
response = nil
while retry > 0 and response == nil do
	print("HttpClient test: PUT without body to httpbin.org")
	response = ParseJson(HttpPut('http://httpbin.org/put', nil, httpHeaders))
end
testSucceeded = testSucceeded and (response['headers']['Content-Type'] == 'application/json' and response['headers']['Toto'] == 'Tutu')
testSucceeded = testSucceeded and (response['data'] == '')
if not testSucceeded then print('Failed in HttpPut without body') PrintRecursive(response) end

-- Issue HttpDelete (juste make sure it is issued, we can't check the response)
HttpDelete('http://httpbin.org/delete', httpHeaders)

-- TODO Very strange: Since Orthanc 1.6.0, a timeout frequently occurs
-- in curl at this point

-- Issue HttpGet
retry = 10
response = nil
while retry > 0 and response == nil do
	print("HttpClient test: GET to httpbin.org")
	response = ParseJson(HttpGet('http://httpbin.org/get', httpHeaders))
end
testSucceeded = testSucceeded and (response['headers']['Content-Type'] == 'application/json' and response['headers']['Toto'] == 'Tutu')
if not testSucceeded then print('Failed in HttpGet') PrintRecursive(response) end


system = ParseJson(RestApiGet('/system'))

if system['Version'] == 'mainline' or system['Version'] == '1.11.1' or system['ApiVersion'] >= 18 then  -- introduced in 1.11.1 which is ApiVersion 17 (too lazy to reimplement IsAboveOrthancVersion in lua :-) )
	-- Test SetHttpTimeout
	SetHttpTimeout(10)
	print("HttpClient test: GET with timeout (10) to httpstat.us")
	response = HttpGet('https://httpstat.us/200?sleep=1000')
	testSucceeded = testSucceeded and (response == '200 OK')
	if not testSucceeded then print('Failed in SetHttpTimeout1') PrintRecursive(response) end

	SetHttpTimeout(1)
	print("HttpClient test: GET with timeout (1) to httpstat.us")
	response = HttpGet('https://httpstat.us/200?sleep=2000')
	testSucceeded = testSucceeded and (response == nil)
	if not testSucceeded then print('Failed in SetHttpTimeout2') PrintRecursive(response) end
end

if testSucceeded then
	print('OK')
else
	print('FAILED')
end
