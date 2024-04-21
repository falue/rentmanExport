import requests

# Constants
BASE_URL = 'https://api.rentman.net'
JWT_TOKEN = ''  # Create a file called "JWT_TOKEN" (without file extension), put the JWT token there, it will be read by this script and inserted.

def load_jwt_token(file_path):
    try:
        with open(file_path, 'r') as file:
            JWT_TOKEN = file.read().strip()  # Read the token and strip any extra whitespace
        return JWT_TOKEN
    except FileNotFoundError:
        print("The file 'JWT_TOKEN' was not found - create it! Insert the token there.")
        return None
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

# Function to make a test API call
def test_api_call(jwt_token_local):
    url = f"{BASE_URL}/contacts"  # Adjust if needed for a simple test
    headers = {
        'Authorization': f"Bearer {jwt_token_local}"
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        print("API call successful, yeah!")
        # print(response.json())  # Print out the response to check data
    else:
        print("API call failed.")
        print("Status code:", response.status_code)
        print("Response:", response.text)

# Main script
if __name__ == '__main__':
    JWT_TOKEN = load_jwt_token('JWT_TOKEN')

    if JWT_TOKEN:
        test_api_call(JWT_TOKEN)  # Perform a test API call with the JWT
    else:
        print("JWT token is missing. Please include your JWT token.")

