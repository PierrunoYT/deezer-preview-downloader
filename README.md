# Deezer Downloader

A Python script to download tracks from Deezer using the ARL token with support for the 2024 authentication system.

## Features

- ✅ **2024 Authentication Support** - Works with Deezer's updated API and token system
- ✅ **Multiple Quality Levels** - Supports 320kbps, 256kbps, and 128kbps MP3 downloads
- ✅ **Blowfish Decryption** - Proper decryption for encrypted tracks
- ✅ **URL Parsing** - Supports both direct track IDs and Deezer URLs
- ✅ **Progress Tracking** - Real-time download progress display
- ✅ **Safe Filenames** - Automatic filename sanitization
- ✅ **Comprehensive Logging** - Detailed error handling and debugging
- ✅ **Fallback Support** - Falls back to preview downloads when full tracks unavailable

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Get and set your Deezer ARL token:

   **Quick setup with helper script:**
   ```bash
   python get_arl_token.py
   ```

   **Manual setup:**

   First, get your ARL token:
   1. Open your browser and go to https://www.deezer.com
   2. Login to your Deezer account (use VPN if Deezer is blocked in your country)
   3. Open Developer Tools (F12 or right-click → Inspect)
   4. Go to Application tab (Chrome) or Storage tab (Firefox)
   5. Expand "Cookies" and click on "https://www.deezer.com"
   6. Find the cookie named "arl" and copy its value (~192 characters)

   Then set it as an environment variable:
   ```bash
   # Windows (Command Prompt)
   set DEEZER_ARL_TOKEN=your_arl_token_here

   # Windows (PowerShell)
   $env:DEEZER_ARL_TOKEN="your_arl_token_here"

   # Linux/macOS
   export DEEZER_ARL_TOKEN=your_arl_token_here
   ```

   **Important Notes:**
   - ARL tokens expire periodically (usually every few months)
   - You need an active Deezer account (free or premium)
   - If you get "Invalid CSRF token" errors, get a fresh ARL token

## Finding Track IDs

To get the track ID from a Deezer URL:

1. Go to the song on Deezer website
2. Copy the URL (e.g., `https://www.deezer.com/track/123456789`)
3. The number at the end is your track ID (`123456789`)

**Important:** 
- Deezer track IDs are numeric (like `123456789`)
- This is NOT the same as Spotify IDs (which look like `30rKjcymCnl6hDo1PR1El`)
- Deezer is not available in all countries. Use a VPN if needed.

## Usage

```bash
python deezer.py <track_id_or_url> [-o output_directory] [-v]
```

### Examples

```bash
# Download using track ID
python deezer.py 123456789

# Download using full Deezer URL
python deezer.py "https://www.deezer.com/track/123456789"

# Download using short Deezer link
python deezer.py "https://link.deezer.com/s/30rKjcymCn"

# Download to specific directory
python deezer.py 123456789 -o ./downloads

# Enable verbose logging for debugging
python deezer.py 123456789 -v
```

## Troubleshooting

### Common Issues

1. **"Invalid CSRF token" or "VALID_TOKEN_REQUIRED"**
   - Your ARL token is expired or invalid
   - Solution: Get a fresh ARL token using `python get_arl_token.py`
   - Make sure you're logged into Deezer when getting the token

2. **"ARL token validation failed"**
   - Token format is incorrect (should be ~192 alphanumeric characters)
   - Solution: Double-check you copied the entire "arl" cookie value

3. **"Track is not available for streaming/download"**
   - Track may be geo-restricted or removed from Deezer
   - Solution: Try using a VPN to a different country
   - Verify the track exists and is playable on Deezer website

4. **"Could not generate download URL"**
   - Track may not be available in any quality level
   - Solution: Try a different track or check if your account has proper access

5. **Download fails or produces corrupted files**
   - Network issues or incomplete download
   - Solution: Check internet connection, try running with `-v` flag for detailed logging

6. **"Failed to get API token"**
   - Session establishment failed
   - Solution: Check if Deezer is accessible from your location, try with VPN

### Dependencies

- `requests` - For HTTP requests
- `pycryptodome` - For Blowfish decryption
