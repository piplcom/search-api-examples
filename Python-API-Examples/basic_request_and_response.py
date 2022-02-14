#Hello World for the Pipl API. Test a basic request and response
from piplapis.search import SearchAPIRequest
from piplapis.search import SearchAPIResponse
from piplapis.error import APIError

request = SearchAPIRequest(email="clark.kent@example.com", api_key="YOUR_KEY_HERE")
piplAPIResponse = request.send()
print(piplAPIResponse.to_json())
