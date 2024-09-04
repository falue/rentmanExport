import requests
import argparse
import json
import time
import sys
import os
import urllib.parse  # For handling URL to filename conversion
import pypandoc
import datetime


# Constants for the API endpoints
BASE_URL = 'https://api.rentman.net'
JWT_TOKEN = ''  # Create a file called "JWT_TOKEN" (without file extension), put the JWT token there, it will be read by this script and inserted.

# Only export first n of your equipment collection.
# Set to 0 if you want it all.
# Note that after 300 equipments some rule imposed by the rentman API will kick in. Needs work for that I guess.
start_index = 0  # 0 for starting at first object
num_obj_export = 4

# Set up argument parsing
parser = argparse.ArgumentParser(description='Collect data and export files.')
parser.add_argument('--start', type=int, help='Start index', default=num_obj_export)  # Default start index is 0
parser.add_argument('--num', type=int, help='Number of objects to export', default=start_index)  # Default number of objects to export is 5

# Parse the arguments
args = parser.parse_args()

# Assign variables from arguments
start_index = args.start
num_obj_export = args.num

# Detailed printouts
verbose = True

# Caveat: "Custom fields are not queryable." (https://api.rentman.net/#section/Introduction/Custom-fields)
extra_input_fields = {
    "custom_1": "Artikelbeschreibung in Englisch",
    "custom_4": "Bemerkung an Mieter\\*in",
    "custom_7": "Baujahr",
    "custom_8": "Kategorie"
}

def load_file_content(file_path):
    try:
        with open(file_path, 'r') as file:
            return file.read().strip()  # Read the token and strip any extra whitespace
    except FileNotFoundError:
        print(f"The file '{file_path}' was not found.")
        return None
    except Exception as e:
        print(f"An error occurred: {e}")
        return None
    
def safe_filename(url):
    """Create a safe filename from a URL."""
    # Extract the file name from the URL, decode any URL-encoded characters
    parsed_url = urllib.parse.urlparse(url)
    # Extract the file name from the path component of the URL
    filename = os.path.basename(parsed_url.path)
    # Decode any URL-encoded characters
    filename = urllib.parse.unquote(filename)
    # Remove any unsafe characters
    return "".join(c for c in filename if c.isalnum() or c in (' ', '.', '_', '-')).rstrip()

## saves paths as URL enc oded but makes it little readable in finder
def safe_filename_NEW(url):
    """Create a safe filename from a URL."""
    # Extract the file name from the URL
    filename = urllib.parse.unquote(os.path.basename(url))
    # URL encode the filename to ensure it's safe for file systems and URLs
    # This replaces "ü", spaces, and special characters with percent-encoded values
    safe_encoded_filename = urllib.parse.quote(filename, safe='')
    return safe_encoded_filename

def revert_to_original_filename(safed_filename):
    """Decode a URL-safe filename back to its original form."""
    return urllib.parse.unquote(safed_filename)

# Function to get all equipment
def get_all_equipment():
    url = f"{BASE_URL}/equipment"
    headers = {
        'Authorization': f"Bearer {JWT_TOKEN}"
    }
    response = requests.get(url, headers=headers)
    return response.json()

# Function to get specific equipment
def get_equipment(equipment_id):
    url = f"{BASE_URL}/equipment/{equipment_id}"
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

def get_categories():
    # Categories aka folders in rentman system
    url = f"{BASE_URL}/folders"
    headers = {'Authorization': f"Bearer {JWT_TOKEN}"}
    response = requests.get(url, headers=headers)
    folders = response.json()
    return {folder['id']: folder for folder in folders['data']}

# Function to download file
def download_file(url, folder_path):
    filename = safe_filename(url)
    response = requests.get(url)
    if response.status_code == 200:
        file_path = os.path.join(folder_path, filename)
        with open(file_path, 'wb') as f:
            f.write(response.content)
        return filename  # Return the filename for inclusion in JSON and Markdown files
    return None  # In case of download failure

def convert_md_to_pdf(md_file_path, output_pdf_path, resource_path):
    try:
        # Convert markdown to PDF using Pandoc
        pypandoc.convert_file(md_file_path, 'pdf', outputfile=output_pdf_path, extra_args=(["-V", "papersize:a4", "-V", "geometry:margin=1.5cm", f"--resource-path={resource_path}", "--embed-resources", "--standalone"]))
    except Exception as e:
        print("\nAn error occurred while generating PDF; skipping:", e)

