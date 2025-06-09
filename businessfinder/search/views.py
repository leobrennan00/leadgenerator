import time
from collections import defaultdict

from django.conf import settings
from django.contrib import messages
from django.core.mail import send_mail
from django.db.models import Count
from django.shortcuts import render, redirect
import requests
from geopy.distance import geodesic
import re
from bs4 import BeautifulSoup
import csv
import os
from rapidfuzz import process, fuzz

from search.models import EmailAddress, BusinessType

#Google API key
API_KEY = 'AIzaSyCmTJMnIl4E3v5Y2u5Q1JqfhVj6aqKmPJ8'

#endpoint for Google Places API
endpoint_url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
place_details_url = "https://maps.googleapis.com/maps/api/place/details/json"

#where emails csv files are stored
EMAIL_FOLDER = os.path.join(os.path.dirname(__file__), '..', 'emails')

#Function to get email from website using web scraping
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


#Function to get place details (including the website, phone number, and address)
def get_place_details(place_id, api_key):
    params = {
        'place_id': place_id,
        'fields': 'website,formatted_phone_number,formatted_address',  #Request website, phone number, and address
        'key': api_key
    }

    #Send the request to Google Place Details API
    response = requests.get(place_details_url, params=params)
    result = response.json().get('result', {})

    website = result.get('website', 'Not available')
    phone_number = result.get('formatted_phone_number', 'Not available')
    address = result.get('formatted_address', 'Not available')

    email = 'Not available'
    if website != 'Not available':
        email = extract_email_from_website(website)

    return website, phone_number, address, email

#Function to read emails from the existing CSV file and return them as a set
def read_emails_from_csv():
    emails = set()
    try:
        with open('mechanic_emails.csv', mode='r', encoding='utf-8') as file:
            reader = csv.reader(file)
            for row in reader:
                emails.add(row[0])  #Assuming email is the first column
    except FileNotFoundError:
        pass  #If the file doesn't exist, return an empty set
    return emails

#function that also stores emails in a CSV
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
    from .models import EmailAddress, BusinessType

    params = {
        'location': f'{location[0]},{location[1]}',
        'radius': radius,
        'keyword': business,
        'key': api_key
    }

    total_results = 0
    trades_info = []
    emails_found = set()

    # Create or get the related business type object
    normalized_name = normalize_business_type(business)
    business_type_obj, _ = BusinessType.objects.get_or_create(name=normalized_name)

    while True:
        response = requests.get(endpoint_url, params=params)
        data = response.json()
        results = data.get('results', [])
        total_results += len(results)

        for place in results:
            place_id = place.get('place_id')
            website, phone_number, address, email = get_place_details(place_id, api_key)

            place_location = (place['geometry']['location']['lat'], place['geometry']['location']['lng'])
            distance = round(geodesic(location, place_location).km, 2)

            if distance <= (radius / 1000):
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

                # Store email and related business type in the database
                EmailAddress.objects.get_or_create(
                    email=email,
                    defaults={'business_type': business_type_obj}
                )

        if 'next_page_token' in data:
            params['pagetoken'] = data['next_page_token']
            time.sleep(2)  # small delay for next_page_token to activate
        else:
            break

    csv_filename = f"{business.lower().replace(' ', '_')}_emails.csv"
    write_emails_to_csv(emails_found, csv_filename)

    return trades_info, total_results


#example: allows both 'Carpenter' and 'Carpentry' search to have the same business type ID in database
def normalize_business_type(user_input, score_threshold=50):
    user_input = user_input.strip().lower()

    #Fetch existing business types
    existing_types = list(BusinessType.objects.values_list('name', flat=True))
    existing_types_lower = [t.lower() for t in existing_types]

    #Use token_set_ratio for more flexible matching
    best_match = process.extractOne(user_input, existing_types_lower, scorer=fuzz.partial_ratio, score_cutoff=score_threshold)

    if best_match:
        # Return the original-cased name from DB, not lowercase
        print(best_match[0])
        index = existing_types_lower.index(best_match[0])
        return existing_types[index]
    else:
        # No good match found — use original input (capitalized)
        return user_input.capitalize()



#View for handling search input and displaying results
def index(request):
    trades_info = []
    total_results = 0
    csv_files = list_csv_files_with_counts()

    #creates a dictionary
    email_lists = defaultdict(list)
    for entry in EmailAddress.objects.select_related("business_type"):
        if entry.business_type:
            email_lists[entry.business_type.name].append(entry.email)

    email_counts = EmailAddress.objects.values('business_type__name').annotate(count=Count('id'))

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
        'email_counts': email_counts,
        'email_lists': dict(email_lists)
    })

def send_email_view(request):
    # Get list of business types to display in a dropdown
    business_types = BusinessType.objects.all()

    if request.method == 'POST':
        subject = request.POST.get('subject')
        message = request.POST.get('message')
        selected_business_type_id = request.POST.get('business_type')

        #Gets emails associated with selected business type
        email_queryset = EmailAddress.objects.filter(business_type_id=selected_business_type_id).values_list('email', flat=True)

        for recipient in email_queryset:
            if recipient:
                try:
                    send_mail(subject, message, settings.EMAIL_HOST_USER, [recipient])
                    time.sleep(1)  #to avoid hitting email limits
                except Exception as e:
                    messages.error(request, f'Failed to send email to {recipient}: {e}')

        messages.success(request, 'Emails sent successfully.')
        return redirect('send_email')

    return render(request, 'search/send_email.html', {'business_types': business_types})
