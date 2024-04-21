import requests
import json
import time
import sys

# Constants for the API endpoints
BASE_URL = 'https://api.rentman.net'
JWT_TOKEN = ''  # Create a file called "JWT_TOKEN" (without file extension), put the JWT token there, it will be read by this script and inserted.

# Function to get all equipment
def get_all_equipment():
    url = f"{BASE_URL}/equipment"
    headers = {
        'Authorization': f"Bearer {JWT_TOKEN}"
    }
    response = requests.get(url, headers=headers)
    return response.json()

# Function to get files for a specific equipment item
def get_equipment_files(equipment_id):
    url = f"{BASE_URL}/equipment/{equipment_id}/files"
    headers = {
        'Authorization': f"Bearer {JWT_TOKEN}"
    }
    response = requests.get(url, headers=headers)
    return response.json()

# Function to update the progress in the console
def update_progress(current, total):
    sys.stdout.write('\rCollecting Equipment Files... {}/{}'.format(current, total))
    sys.stdout.flush()

# Main script
if __name__ == '__main__':
    # Fetch all equipment data
    equipment_data = get_all_equipment()
    equipment_items = equipment_data['data'][:10]  # Adjust this according to the actual response structure

    # Number of equipment items
    total_items = len(equipment_items)
    print("Total equipment items to process:", total_items)

    # Iterate through equipment and fetch files
    all_equipment_files = {}
    last_request_time = time.time()

    for index, item in enumerate(equipment_items, start=1):
        equipment_id = item['id']  # Adjust this according to the actual response key for equipment ID
        update_progress(index, total_items)  # Update the progress before the API call

        # Ensure that at least 0.66 seconds have passed since the last request
        # Max of 20 req./s
        current_time = time.time()
        elapsed = current_time - last_request_time
        if elapsed < 0.066:
            time.sleep(0.066- elapsed)
        
        files_data = get_equipment_files(equipment_id)
        last_request_time = time.time()
        ## file_urls = [file['url'] for file in files_data['data'] if 'rentman-tempstorage' not in file['url']]  # Filter out deleted images
        file_urls = [file for file in files_data['data']]
        
        # Exclude file URLs that contain 'rentman-tempstorage'
        # Those are labels.pdf and are not loadable
        all_equipment_files[equipment_id] = file_urls

    # Finish progress
    sys.stdout.write('\n')
    sys.stdout.flush()

    # Save all equipment and file URLs to a JSON file
    with open('collectAllEquipmentPhotoUrls.json', 'w') as f:
        json.dump(all_equipment_files, f, indent=4)

    print("All equipment and associated file URLs have been saved to 'collectAllEquipmentPhotoUrls.json'")
