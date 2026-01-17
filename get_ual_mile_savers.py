import requests
import csv
import time

# Here for future use if needed
def dedupe_dest_code(data):
    seen = set()
    deduped = []
    for item in data:
        city = item.get("city")
        if city not in seen:
            seen.add(city)
            deduped.append(item)
    return deduped
#####################

# Import airport codes and geoIDs
import csv

# Initialize the dictionary
aircodes = {}

# Path to your CSV file
csv_file_path = 'aircodes.csv'  # Change this to your actual file path

# Read the CSV file
with open(csv_file_path, mode='r', newline='', encoding='utf-8') as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        code = row['code']
        id_value = row['id']
        aircodes[code] = id_value

# Ask user for airport code
start_code = input("Enter Airport Code: ")
start_code=start_code.upper()

# United Miles Awards GraphQL endpoint
url = "https://vg-api.airtrfx.com/graphql"
headers = {
    "Content-Type": "application/json"
}

# Initial payload to get the list of fares
initial_payload = [{
    "variables": {
        "page": {
            "tenant": "ua",
            "slug": "featured-awards",
            "siteEdition": "en-us"
        },
        "id": "63e2fb7a2b30207947018f73",
        "flatContext": {
            "siteEditionCountryGeoId": "6252001",
            "templateName": "Custom Page: Featured Awards"
        },
        "filters": {
            "origin": {
                "code": start_code,
                "geoId": aircodes[start_code]
            },
            "travelClass": "ECONOMY"
        },
        "urlParameters": {},
        "nearestOriginAirport": {}
    },
    "query": "query ($page: PageInput!, $id: String!, $pageNumber: Int, $limit: Int, $flatContext: FlatContextInput, $urlParameters: StandardFareModuleUrlParameters, $filters: StandardFareModuleFiltersInput, $nearestOriginAirport: AirportInput) {\n  standardFareModule(page: $page, id: $id, pageNumber: $pageNumber, limit: $limit, flatContext: $flatContext, urlParameters: $urlParameters, filters: $filters, nearestOriginAirport: $nearestOriginAirport) {\n    fares(pageNumber: $pageNumber, limit: $limit, urlParameters: $urlParameters, nearestOriginAirport: $nearestOriginAirport) {\n      originCity\n      destinationCity\n      originAirportCode\n      destinationAirportCode\n      formattedDepartureDate\n      formattedReturnDate\n      formattedTravelClass\n      usdTotalPrice\n      currencyCode\n      formattedTotalPrice\n      totalPrice\n      redemption {\n        unit\n        formattedAmount\n        formattedTaxAmount\n      }\n    }\n  }\n}"
}]

# Fetch initial fares
response = requests.post(url, json=initial_payload, headers=headers)

#print(response.json())
#exit()

fares = response.json()[0]['data']['standardFareModule']['fares']

# Prepare CSV output
csv_file = "c:\\users\daren\\iad_featured_awards2.csv"
fieldnames = [
    "Flight Pairing", "Origin", "Destination", "Origin Code", "Destination Code",
    "Depart Date", "Return Date", "Class",
    "Origin Fare in Miles", "Destination Fare in Miles", "Total Fare in Miles"
]

# Dictionary to store dest codes that have already been queried, so no requery necessary
dest_done={}

with open(csv_file, mode='w', newline='', encoding='utf-8') as file:
    writer = csv.DictWriter(file, fieldnames=fieldnames)
    writer.writeheader()

    for fare in fares:

        # Print each individual outbound flight

        print("\nFound flight: "+fare.get("originAirportCode")+"-"+fare.get("destinationAirportCode"))

        # Now fetch any related return flights for this origination

        dest_code = fare.get("originAirportCode")
        orig_code = fare.get("destinationAirportCode")

        # Construct new payload with current originAirportCode
        followup_payload = [{
            "variables": {
                "page": {
                    "tenant": "ua",
                    "slug": "featured-awards",
                    "siteEdition": "en-us"
                },
                "id": "63e2fb7a2b30207947018f73",
                "flatContext": {
                    "siteEditionCountryGeoId": "6252001",
                    "templateName": "Custom Page: Featured Awards"
                },
                "filters": {
                    "origin": {
                        "code": orig_code,
                        "geoId": aircodes[orig_code]
                    },
                    "destination": {
                        "code": dest_code,
                        "geoId": aircodes[dest_code]
                    },
                    "travelClass": "ECONOMY"
                },
                "urlParameters": {},
                "nearestOriginAirport": {}
            },
            "query": initial_payload[0]["query"]
        }]

#        print(followup_payload)

        # Find return flights (if not already done previously)
        if dest_done.get(fare.get("destinationAirportCode")):

            print("\t\t>>> Using cached dest data for "+orig_code+"-"+dest_code)

            # Use cached dest data from previous fetch
            for sub_fare in dest_done[fare.get("destinationAirportCode")]:

########### WHEN DEST IS CACHED: HERE IS WHERE WE COMBINE THE DEPARTURE AND RETURN FLIGHTS TOGETHER - IF THEY EXIST #############

                if fare.get("formattedDepartureDate") < sub_fare.get("formattedDepartureDate"):

