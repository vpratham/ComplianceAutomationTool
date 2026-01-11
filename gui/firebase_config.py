# gui/firebase_config.py
"""
Shared Firebase configuration for SmartCompliance application.
Using Firebase REST API directly to avoid pyrebase compatibility issues.
"""
# Suppress warnings
import warnings
warnings.filterwarnings('ignore', category=DeprecationWarning)

import requests
import json
import time
from typing import Optional, Dict, Any

# Firebase Configuration
# Note: Make sure your Firebase Realtime Database is enabled in Firebase Console
# The databaseURL format is typically: https://[project-id]-default-rtdb.firebaseio.com/
# If you have a different database URL, update it below.
FIREBASE_CONFIG = {
    "apiKey": "AIzaSyBm82zxebOaSAVNZoC94oOQ8hzz58cGy8I",
    "authDomain": "smartcompliance-5dbb9.firebaseapp.com",
    "databaseURL": "https://smartcompliance-5dbb9-default-rtdb.firebaseio.com/",  # Realtime Database URL - verify in Firebase Console
    "projectId": "smartcompliance-5dbb9",
    "storageBucket": "smartcompliance-5dbb9.firebasestorage.app",
    "messagingSenderId": "1040761393077",
    "appId": "1:1040761393077:web:bd7d28e30a6d6ed62f93fc",
    "measurementId": "G-S1F4TKDQPJ"
}

# Extract database URL
DATABASE_URL = FIREBASE_CONFIG["databaseURL"].rstrip('/')

class FirebaseDatabase:
    """Simple Firebase Realtime Database client using REST API."""
    
    def __init__(self, database_url: str, api_key: str):
        self.database_url = database_url
        self.api_key = api_key
        self.base_url = f"{database_url}.json"
        
    def push(self, path: str, data: Dict[Any, Any]) -> Optional[str]:
        """
        Push data to Firebase Realtime Database.
        
        Args:
            path: Database path (e.g., 'queries')
            data: Data to push
            
        Returns:
            Key of the pushed data or None if failed
        """
        url = f"{self.database_url}/{path}.json"
        try:
            # Try without auth first (if security rules allow)
            response = requests.post(url, json=data, timeout=10)
            
            # If unauthorized, try with auth token (though API key alone won't work for Realtime DB)
            if response.status_code == 401:
                # For Realtime Database, we'd need an ID token, not API key
                # But let's try without auth if rules allow public write
                response = requests.post(url, json=data, timeout=10)
            
            response.raise_for_status()
            result = response.json()
            # Firebase returns the key name on POST
            if isinstance(result, dict) and 'name' in result:
                return result.get('name')
            # Sometimes Firebase returns just the key as a string
            elif isinstance(result, str):
                return result
            return None
        except requests.exceptions.RequestException as e:
            # Print detailed error for debugging
            error_detail = getattr(e.response, 'text', str(e)) if hasattr(e, 'response') else str(e)
            print(f"Firebase push error: {error_detail}")
            return None
    
    def get(self, path: str) -> Optional[Dict]:
        """Get data from Firebase Realtime Database."""
        url = f"{self.database_url}/{path}.json"
        try:
            response = requests.get(url, params={"auth": self.api_key})
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Firebase get error: {e}")
            return None

# Initialize Firebase Database using REST API
try:
    database = FirebaseDatabase(DATABASE_URL, FIREBASE_CONFIG["apiKey"])
    firebase = True  # Indicate Firebase is available
    auth = None  # Not using auth for now
except Exception as e:
    print(f"Warning: Firebase initialization failed: {e}")
    database = None
    firebase = None
    auth = None

