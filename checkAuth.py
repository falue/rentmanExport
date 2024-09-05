import requests
import sys

# Constants
BASE_URL = 'https://api.rentman.net'
JWT_TOKEN = ''  # Placeholder for the JWT token

def load_jwt_token(file_path):
    try:
        with open(file_path, 'r') as file:
            jwt_token = file.read().strip()  # Read the token and strip any extra whitespace
        return jwt_token
    except FileNotFoundError:
        print("The file 'JWT_TOKEN' was not found - create it! Insert the token there.")
        return None
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

# Function to make a test API call
def test_api_call(jwt_token_local):
    url = f"{BASE_URL}/contacts"  # Adjust the endpoint if needed
    headers = {
        'Authorization': f"Bearer {jwt_token_local}"
    }
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            # print("API call successful!")
            return True
        else:
            print("API call failed.")
            print("Status code:", response.status_code)
            print("Response:", response.text)
            return False
    except requests.exceptions.RequestException as e:
        # print(f"Request failed: {e}")
        return False

# Main script
if __name__ == '__main__':
    JWT_TOKEN = load_jwt_token('JWT_TOKEN')

    if JWT_TOKEN:
        success = test_api_call(JWT_TOKEN)  # Perform a test API call with the JWT
        if success:
            sys.exit(0)  # Exit with code 0 if successful
        else:
            sys.exit(1)  # Exit with code 1 if failed
    else:
        print("JWT token is missing. Please include your JWT token.")
        sys.exit(1)  # Exit with code 1 if JWT token is missing
