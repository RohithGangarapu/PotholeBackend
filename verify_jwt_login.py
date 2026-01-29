
import os
import django
from django.test import Client
from django.contrib.auth.hashers import make_password
import json

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from app.models import User

def verify_jwt_login():
    client = Client()
    email = "jwt_test@example.com"
    password = "securepassword123"
    username = "jwtuser"
    
    # Create test user
    print(f"Creating test user: {email}")
    user, created = User.objects.get_or_create(
        email=email,
        defaults={
            'username': username,
            'password': make_password(password),
            'phone': '9876543210'
        }
    )
    if not created:
        user.password = make_password(password)
        user.save()

    try:
        # Test 1: Successful login returns tokens
        print("\nTest 1: Successful login returns tokens")
        response = client.post('/api/v1/login/', 
                               data=json.dumps({"email": email, "password": password}),
                               content_type='application/json')
        print(f"Status Code: {response.status_code}")
        content = json.loads(response.content)
        # print(f"Response: {content}") 
        
        assert response.status_code == 200
        assert content['status'] == 'success'
        assert 'tokens' in content
        assert 'access' in content['tokens']
        assert 'refresh' in content['tokens']
        print("✅ Tokens received successfully")
        
        token = content['tokens']['access']
        
        # Test 2: Use token to access a protected resource (simulated)
        # Since currently views are open, we just verify the authentication class doesn't crash
        # We can manually invoke the authentication logic or just define a quick test view in memory if possible?
        # For now, let's just assume if generation works and settings are set, it's good. 
        # But we can check if the token decode works.
        
        from rest_framework_simplejwt.tokens import AccessToken
        access_token = AccessToken(token)
        print(f"✅ Token decoded successfully. User ID in token: {access_token['user_id']}")
        assert access_token['user_id'] == user.id

    finally:
        # Clean up
        print(f"\nCleaning up test user: {email}")
        user.delete()

if __name__ == "__main__":
    verify_jwt_login()
