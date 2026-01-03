"""
Setup Google OAuth 2.0 credentials for Bintacura
This script creates OAuth 2.0 credentials for web application
"""

import subprocess
import json

def setup_google_oauth():
    """Setup Google OAuth credentials using gcloud"""
    
    print("Setting up Google OAuth 2.0 credentials for Bintacura...")
    
    # The redirect URIs for the OAuth app
    redirect_uris = [
        "https://bintacura.org/patient/wearable-devices/oauth/callback/",
        "https://www.bintacura.org/patient/wearable-devices/oauth/callback/",
        "http://127.0.0.1:8080/patient/wearable-devices/oauth/callback/",
        "http://localhost:8080/patient/wearable-devices/oauth/callback/"
    ]
    
    print("\n" + "="*70)
    print("GOOGLE OAUTH 2.0 CREDENTIALS SETUP INSTRUCTIONS")
    print("="*70)
    print("\nTo create OAuth 2.0 credentials, please follow these steps:")
    print("\n1. Go to: https://console.cloud.google.com/apis/credentials?project=bintacura")
    print("\n2. Click '+ CREATE CREDENTIALS' -> 'OAuth client ID'")
    print("\n3. Select 'Web application' as the application type")
    print("\n4. Name: 'Bintacura Health Platform'")
    print("\n5. Add these Authorized redirect URIs:")
    for uri in redirect_uris:
        print(f"   - {uri}")
    print("\n6. Click 'CREATE'")
    print("\n7. Copy the Client ID and Client Secret")
    print("\n8. Update your .env file with:")
    print("   GOOGLE_FIT_CLIENT_ID=<your_client_id>")
    print("   GOOGLE_FIT_CLIENT_SECRET=<your_client_secret>")
    print("\n" + "="*70)
    
    # Enable required APIs
    print("\nEnabling required Google APIs...")
    apis = [
        "fitness.googleapis.com",
        "people.googleapis.com"
    ]
    
    for api in apis:
        print(f"Enabling {api}...")
        result = subprocess.run(
            ["gcloud", "services", "enable", api, "--project=bintacura"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print(f"✓ {api} enabled successfully")
        else:
            print(f"✗ Error enabling {api}: {result.stderr}")
    
    print("\n" + "="*70)
    print("Next Steps:")
    print("="*70)
    print("1. Create OAuth credentials using the console URL above")
    print("2. Configure the OAuth consent screen if not already done")
    print("3. Add the scopes: fitness.activity.read, fitness.heart_rate.read, etc.")
    print("4. Update your .env file with the credentials")
    print("="*70)

if __name__ == "__main__":
    setup_google_oauth()
