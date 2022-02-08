#simple app to demonstrate using job and organization as query parameters in a full person search

import piplapis.data as fields
from piplapis.search import SearchAPIRequest
from piplapis.search import SearchAPIResponse
from piplapis.error import APIError

query_fields = [fields.Job(title="Field Reporter", organization="The Daily Planet"),
                fields.Email("clark.kent@example.com")]
query_person = fields.Person(fields=query_fields)
request = SearchAPIRequest(person=query_person, api_key="YOUR_KEY_HERE")
piplAPIResponse = request.send()
response_json = piplAPIResponse.to_json()
print(response_json)