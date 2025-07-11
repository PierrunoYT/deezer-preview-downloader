#!/usr/bin/env python3
"""
Test script for Deezer downloader
"""

import os
import sys
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from deezer import (
    extract_track_id_from_url,
    sanitize_filename,
    get_api_token,
    get_track_details,
    generate_blowfish_key
)

def test_url_extraction():
    """Test URL extraction functionality"""
    print("Testing URL extraction...")
    
    # Test cases
    test_urls = [
        "https://www.deezer.com/track/123456789",
        "https://deezer.com/track/987654321",
        "https://www.deezer.com/en/track/555666777",
    ]
    
    for url in test_urls:
        track_id = extract_track_id_from_url(url)
        print(f"URL: {url} -> Track ID: {track_id}")
    
    print("✓ URL extraction test completed\n")

def test_filename_sanitization():
    """Test filename sanitization"""
    print("Testing filename sanitization...")
    
    test_names = [
        "Artist - Song Title",
        "Artist/Name - Song<Title>",
        "Artist: Song | Title?",
        "   Spaced   Artist   -   Song   ",
    ]
    
    for name in test_names:
        sanitized = sanitize_filename(name)
        print(f"'{name}' -> '{sanitized}'")
    
    print("✓ Filename sanitization test completed\n")

def test_blowfish_key_generation():
    """Test Blowfish key generation"""
    print("Testing Blowfish key generation...")
    
    track_id = "123456789"
    key = generate_blowfish_key(track_id)
    print(f"Track ID: {track_id}")
    print(f"Generated key length: {len(key)} bytes")
    print(f"Key (hex): {key.hex()}")
    
    print("✓ Blowfish key generation test completed\n")

def test_api_connection():
    """Test API connection with ARL token"""
    print("Testing API connection...")

    arl_token = os.getenv('DEEZER_ARL_TOKEN')
    if not arl_token:
        print("❌ DEEZER_ARL_TOKEN environment variable not set")
        return False

    print(f"ARL token length: {len(arl_token)} characters")

    # Test API token retrieval
    auth_result = get_api_token(arl_token)
    if auth_result:
        api_token, session = auth_result
        print(f"✓ Successfully got API token: {api_token[:20]}...")
        return True
    else:
        print("❌ Failed to get API token")
        return False

def test_track_details():
    """Test track details retrieval"""
    print("Testing track details retrieval...")

    arl_token = os.getenv('DEEZER_ARL_TOKEN')
    if not arl_token:
        print("❌ DEEZER_ARL_TOKEN environment variable not set")
        return False

    # Get API token and session first
    auth_result = get_api_token(arl_token)
    if not auth_result:
        print("❌ Could not get API token")
        return False

    api_token, session = auth_result

    # Test with a popular track ID (this might need to be updated)
    test_track_id = "3135556"  # Daft Punk - One More Time

    track_details = get_track_details(test_track_id, session, api_token)
    if track_details:
        print(f"✓ Got track details for ID {test_track_id}")
        print(f"  Title: {track_details.get('SNG_TITLE', 'Unknown')}")
        print(f"  Artist: {track_details.get('ART_NAME', 'Unknown')}")
        print(f"  MD5_ORIGIN: {track_details.get('MD5_ORIGIN', 'Missing')}")
        return True
    else:
        print(f"❌ Failed to get track details for ID {test_track_id}")
        return False

def main():
    """Run all tests"""
    print("=== Deezer Downloader Test Suite ===\n")
    
    # Run basic tests that don't require API access
    test_url_extraction()
    test_filename_sanitization()
    test_blowfish_key_generation()
    
    # Run API tests if token is available
    if test_api_connection():
        test_track_details()
    else:
        print("Skipping API-dependent tests due to missing or invalid ARL token\n")
    
    print("=== Test Suite Completed ===")
    print("\nTo test actual downloading, run:")
    print("python deezer.py <track_id> -v")

if __name__ == "__main__":
    main()
