#!/usr/bin/env python3
"""
Helper script to guide users through getting a fresh ARL token from Deezer
"""

import os
import re
import sys

def validate_arl_token(token):
    """Validate ARL token format"""
    if not token:
        return False, "Token is empty"
    
    token = token.strip()
    
    if len(token) < 100:
        return False, f"Token too short ({len(token)} chars, should be ~192)"
    
    if not re.match(r'^[a-zA-Z0-9]+$', token):
        return False, "Token contains invalid characters (should be alphanumeric only)"
    
    return True, f"Token format looks valid ({len(token)} characters)"

def main():
    print("=== Deezer ARL Token Helper ===\n")

    print("To get your ARL token:")
    print("1. Open your web browser and go to https://www.deezer.com")
    print("2. Log in to your Deezer account")
    print("3. Open Developer Tools (F12 or right-click -> Inspect)")
    print("4. Go to the 'Application' tab (Chrome) or 'Storage' tab (Firefox)")
    print("5. In the left sidebar, expand 'Cookies' and click on 'https://www.deezer.com'")
    print("6. Find the cookie named 'arl' and copy its value")
    print("7. The value should be a long string of letters and numbers (~192 characters)")
    print("\nNote: Make sure you're logged in and have an active Deezer account.\n")
    
    # Check current environment variable
    current_token = os.getenv('DEEZER_ARL_TOKEN')
    if current_token:
        is_valid, message = validate_arl_token(current_token)
        print(f"Current ARL token in environment: {message}")
        if not is_valid:
            print("❌ Current token appears invalid\n")
        else:
            print("✓ Current token format looks good\n")
    else:
        print("No DEEZER_ARL_TOKEN environment variable found\n")
    
    # Get new token from user
    while True:
        token = input("Paste your ARL token here (or 'quit' to exit): ").strip()
        
        if token.lower() in ['quit', 'exit', 'q']:
            print("Exiting...")
            sys.exit(0)
        
        if not token:
            print("Please enter a token or 'quit' to exit\n")
            continue
        
        is_valid, message = validate_arl_token(token)
        print(f"Validation result: {message}")
        
        if is_valid:
            print("✓ Token format looks valid!")
            
            # Show how to set environment variable
            print("\nTo set this as your environment variable:")
            print("\nWindows (Command Prompt):")
            print(f'set DEEZER_ARL_TOKEN={token}')
            print("\nWindows (PowerShell):")
            print(f'$env:DEEZER_ARL_TOKEN="{token}"')
            print("\nLinux/macOS:")
            print(f'export DEEZER_ARL_TOKEN="{token}"')
            
            print("\nOr create a .env file in your project directory with:")
            print(f'DEEZER_ARL_TOKEN={token}')
            
            # Test the token
            test = input("\nWould you like to test this token? (y/n): ").strip().lower()
            if test in ['y', 'yes']:
                print("Testing token...")
                os.environ['DEEZER_ARL_TOKEN'] = token
                
                try:
                    # Import and test
                    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
                    from deezer import get_api_token

                    auth_result = get_api_token(token)
                    if auth_result:
                        api_token, session = auth_result
                        print("✓ Token test successful! You can now use the downloader.")
                    else:
                        print("❌ Token test failed. The token might be expired or invalid.")
                        print("Please try getting a fresh token from your browser.")
                except ImportError:
                    print("Could not import deezer module for testing.")
                except Exception as e:
                    print(f"Error during token test: {e}")
            
            break
        else:
            print(f"❌ {message}")
            print("Please try again with a valid ARL token\n")

if __name__ == "__main__":
    main()
