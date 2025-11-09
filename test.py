#!/usr/bin/env python3
"""Test configuration"""

import os
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

print("="*60)
print("CONFIGURATION TEST")
print("="*60)

# Test Gemini
gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
print(f"\n1. GEMINI_API_KEY")
print(f"   Loaded: {'Yes' if gemini_key else 'No'}")
print(f"   Length: {len(gemini_key)} characters")
print(f"   Preview: {gemini_key[:10]}...")

if gemini_key:
    try:
        genai.configure(api_key=gemini_key)
        print("   ✓ API configured")
        
        print("\n   Available models:")
        for model in genai.list_models():
            if 'generateContent' in model.supported_generation_methods:
                print(f"     - {model.name}")
        
        # Test generation
        print("\n   Testing generation...")
        test_model = genai.GenerativeModel('gemini-1.5-flash')
        response = test_model.generate_content("Say hello")
        print(f"   ✓ Test successful: {response.text[:50]}")
        
    except Exception as e:
        print(f"   ✗ Error: {e}")
else:
    print("   ✗ Not set in .env file")

# Test Twilio
print(f"\n2. TWILIO CONFIG")
twilio_sid = os.getenv("TWILIO_ACCOUNT_SID", "").strip()
twilio_token = os.getenv("TWILIO_AUTH_TOKEN", "").strip()
twilio_phone = os.getenv("TWILIO_PHONE_NUMBER", "").strip()

print(f"   Account SID: {'Set' if twilio_sid else 'Not set'}")
print(f"   Auth Token: {'Set' if twilio_token else 'Not set'}")
print(f"   Phone Number: {twilio_phone if twilio_phone else 'Not set'}")

print("\n" + "="*60)