# Function to update the progress in the console
def update_progress(current, total, files_download, filename):
    """
    Update and display the progress of data collection and file creation in the terminal.
    """
    # Calculate the percentage of completion
    percent_complete = (current / total) * 100
    # Determine the length of the progress bar
    bar_length = 40
    filled_length = int(bar_length * current // total)
    
    # Create the progress bar
    bar = '█' * filled_length + '▒' * (bar_length - filled_length)
    
    # Prepare the message to display
    progress_message = f"\r{current}/{total} {bar} {percent_complete:.1f}% - Gathering {files_download} {'file' if files_download == 1 else 'files'} and data of '{filename}'                                            "
    
    # Write the progress message to standard output
    sys.stdout.write(progress_message)
    sys.stdout.flush()

# Main script
if __name__ == '__main__':
    JWT_TOKEN = load_file_content('JWT_TOKEN')

    if(num_obj_export > 0):
        print(f"Limit export of {num_obj_export} equipment. Change in the code to any other integer or to 0 if you want to export everything.\n")
    else:
        print(f"Reading database, export everything.\n")

    root_folder = 'equipmentDump'
    os.makedirs(root_folder, exist_ok=True)  # Create root directory

    categories = get_categories()  # Retrieve all folders (aka categories)
    equipment_data = get_all_equipment()
    # equipment_items = equipment_data['data']
    if(num_obj_export > 0):
        # Limit to first n equipment items for testing
        #equipment_items = equipment_data['data'][:num_obj_export]
        equipment_items = equipment_data['data'][start_index:start_index + num_obj_export]
    else:
        equipment_items = equipment_data['data']

    last_request_time = time.time()  # Initialize the last request time

    print(f"Collecting equipment data and creating files…")

    for index, item in enumerate(equipment_items, start=1):
        equipment_name = safe_filename(item.get('name', 'Unknown'))
        equipment_id = item['id']

        if(verbose):
            #print(f"\nCollecting {index}/{len(equipment_items)}: '{equipment_id} - {equipment_name}'")
            if(num_obj_export>0):
                tot_export = start_index+num_obj_export
            else:
                tot_export = len(equipment_items)
            print(f"\nCollecting {start_index+index}/{tot_export}: '{equipment_id} - {equipment_name}'")

        category_path = item.get('folder', None)  # eg.  "folder": "/folders/55"
        # Add human readable key/value to item - ATTENTION: This is *not* according to specs of rentman
        # in equipment:
        #   "folder": "/folders/55"
        #
        # in categories:
        #   55: {'id': 55, 'created': '2023-12-09T20: 07: 09+01: 00', 'modified': '2024-02-11T13: 19: 59+01: 00', 'creator': '/crew/33', 'displayname': 'Sideboards', 'parent': '/folders/50', 'name': 'Sideboards', 'order': 10, 'itemtype': 'equipment', 'path': 'MÖBEL & GROSSREQUISITEN/Sideboards', 'updateHash': '84bba838972ede16a4c8ce4ea286d3bc'

        if(category_path):
            category_path = os.path.basename(category_path)  # eg. 55
            category_path_human_readable = categories[int(category_path)]["path"]  # Find human readable path in categories
            item["folder_path"] = category_path_human_readable
            if(verbose):
                print(f"   Joining additional data from /folders/{{id}} call: {category_path_human_readable}")
        else:
            item["folder_path"] = "."

        folder_name = f"{item['code']}_{item['qrcodes']}_{equipment_name}"
        folder_path = os.path.join(root_folder, folder_name)
        if(item.get('in_archive')):
            folder_path = os.path.join(root_folder, "_archived", folder_name)
        os.makedirs(folder_path, exist_ok=True)

        # Get additional details that is not delivered by "{BASE_URL}/equipment" call
        item_details = get_equipment(equipment_id)
        # item["country_of_origin"] = item_details["data"]["country_of_origin"]  # country_of_origin is not available somehow
        item["current_quantity_excl_cases"] = item_details["data"]["current_quantity_excl_cases"]
        item["current_quantity"] = item_details["data"]["current_quantity"]
        item["quantity_in_cases"] = item_details["data"]["quantity_in_cases"]
        if(verbose):
            print(f"   Joining additional data from /equipment/{{id}} call:")
            print(f"      - current_quantity_excl_cases:\t{item['current_quantity_excl_cases']}")
            print(f"      - current_quantity:\t\t{item['current_quantity']}")
            print(f"      - quantity_in_cases:\t\t{item['quantity_in_cases']}")


        # Save all data to JSON
        data_file_path = os.path.join(folder_path, 'data.json')
        with open(data_file_path, 'w') as f:
            json.dump(item, f, indent=4)

        # Ensure rate limiting before fetching files
        # Rentman API does not allow more than 20 requests per second
        current_time = time.time()
        elapsed = current_time - last_request_time
        if elapsed < 0.1:
            time.sleep(0.1 - elapsed)
        last_request_time = time.time()

        # Download and save file URLs
        files_data = get_equipment_files(equipment_id)
        files_list = []
        for file in files_data['data']:
            file_url = file.get('url')
            # TODO: Check if manual added PDF to files on an equipment shows up here or not (because labels are saved here, are PDFs and sum such as well?)
            if 'rentman-tempstorage' not in file_url:
                if(verbose):
                    print(f"   Getting file: {file_url}")
                filename = download_file(file_url, folder_path)
                if filename:  # Check if file was successfully downloaded
                    files_list.append({'filename': filename, 'local_path': os.path.join(folder_name, filename), 'original_url': file_url, 'data': file})

        # Update JSON with file data
        with open(data_file_path, 'w') as f:
            json.dump({'equipment_data': item, 'files': files_list}, f, indent=4)
        
        # Update progress
        if(not verbose):
            update_progress(index, len(equipment_items), len(files_list), equipment_name)
        else:
            print(f"   Created .JSON file: {data_file_path}")

        # Create markdown file with all data
        md_content = f"[Ça Tourne Requisit](https://www.catourne.ch)\n\n"
        md_content += f"# {item.get('name', 'Unknown')}"
        if(item.get('in_archive')):
            md_content += f" *(Archiviert)*"
        md_content += "\n\nKategorie: › "
        md_content += f"{item.get('folder_path', 'Unknown').replace('/', ' › ')}\n\n"
        md_content += "\n\n"
        md_content += "## Details\n"
        for key, value in item.items():
            if(key == "custom"):
                # Show "EXTRA INPUT FIELDS" in a special way
                md_content += f"- **Extra Input Fields ('custom')**:\n"
                for subKey, subValue in value.items():
                    md_content += f"  - *{extra_input_fields.get(subKey, subKey)}*: {subValue}\n"
            else:
                md_content += f"- **{key}**: {value}\n"
        md_content += f"\n## Files ({len(files_list)})\n"
        for file in files_list:
            if(file["data"]["type"].startswith("image/")):
                md_content += f"![File](<../{file['local_path']}>)\nLocal Image: [{file['filename']}](<../{file['local_path']}>) | <sub><sup>[*Original URL*]({file['original_url']})</sup></sub><br><br>\n\n\n"
            elif(file['filename'].endswith('.txt') or file['filename'].endswith('.rtf') or file['filename'].endswith('.TXT') or file['filename'].endswith('.RTF')):
                file_contents = load_file_content(os.path.join(folder_path, file['filename']))
                md_content += f"Local File: [{file['filename']}](<../{file['local_path']}>) - Content:\n\n> {file_contents}\n\n<sub><sup>[*Original URL*]({file['original_url']})</sup></sub><br><br>\n\n\n"
            else:
                md_content += f"Local File: [{file['filename']}](<../{file['local_path']}>) | <sub><sup>[*Original URL*]({file['original_url']})</sup></sub><br><br>\n\n\n"

        if(len(files_list) == 0):
            md_content += f"\n#### *No files for this document.*\n\n"
        
        
        md_content += f"\n---\n"
        current_datetime = datetime.datetime.now()
        formatted_date = current_datetime.strftime('%d.%m.%Y - %H:%M')
        md_content += f"<br><br><sub><sup>Export Date: {formatted_date}</sub></sup>\n"

        md_file_path = os.path.join(folder_path, 'data.md')
        with open(md_file_path, 'w') as f:
            f.write(md_content)

        if(verbose):
            print(f"   Created .MD file:   {md_file_path}")

        # Convert .md to .PDF
        pdf_path = os.path.join(folder_path, f"{folder_name}.pdf")
        convert_md_to_pdf(md_file_path, pdf_path, folder_path)

        if(verbose):
            print(f"   Created .PDF file:  {pdf_path}")

    # Finish progress
    sys.stdout.write('\n')
    sys.stdout.flush()
    print(f"\nData collection of {len(equipment_items)} equipment pieces complete 🥳")
