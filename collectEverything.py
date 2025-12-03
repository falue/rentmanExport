import requests
import argparse
import json
import time
import sys
import os
import contextlib
import urllib.parse  # For handling URL to filename conversion
from urllib.parse import quote
import subprocess
import qrcode
import qrcode.image.svg
import pypandoc
import datetime
import shutil
from weasyprint import HTML


# Constants for the API endpoints
BASE_URL = 'https://api.rentman.net'
JWT_TOKEN = ''  # Create a file called "JWT_TOKEN" (without file extension), put the JWT token there, it will be read by this script and inserted.

# Only export first n of your equipment collection.
# Set to 0 if you want it all.
# Note that after 300 equipments some rule imposed by the rentman API will kick in. Needs work for that I guess.
start_index = 0  # 0 for starting at first object
num_obj_to_export = 4

# Set up argument parsing
parser = argparse.ArgumentParser(description='Collect data and export files.')
parser.add_argument('--start', type=int, help='Start index', default=num_obj_to_export)  # Default start index is 0
parser.add_argument('--num', type=int, help='Number of objects to export', default=start_index)  # Default number of objects to export is 5
parser.add_argument('--id', type=str, help='Comma-separated list of specific equipment IDs to export', default="")  
parser.add_argument('--verbose', action='store_true', help='Print all the details of the export')
parser.add_argument('--overwrite', action='store_true', help='Overwrite existing files')

# Parse the arguments
args = parser.parse_args()

# Assign variables from arguments
start_index = args.start
num_obj_to_export = args.num
specific_obj_export = [int(i) for i in args.id.split(',')] if args.id else []
overwrite = args.overwrite  # Re-Download, encode etc if file data.json exists
verbose = args.verbose

num_obj_exported = 0

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
    """Create a safe filename from a NAME by replacing spaces, slashes, and other special characters with underscores."""
    # Extract the file name from the URL
    filename = os.path.basename(urllib.parse.urlparse(url).path)
    # Replace spaces and slashes with underscores
    filename = filename.replace(' ', '_').replace('/', '_').replace('\\', '_')
    # Remove any characters that are not alphanumeric, underscore, hyphen, dot, or special characters like äöü
    safe_filename = "".join(c if c.isalnum() or c in ('_', '-', '.', 'ä', 'ö', 'ü') else '_' for c in filename).rstrip()
    return safe_filename
    
def safe_filename_OLD(url):
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

def make_path_url_compatible(path):
    # Split the path into components, encode each component, and join them back with '/'
    return '/'.join(quote(part) for part in path.split('/'))

def revert_to_original_filename(safed_filename):
    """Decode a URL-safe filename back to its original form."""
    return urllib.parse.unquote(safed_filename)

# Function to get all equipment data with pagination
def get_all_equipment():
    equipment_data = []
    limit = 100  # Maximum number of records per request
    offset = 0   # Start at the first record
    
    headers = {
        'Authorization': f"Bearer {JWT_TOKEN}"
    }
    
    while True:
        # Define the request URL with limit and offset
        print(f"  {int(offset/limit+1)}. API call to '{BASE_URL}/equipment?limit={limit}&offset={offset}'")
        url = f"{BASE_URL}/equipment?limit={limit}&offset={offset}"
        response = requests.get(url, headers=headers)
        data = response.json()

        # Check for errors in response
        if response.status_code != 200:
            print(f"Error: {response.status_code}: {data.get('errorMessage', 'Unknown error')}")
            break
        
        # Add the retrieved data to the list
        equipment_data.extend(data.get('data', []))

        # Check if there are more records to fetch
        if len(data.get('data', [])) < limit:
            break  # No more records to fetch, exit the loop

        # Increase the offset for the next request
        offset += limit

    return equipment_data

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

def generate_qr_code(qr_path, number):
    """
    Generates a QR code SVG image for the provided number.

    Args:
    qr_path (str): The file path where the QR code SVG will be saved.
    number (str): The number to encode in the QR code.

    Returns:
    None. Saves the QR code image as an SVG file.
    """
    # Set the factory to create an SVG image
    svg_factory = qrcode.image.svg.SvgPathImage

    # Create a QRCode object with SVG support
    qr = qrcode.QRCode(
        version=1,  # Controls the size of the QR Code
        error_correction=qrcode.constants.ERROR_CORRECT_H,  # High error correction level
        box_size=10,
        border=4,
        image_factory=svg_factory
    )

    # Add data to the QR Code
    qr.add_data(number)
    qr.make(fit=True)

    # Create an SVG image from the QR Code instance
    img = qr.make_image(fill_color="black", back_color="white")

    # Save the SVG image to the specified path
    img.save(qr_path)
    #print(f"QR code generated and saved at '{qr_path}'.")

def convert_html_to_pdf(html_path, pdf_path_sheet):
    try:
        # Make weasyprint silent (subpress all warnings)
        with open(os.devnull, 'w') as f, contextlib.redirect_stdout(f), contextlib.redirect_stderr(f):
            # weasyprint
            # Convert HTML to PDF using WeasyPrint
            HTML(html_path).write_pdf(pdf_path_sheet)
    except Exception as e:
        print(f"      An error occurred: {e}")