##### TO DO: If no return flights earlier, we should still write the original outbound to disk

                    writer.writerow({
                    "Origin": fare.get("originCity"),
                    "Destination": fare.get("destinationCity"),
                    "Origin Code": fare.get("originAirportCode"),
                    "Destination Code": fare.get("destinationAirportCode"),
                    "Depart Date": fare.get("formattedDepartureDate"),
                    "Return Date": sub_fare.get("formattedDepartureDate"),
                    "Class": fare.get("formattedTravelClass")+"/"+sub_fare.get("formattedTravelClass"),
                    "Origin Fare in Miles": fare.get("usdTotalPrice"),
                    "Destination Fare in Miles": sub_fare.get("usdTotalPrice"),
                    "Total Fare in Miles": fare.get("usdTotalPrice") + sub_fare.get("usdTotalPrice"),
                    "Flight Pairing": fare.get("originAirportCode")+"-"+fare.get("destinationAirportCode")
                    })

            # Done - continue on with next originating flight, no need to fetch return data as already populated
            continue

        print("Fetching return flights: "+orig_code+"-"+dest_code)

        try:
            followup_resp = requests.post(url, json=followup_payload, headers=headers)

            followup_data = followup_resp.json()
#            print(followup_data)

            if not followup_data[0]['data']['standardFareModule']['fares']:

########### NO RETURN AWARD FLIGHTS FOUND SO STORE DUMMY DATA (FOR QUERY CACHE) AND THIS ORIG ENTRY WITH NO RETURN

                dest_done[fare.get("destinationAirportCode")] = {}

                writer.writerow({
                    "Origin": fare.get("originCity"),
                    "Destination": fare.get("destinationCity"),
                    "Origin Code": fare.get("originAirportCode"),
                    "Destination Code": fare.get("destinationAirportCode"),
                    "Depart Date": fare.get("formattedDepartureDate"),
                    "Return Date": fare.get("formattedReturnDate"),
                    "Class": fare.get("formattedTravelClass"),
                    "Origin Fare in Miles": fare.get("usdTotalPrice"),
                    "Destination Fare in Miles": "N/A",
                    "Total Fare in Miles": "N/A",
                    "Flight Pairing": fare.get("originAirportCode")+"-"+fare.get("destinationAirportCode")
                })

                # No need to iterate through subfares so continue to next outbound
                continue

########### QUERY FOR DEST FARES

            sub_fares = followup_data[0]['data']['standardFareModule']['fares']

########### WHEN DEST IS QUERIED: HERE IS WHERE WE COMBINE THE DEPARTURE AND RETURN FLIGHTS TOGETHER - IF THEY EXIST #############

            for sub_fare in sub_fares:

                if fare.get("formattedDepartureDate") < sub_fare.get("formattedDepartureDate"):

##### TO DO: If no return flights earlier, we should still write the original outbound to disk (else: writer write only fare.get)

                    writer.writerow({
                    "Origin": fare.get("originCity"),
                    "Destination": fare.get("destinationCity"),
                    "Origin Code": fare.get("originAirportCode"),
                    "Destination Code": fare.get("destinationAirportCode"),
                    "Depart Date": fare.get("formattedDepartureDate"),
                    "Return Date": sub_fare.get("formattedDepartureDate"),
                    "Class": fare.get("formattedTravelClass")+"/"+sub_fare.get("formattedTravelClass"),
                    "Origin Fare in Miles": fare.get("usdTotalPrice"),
                    "Destination Fare in Miles": sub_fare.get("usdTotalPrice"),
                    "Total Fare in Miles": fare.get("usdTotalPrice") + sub_fare.get("usdTotalPrice"),
                    "Flight Pairing": fare.get("originAirportCode")+"-"+fare.get("destinationAirportCode")
                    })

                #STORE FOR NEXT ENTRY THAT CONTAINS THIS DEST
                dest_done[fare.get("destinationAirportCode")] = sub_fares

        except Exception as e:

############## NO RETURN AWARD FLIGHTS FOUND SO STORE DUMMY DATA AND STORE THIS OUTBOUND ENTRY

            dest_done[fare.get("destinationAirportCode")] = {}

            writer.writerow({
                "Origin": fare.get("originCity"),
                "Destination": fare.get("destinationCity"),
                "Origin Code": fare.get("originAirportCode"),
                "Destination Code": fare.get("destinationAirportCode"),
                "Depart Date": fare.get("formattedDepartureDate"),
                "Return Date": fare.get("formattedReturnDate"),
                "Class": fare.get("formattedTravelClass"),
                "Origin Fare in Miles": fare.get("usdTotalPrice"),
                "Destination Fare in Miles": "N/A",
                "Total Fare in Miles": "N/A",
                "Flight Pairing": fare.get("originAirportCode")+"-"+fare.get("destinationAirportCode")
            })

            print(f"Error querying for {orig_code}-{dest_code}")

        # Throttle requests slightly to avoid hammering the API
        time.sleep(1)

print(f"Detailed award data saved to {csv_file}")
