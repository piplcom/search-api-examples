#simple app to test match_requirments
from piplapis.search import SearchAPIRequest
from piplapis.search import SearchAPIResponse
from piplapis.error import APIError

request = SearchAPIRequest(email="gmoult@gmail.com", match_requirements="url|social_profiles", api_key="YOURKEYHERE")
piplAPIResponse = request.send()
testJSON = piplAPIResponse.to_json()
print(testJSON)
