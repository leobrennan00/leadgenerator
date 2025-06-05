import requests
from geopy.distance import geodesic
import re
from bs4 import BeautifulSoup

# Your Google API key
API_KEY = 'AIzaSyCmTJMnIl4E3v5Y2u5Q1JqfhVj6aqKmPJ8'

# Your location's latitude and longitude (optional for distance)
my_location = (54.3948301, -8.5284118)  # replace with your actual coordinates

# Define the country code (ISO 3166-1 alpha-2) to restrict the search
country_code = 'IE'  # For the United States, change it as per your country

# Radius for the search (in meters, 40km = 40,000 meters) - Optional for restricting results
radius = 100000

# What type of business is searched
business = 'electrician'

# Define the endpoint for Google Places API Text Search
endpoint_url = "https://maps.googleapis.com/maps/api/place/textsearch/json"#

place_details_url = "https://maps.googleapis.com/maps/api/place/details/json"


# Function to get email from website (basic extraction)
def extract_email_from_website(website_url):
    try:
        response = requests.get(website_url, timeout=5)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            # Look for mailto: links (simple email extraction)
            mailto_links = soup.find_all('a', href=re.compile('mailto:'))
            emails = [link['href'].replace('mailto:', '') for link in mailto_links if 'href' in link.attrs]
            if emails:
                return emails[0]  # return the first found email
        return 'Not available'
    except requests.exceptions.RequestException:
        return 'Not available'


# Function to get place details (including the website, phone number, and address)
def get_place_details(place_id, api_key):
    params = {
        'place_id': place_id,
        'fields': 'website,formatted_phone_number,formatted_address',  # Request website, phone number, and address
        'key': api_key
    }

    # Send the request to Google Place Details API
    response = requests.get(place_details_url, params=params)
    result = response.json().get('result', {})

    # Get the website, phone number, and address from the result
    website = result.get('website', 'Not available')
    phone_number = result.get('formatted_phone_number', 'Not available')
    address = result.get('formatted_address', 'Not available')

    # Try to extract email from the website if available
    email = 'Not available'
    if website != 'Not available':
        email = extract_email_from_website(website)

    return website, phone_number, address, email


# Function to search for businesses of a certain type (electrician) in a country using Text Search
def search_trades_by_country(api_key):
    query = f'{business} in {country_code}'  # Search for electricians in the specified country
    trades_info = []

    # First request to fetch the initial set of results
    params = {
        'query': query,
        'key': api_key
    }

    # Loop to handle pagination if there are more results
    while True:
        response = requests.get(endpoint_url, params=params)
        results = response.json().get('results', [])

        # Extract business details from the response
        for place in results:
            website = place.get('website', 'Not available')
            place_id = place.get('place_id')

            # Get website, phone number, address, and email using Place Details API
            website, phone_number, address, email = get_place_details(place_id, api_key)

            # Calculate the distance from the user's location
            if my_location:
                place_location = (place['geometry']['location']['lat'], place['geometry']['location']['lng'])
                distance = geodesic(my_location, place_location).km
            else:
                distance = 'N/A'

            trades_info.append({
                'name': place.get('name', 'No name provided'),
                'website': website,
                'phone_number': phone_number,
                'address': address,
                'email': email,
                'distance': distance
            })

        # Check if there's a next page of results
        next_page_token = response.json().get('next_page_token')
        if next_page_token:
            # Add the next page token to the params to fetch the next set of results
            params['pagetoken'] = next_page_token
        else:
            break  # No more pages, exit the loop

    return trades_info


# Main function to get trades' websites, phone numbers, addresses, and emails
def get_trades_info(api_key):
    trades = search_trades_by_country(api_key)
    return trades


# Call the main function
trades_info = get_trades_info(API_KEY)

# Print out the list of trades with their websites, phone numbers, addresses, and emails
for trades in trades_info:
    print(f"Business: {business}")
    print(f"Name: {trades['name']}")
    print(f"Website: {trades['website']}")
    print(f"Phone Number: {trades['phone_number']}")
    print(f"Address: {trades['address']}")
    print(f"Email: {trades['email']}")
    print(f"Distance: {trades['distance']}")
    print("-" * 40)