def compress_pdf(input_path, quality="screen"):
    """
    Compress PDF via Ghostscript.
    quality: one of 'screen', 'ebook', 'printer', 'prepress', 'default'
    """
    output_path = input_path + ".tmp.pdf"
    command = [
        "gs",
        "-sDEVICE=pdfwrite",
        "-dCompatibilityLevel=1.4",
        f"-dPDFSETTINGS=/{quality}",
        "-dNOPAUSE",
        "-dQUIET",
        "-dBATCH",
        f"-sOutputFile={output_path}",
        input_path,
    ]

    try:
        subprocess.run(command, check=True)
        os.remove(input_path)
        os.rename(output_path, input_path)
    except subprocess.CalledProcessError as e:
        print(f"An error occurred while compressing the PDF (gs): {e}")
        if os.path.exists(output_path):
            os.remove(output_path)
   

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
    progress_message = f"\r{current}/{total} {bar} {percent_complete:.1f}% - Gathering {files_download} {'file' if files_download == 1 else 'files'} and data of '{filename}'"

    # Write the progress message to standard output and clear the rest of the line
    sys.stdout.write(progress_message + "\033[K")
    sys.stdout.flush()

# Main script
if __name__ == '__main__':
    JWT_TOKEN = load_file_content('JWT_TOKEN')

    if(num_obj_to_export > 0):
        print(f"Limit export of {num_obj_to_export} equipment. Change in the code to any other integer or to 0 if you want to export everything.\n")
    elif(specific_obj_export):
        print(f"Fetch {len(specific_obj_export)} object(s) with code(s) {specific_obj_export}\n")
    else:
        print(f"Reading database, export everything.\n")

    root_folder = 'equipmentDump'
    os.makedirs(root_folder, exist_ok=True)  # Create root directory

    categories = get_categories()  # Retrieve all folders (aka categories)
    equipment_data = get_all_equipment()
    print(f"Found {len(equipment_data)} articles in DB.")
    print(f"-------------------------------")

    # equipment_items = equipment_data['data']
    if(num_obj_to_export > 0):
        # Limit to first n equipment items for testing
        #equipment_items = equipment_data['data'][:num_obj_to_export]
        equipment_items = equipment_data[start_index:start_index + num_obj_to_export]
    else:
        equipment_items = equipment_data

    last_request_time = time.time()  # Initialize the last request time

    print(f"Collecting equipment data and creating files…")

    for index, item in enumerate(equipment_items, start=1):
        equipment_name = safe_filename(item.get('name', 'Unknown'))
        equipment_id = item['id']

        # if(specific_obj_export > 0 and int(item['code']) != specific_obj_export):
        if specific_obj_export and int(item['code']) not in specific_obj_export:
            # Skip if it's not in the list
            # print(f"{specific_obj_export} is not {item['code']}")
            continue  # Skip to the next iteration
        
        num_obj_exported += 1

        if(verbose):
            #print(f"\nCollecting {index}/{len(equipment_items)}: '{equipment_id} - {equipment_name}'")
            if(num_obj_to_export>0):
                tot_export = start_index+num_obj_to_export
            else:
                tot_export = len(equipment_items)
            print(f"\nCollecting {start_index+index}/{tot_export}: '{equipment_id} - {equipment_name}'")

        category_path = item.get('folder', None)  # eg.  "folder": "/folders/55"
        # Add human readable key/value to item - ATTENTION: This is *not* according to specs of rentman
        # in equipment:
        #   "folder": "/folders/55"
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

        #folder_name = f"{item['code']}_{item['qrcodes']}_{equipment_name}"
        ###folder_name = os.path.join(make_path_url_compatible(item["folder_path"]), f"{item['code']}_{item['qrcodes']}_{make_path_url_compatible(equipment_name)}")
        eq_name = f"{item['code']}_{item['qrcodes']}_{equipment_name}"
        folder_name = os.path.join(item["folder_path"], eq_name)
        #'/'.join(quote(folder_name) for folder_name in folder_name.split('/'))
        #  TODO: make parts of item["folder_path"] url-friendly
        # folder_name = "".join(c for c in folder_name if c.isalnum() or c in (' ', '.', '_', '-')).rstrip()

        folder_path = os.path.join(root_folder, folder_name)
        if(item.get('in_archive')):
            folder_path = os.path.join(root_folder, "_archived", folder_name)
        os.makedirs(folder_path, exist_ok=True)

        if(not overwrite and os.path.isfile(os.path.join(folder_path, "data.json"))):
            if(verbose):
                print(f"   Data already fetched - skipped")
            update_progress(index, len(equipment_items), 0, equipment_name)
            continue  # Skip to the next iteration

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
                    files_list.append({'filename': filename, 'local_path': filename, 'original_url': file_url, 'data': file})

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
        category_path_list = f"{item.get('folder_path', 'Unknown').replace('/', ' › ')}\n\n"
        md_content += category_path_list
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
        image_list = []
        for file in files_list:
            if(file["data"]["type"].startswith("image/")):
                image_list.append(file['local_path'])
                md_content += f"![File](<./{file['local_path']}>)\nLocal Image: [{file['filename']}](<./{file['local_path']}>) | <sub><sup>[*Original URL*]({file['original_url']})</sup></sub><br><br>\n\n\n"
            elif(file['filename'].endswith('.txt') or file['filename'].endswith('.rtf') or file['filename'].endswith('.TXT') or file['filename'].endswith('.RTF')):
                file_contents = load_file_content(os.path.join(folder_path, file['filename']))
                md_content += f"Local File: [{file['filename']}](<./{file['local_path']}>) - Content:\n\n> {file_contents}\n\n<sub><sup>[*Original URL*]({file['original_url']})</sup></sub><br><br>\n\n\n"
            else:
                md_content += f"Local File: [{file['filename']}](<./{file['local_path']}>) | <sub><sup>[*Original URL*]({file['original_url']})</sup></sub><br><br>\n\n\n"

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
        pdf_path = os.path.join(folder_path, f"{eq_name}.pdf")
        convert_md_to_pdf(md_file_path, pdf_path, folder_path)
        # compress_pdf(pdf_path, 125, 5)

        if(verbose):
            print(f"   Created .PDF file:  {pdf_path}")

        # Create QRCODE svg from euqipment serial number
        serial_numbers = [num.strip() for num in item['qrcodes_of_serial_numbers'].split(",") if num.strip()]
        qr_codes_html = ""
        for number in serial_numbers:
            qr_path = os.path.join(folder_path, f"{eq_name}-{number}-qr.svg")
            qr_codes_html += f'<div class="qr"><img src="{eq_name}-{number}-qr.svg" alt=""> {number}</div>\n        '
            generate_qr_code(qr_path, number)
            if(verbose):
                print(f"   Created QR code:  {number}")

        # Make equipment sheet html
        html_path = os.path.join(folder_path, f"{eq_name}-sheet.html")
        # Get base file from equipment-sheet.html
        # Read the HTML template into a variable
        with open('equipment-sheet.html', 'r') as file:
            html_content = file.read()

        # Replace the placeholders in the HTML content
        """
            %%name%% => item['displayname']
            %%img_1%% => if(len(image_list) > 0) image_list[0]
            %%img_2%% => if(len(image_list) > 1) image_list[1]
            %%amount%% => len(serial_numbers)
            %%code%% => item['code']
            %%length%% => item['length']
            %%width%% => item['width']
            %%height%% => item['height']
            %%qr_codes%% => qr_codes_html
        """
        html_content = html_content.replace('%%name%%', item['displayname'])
        # Choose image that is set as poster image by rentman user
        if(item['image'] and len(image_list) > 0 and len(item['image']) > 0):
            poster = int(os.path.basename(item['image']))
            for img in files_list:
                if poster == img["data"]["id"]:
                    html_content = html_content.replace('%%img%%', img["local_path"])
        html_content = html_content.replace('%%categories%%', category_path_list)
        html_content = html_content.replace('%%amount%%', str(len(serial_numbers)))
        html_content = html_content.replace('%%code%%', item['code'])
        html_content = html_content.replace('%%length%%', str(item['length']))
        html_content = html_content.replace('%%width%%', str(item['width']))
        html_content = html_content.replace('%%height%%', str(item['height']))
        html_content = html_content.replace('%%qr_codes%%', qr_codes_html)
        # Fill new file
        with open(html_path, 'w') as file:
            file.write(html_content)
        if(verbose):
            print(f"   Created .HTML equipment sheet file:  {html_path}")
        
        # Make equipment sheet pdf from html
        pdf_path_sheet = os.path.join(folder_path, f"{eq_name}-sheet.pdf")
        convert_html_to_pdf(html_path, pdf_path_sheet)
        if(verbose):
            print(f"   Created .PDF from equipment sheet .html file:  {pdf_path_sheet}")
            
        # Reduce file size of PDF
        compress_pdf(pdf_path_sheet, "screen")
        if(verbose):
            print(f"   - Resized .PDF")

        # Copy PDF to one folder for easy access if not in archive
        pdf_path_collected = os.path.join("equipmentSheets", f"{eq_name}-sheet.pdf")
        try:
            # Dont copy sheet if article is in archive;
            # ignore sheets without any images OR qr codes
            if(not item.get('in_archive') and (len(image_list) > 0 or len(serial_numbers) > 0)):
                shutil.copyfile(pdf_path_sheet, pdf_path_collected)
                if(verbose):
                    print(f"   - Copied .PDF to {pdf_path_collected}")
        except Exception as e:
            print(f"   - An error occurred: {e} - Maybe folder 'equipmentSheets' in root is missing?")


    # Finish progress
    sys.stdout.write('\n')
    sys.stdout.flush()
    if(specific_obj_export):
        if(num_obj_exported):
            print(f"Fetched {num_obj_exported} object(s) with code(s) {specific_obj_export} 🥳")
        else:
            print(f"Object(s) with code(s) {specific_obj_export} does not exist.")
    else:
        print(f"\nData collection of {len(equipment_items)} equipment pieces complete 🥳")
