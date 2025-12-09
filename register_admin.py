import requests

# The URL for the registration page
register_url = 'http://127.0.0.1:5000/register'

# The data for the new admin user
admin_data = {
    'username': 'admin',
    'email': 'admin@jengamart.com',
    'password': 'adminpassword',
    'confirm_password': 'adminpassword'
}

# Send the POST request to register the admin user
response = requests.post(register_url, data=admin_data)

# Check the response
if response.status_code == 200:
    print('Admin user registered successfully.')
else:
    print(f'Failed to register admin user. Status code: {response.status_code}')
    print(response.text)
