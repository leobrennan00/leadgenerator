from django.shortcuts import render
import requests
from geopy.distance import geodesic
import re
from bs4 import BeautifulSoup
import csv
import os

# Your Google API key
API_KEY = 'AIzaSyCmTJMnIl4E3v5Y2u5Q1JqfhVj6aqKmPJ8'

# Define the endpoint for Google Places API
endpoint_url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
place_details_url = "https://maps.googleapis.com/maps/api/place/details/json"

EMAIL_FOLDER = os.path.join(os.path.dirname(__file__), '..', 'emails')

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

    website = result.get('website', 'Not available')
    phone_number = result.get('formatted_phone_number', 'Not available')
    address = result.get('formatted_address', 'Not available')

    email = 'Not available'
    if website != 'Not available':
        email = extract_email_from_website(website)

    return website, phone_number, address, email

# Function to read emails from the existing CSV file and return them as a set
def read_emails_from_csv():
    emails = set()
    try:
        with open('mechanic_emails.csv', mode='r', encoding='utf-8') as file:
            reader = csv.reader(file)
            for row in reader:
                emails.add(row[0])  # Assuming email is the first column
    except FileNotFoundError:
        pass  # If the file doesn't exist, return an empty set
    return emails


def write_emails_to_csv(emails, filename):

    folder_path = os.path.join(os.path.dirname(__file__), '..', 'emails')
    os.makedirs(folder_path, exist_ok=True)

    file_path = os.path.join(folder_path, filename)

    existing_emails = set()
    if os.path.exists(file_path):
        with open(file_path, mode='r', encoding='utf-8') as file:
            reader = csv.reader(file)
            for row in reader:
                if row:
                    existing_emails.add(row[0])

    with open(file_path, mode='a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        for email in emails:
            if email not in existing_emails:
                writer.writerow([email])
                existing_emails.add(email)

def list_csv_files_with_counts():
    files = []
    if os.path.exists(EMAIL_FOLDER):
        for filename in os.listdir(EMAIL_FOLDER):
            if filename.endswith('.csv'):
                file_path = os.path.join(EMAIL_FOLDER, filename)
                try:
                    with open(file_path, mode='r', encoding='utf-8') as f:
                        reader = csv.reader(f)
                        email_count = sum(1 for row in reader if row and row[0] != 'email')  # skip header
                except Exception as e:
                    email_count = 0
                files.append({'name': filename, 'count': email_count})
    return files



# Function to search for trades near a location
def search_trades_nearby(location, radius, business, api_key):
    params = {
        'location': f'{location[0]},{location[1]}',  # lat, long
        'radius': radius,  # in meters
        'keyword': business,  # search for business
        'key': api_key
    }

    #resets place count every search
    total_results = 0


    trades_info = []
    emails_found = set()

    while True:
        response = requests.get(endpoint_url, params=params)
        data = response.json()

        # Log the response data for debugging
        #print(f"API Response: {data}")  # Logs the raw response for inspection

        results = data.get('results', [])

        num_results = len(results)
        total_results += num_results

        for place in results:
            website = place.get('website', 'Not available')
            place_id = place.get('place_id')

            website, phone_number, address, email = get_place_details(place_id, api_key)

            place_location = (place['geometry']['location']['lat'], place['geometry']['location']['lng'])
            distance = geodesic(location, place_location).km

            # Round the distance to 2 decimal places
            distance = round(distance, 2)

            # Log the calculated distance for debugging
            print(f"Distance to {place['name']}: {distance} km")

            if distance <= (radius / 1000):  # Only include businesses within the radius
                trades_info.append({
                    'name': place.get('name', 'No name provided'),
                    'website': website,
                    'phone_number': phone_number,
                    'address': address,
                    'email': email,
                    'distance': distance
                })

            if email != 'Not available':
                emails_found.add(email)

        # Pagination: Check if there is a next page of results
        next_page_token = data.get('next_page_token')
        if next_page_token:
            params['pagetoken'] = next_page_token
        else:
            break

    # Write found emails to CSV after fetching all data
    csv_filename = f"{business.lower().replace(' ', '_')}_emails.csv"
    write_emails_to_csv(emails_found, csv_filename)

    return trades_info, total_results


# View for handling search input and displaying results
def index(request):
    trades_info = []
    total_results = 0
    csv_files = list_csv_files_with_counts()

    if request.method == "POST":
        latitude = float(request.POST['latitude'])
        longitude = float(request.POST['longitude'])
        radius = int(request.POST['radius'])
        business_type = request.POST['business']

        location = (latitude, longitude)
        trades_info, total_results = search_trades_nearby(location, radius, business_type, API_KEY)

    return render(request, 'search/index.html',{

        'trades_info': trades_info,
        'total_results': total_results,
        'csv_files': csv_files})
