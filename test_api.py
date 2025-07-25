import requests

# Test signup
signup_data = {
    'username': 'apitestuser',
    'email': 'apitestuser@example.com',
    'password': 'apitestpass123'
}
signup_response = requests.post('http://localhost:8000/api/signup/', json=signup_data)
print('Signup status:', signup_response.status_code)
print('Signup response:', signup_response.json())

# Test login
login_data = {
    'username': 'apitestuser',
    'password': 'apitestpass123'
}
login_response = requests.post('http://localhost:8000/api/login/', json=login_data)
print('Login status:', login_response.status_code)
print('Login response:', login_response.json())
