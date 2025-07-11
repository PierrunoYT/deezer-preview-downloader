#!/usr/bin/env python3
"""
Deezer Downloader - Download tracks from Deezer using ARL token
Supports the 2024 token-based authentication system
"""

import requests
import os
import argparse
import re
import logging
import hashlib
from pathlib import Path
from Crypto.Cipher import Blowfish

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constants
DEEZER_BASE_URL = 'https://www.deezer.com'
DEEZER_API_URL = f'{DEEZER_BASE_URL}/ajax/gw-light.php'
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

# Get ARL token from environment variable
ARL_TOKEN = os.getenv('DEEZER_ARL_TOKEN')

if not ARL_TOKEN:
    logger.error("DEEZER_ARL_TOKEN environment variable is required")
    exit(1)

def validate_arl_token(arl_token):
    """Validate ARL token format"""
    if not arl_token:
        return False, "ARL token is empty"

    # ARL tokens are typically 192 characters long and contain alphanumeric characters
    if len(arl_token) < 100:
        return False, "ARL token appears too short (should be ~192 characters)"

    if not re.match(r'^[a-zA-Z0-9]+$', arl_token):
        return False, "ARL token contains invalid characters (should be alphanumeric only)"

    return True, "ARL token format appears valid"

def sanitize_filename(filename):
    """Sanitize filename for safe file system operations"""
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    filename = re.sub(r'\s+', ' ', filename).strip()
    return filename

def extract_track_id_from_url(url):
    """Extract track ID from various Deezer URL formats"""
    # Handle short links
    if 'link.deezer.com' in url:
        try:
            headers = {'User-Agent': USER_AGENT}
            response = requests.get(url, allow_redirects=True, headers=headers, timeout=10)
            final_url = response.url
            logger.info(f'Redirected to: {final_url}')

            # If still on link.deezer.com, try manual redirect
            if 'link.deezer.com' in final_url:
                response = requests.get(url, allow_redirects=False, headers=headers, timeout=10)
                if 'Location' in response.headers:
                    final_url = response.headers['Location']
                    logger.info(f'Found redirect location: {final_url}')
                else:
                    logger.debug(f'Page content: {response.text[:500]}')
                    return None

            url = final_url
        except requests.exceptions.RequestException as e:
            logger.error(f'Failed to resolve short link: {e}')
            return None

    # Extract numeric track ID from URL
    match = re.search(r'/track/(\d+)', url)
    if match:
        return match.group(1)

    logger.error(f'Could not extract track ID from URL: {url}')
    return None

def get_api_token(arl_token):
    """Get API token from Deezer using updated method"""
    session = requests.Session()

    headers = {
        'User-Agent': USER_AGENT,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }

    session.cookies.set('arl', arl_token, domain='.deezer.com')

    try:
        # Get main page to establish session and extract initial token
        main_response = session.get(DEEZER_BASE_URL, headers=headers, timeout=30)
        main_response.raise_for_status()

        # Extract API token from HTML
        token_match = re.search(r'"api_token":"([^"]+)"', main_response.text)
        initial_token = token_match.group(1) if token_match else ''

        if initial_token:
            logger.debug(f'Found initial API token: {initial_token[:20]}...')
        else:
            logger.debug('No initial API token found in page')

        # Get user data with the extracted token
        api_params = {
            'method': 'deezer.getUserData',
            'input': '3',
            'api_version': '1.0',
            'api_token': initial_token
        }

        api_response = session.post(DEEZER_API_URL, params=api_params, headers=headers, timeout=30)
        api_response.raise_for_status()
        result = api_response.json()

        logger.debug(f'API token response: {result}')

        if result.get('error'):
            error_msg = result.get('error', {})
            logger.error(f'Failed to get API token: {error_msg}')

            if 'VALID_TOKEN_REQUIRED' in str(error_msg) or 'Invalid CSRF token' in str(error_msg):
                logger.error('ARL token appears to be invalid or expired.')
                logger.error('Please get a fresh ARL token from your browser')
            return None

        user_data = result.get('results')
        if not user_data:
            logger.error('No user data returned - ARL token might be invalid')
            return None

        api_token = user_data.get('checkForm')
        if not api_token:
            logger.error('No API token in response - ARL token might be invalid')
            return None

        user_info = user_data.get('USER', {})
        username = user_info.get('BLOG_NAME') or user_info.get('USERNAME') or 'Unknown'
        logger.info(f'Successfully authenticated as user: {username}')

        return api_token, session

    except requests.exceptions.RequestException as e:
        logger.error(f'Failed to get API token: {e}')
        return None

def get_track_details(track_id, session, api_token):
    """Get track details from Deezer API using existing session"""
    headers = {
        'User-Agent': USER_AGENT,
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.5',
        'Content-Type': 'application/json',
        'Connection': 'keep-alive'
    }

    params = {
        'method': 'deezer.pageTrack',
        'input': '3',
        'api_version': '1.0',
        'api_token': api_token
    }

    data = {'sng_id': track_id}

    try:
        response = session.post(DEEZER_API_URL, params=params, json=data, headers=headers, timeout=30)
        response.raise_for_status()
        result = response.json()

        logger.debug(f'Track details response: {result}')

        if result.get('error'):
            error_msg = result.get('error', {})
            logger.error(f'API Error: {error_msg}')

            if 'VALID_TOKEN_REQUIRED' in str(error_msg):
                logger.error('API token expired. This usually means the ARL token is invalid.')

            return None

        track_data = result.get('results', {}).get('DATA')
        if not track_data:
            logger.error('No track data returned')
            return None

        return track_data

    except requests.exceptions.RequestException as e:
        logger.error(f'Failed to get track details: {e}')
        return None

def generate_blowfish_key(track_id):
    """Generate Blowfish key for track decryption"""
    secret = 'g4el58wc0zvf9na1'
    m = hashlib.md5()
    m.update(bytes([ord(x) for x in track_id]))
    id_md5 = m.hexdigest()

    return bytes((ord(id_md5[i]) ^ ord(id_md5[i + 16]) ^ ord(secret[i])) for i in range(16))

def get_track_download_token(track_details, session, api_token):
    """Get download token from Deezer API for the new 2024 format"""
    if not track_details:
        return None

    sng_id = str(track_details.get('SNG_ID', ''))
    if not sng_id:
        return None

    try:
        media_params = {
            'method': 'song.getListData',
            'input': '3',
            'api_version': '1.0',
            'api_token': api_token
        }

        media_data = {'sng_ids': [sng_id]}

        headers = {
            'User-Agent': USER_AGENT,
            'Accept': 'application/json, text/plain, */*',
            'Content-Type': 'application/json',
        }

        response = session.post(DEEZER_API_URL, params=media_params, json=media_data, headers=headers, timeout=30)
        response.raise_for_status()
        result = response.json()

        logger.debug(f'Media API response: {result}')

        if result.get('error'):
            logger.debug(f'Media API error: {result["error"]}')
            return None

        # Extract media information
        results = result.get('results', {})
        data = results.get('data', [])

        if data and len(data) > 0:
            track_data = data[0]
            media_list = track_data.get('MEDIA', [])

            # Look for download URLs in media list
            for media in media_list:
                if media.get('TYPE') == 'full':
                    return media.get('HREF')

        return None

    except Exception as e:
        logger.debug(f'Failed to get download token: {e}')
        return None

def get_track_token_url(track_details, session, api_token):
    """Get track download URL using the new 2024 token-based format"""
    if not track_details:
        return None

    # First try to get the download URL from the API
    api_download_url = get_track_download_token(track_details, session, api_token)
    if api_download_url:
        logger.debug(f'Got download URL from API: {api_download_url[:80]}...')
        return [api_download_url]

    # Extract track token from track details (fallback method)
    track_token = track_details.get('TRACK_TOKEN')
    if not track_token:
        logger.debug('No TRACK_TOKEN found in track details')
        return None

    # Extract required fields
    md5_origin = track_details.get('MD5_ORIGIN')
    sng_id = str(track_details.get('SNG_ID', ''))

    if not md5_origin or not sng_id:
        logger.error('Missing MD5_ORIGIN or SNG_ID in track details')
        return None

    # Try to construct URL using track token
    # This follows the new 2024 format: https://e-cdns-proxy-X.dzcdn.net/mobile/1/HASH?TOKEN

    # The server number is typically derived from the first character of MD5_ORIGIN
    server_num = md5_origin[0]

    # Try different hash generation methods
    possible_urls = []

    # Method 1: Use MD5_ORIGIN as hash
    url1 = f"https://e-cdns-proxy-{server_num}.dzcdn.net/mobile/1/{md5_origin}?{track_token}"
    possible_urls.append(url1)

    # Method 2: Generate hash from song ID and token
    m = hashlib.md5()
    m.update(f"{sng_id}{track_token}".encode('utf-8'))
    url_hash = m.hexdigest()
    url2 = f"https://e-cdns-proxy-{server_num}.dzcdn.net/mobile/1/{url_hash}?{track_token}"
    possible_urls.append(url2)

    # Method 3: Use track token as hash
    url3 = f"https://e-cdns-proxy-{server_num}.dzcdn.net/mobile/1/{track_token[:32]}?{track_token}"
    possible_urls.append(url3)

    logger.debug(f'Generated {len(possible_urls)} token-based download URLs')
    return possible_urls

def get_track_download_url_legacy(track_details, quality='MP3_128'):
    """Get track download URL using legacy format (fallback)"""
    if not track_details:
        return None

    # Extract required fields
    md5_origin = track_details.get('MD5_ORIGIN')
    sng_id = str(track_details.get('SNG_ID', ''))
    media_version = str(track_details.get('MEDIA_VERSION', '1'))

    if not md5_origin or not sng_id:
        logger.error('Missing MD5_ORIGIN or SNG_ID in track details')
        return None

    # Try different Deezer URL generation secrets and CDN formats
    SECRETS = [
        'jo6aey6haid2Teih',  # Original secret
        'g4el58wc0zvf9na1',  # Alternative secret
        '',  # No secret
    ]

    # Format: quality¤sng_id¤media_version¤md5_origin
    url_part = f"{quality}¤{sng_id}¤{media_version}¤{md5_origin}"

    all_urls = []

    for secret in SECRETS:
        # Generate MD5 hash with secret
        m = hashlib.md5()
        m.update((url_part + secret).encode('utf-8'))
        url_hash = m.hexdigest()

        # Try different CDN formats for each secret
        cdn_formats = [
            f"https://e-cdns-proxy-{md5_origin[0]}.dzcdn.net/mobile/1/{url_hash}",
            f"https://e-cdn-proxy-{md5_origin[0]}.dzcdn.net/mobile/1/{url_hash}",
            f"https://cdns-proxy-{md5_origin[0]}.dzcdn.net/mobile/1/{url_hash}",
            f"https://cdn-proxy-{md5_origin[0]}.dzcdn.net/mobile/1/{url_hash}",
            f"https://e-cdns-proxy-{md5_origin[0]}.deezer.com/mobile/1/{url_hash}",
        ]

        all_urls.extend(cdn_formats)

    logger.debug(f'Generated {len(all_urls)} legacy download URL variants to try')
    return all_urls

def decrypt_track_chunk(chunk, blowfish_key):
    """Decrypt a chunk of track data using Blowfish"""
    if len(chunk) < 2048:
        return chunk

    # Only decrypt every third 2048-byte chunk
    decrypted_chunk = bytearray()

    for i in range(0, len(chunk), 2048):
        chunk_part = chunk[i:i+2048]

        if len(chunk_part) == 2048 and (i // 2048) % 3 == 0:
            # Decrypt this chunk using Blowfish ECB
            try:
                cipher = Blowfish.new(blowfish_key, Blowfish.MODE_ECB)
                decrypted_part = cipher.decrypt(chunk_part)
                decrypted_chunk.extend(decrypted_part)
            except Exception as e:
                logger.debug(f'Decryption failed for chunk at {i}: {e}')
                decrypted_chunk.extend(chunk_part)
        else:
            decrypted_chunk.extend(chunk_part)

    return bytes(decrypted_chunk)

def download_track(track_id, token, output_dir='.'):
    """Download track from Deezer"""
    logger.info(f'Downloading track ID: {track_id}')

    # Get API token and session
    auth_result = get_api_token(token)
    if not auth_result:
        logger.error('Failed to get API token')
        return False

    api_token, session = auth_result

    # Get track details
    track_details = get_track_details(track_id, session, api_token)
    if not track_details:
        logger.error('Track details not available')
        return False

    track_title = track_details.get('SNG_TITLE', 'Unknown Title')
    artist_name = track_details.get('ART_NAME', 'Unknown Artist')

    logger.info(f'Track: {artist_name} - {track_title}')

    # Debug: Show available file sizes
    filesizes = {k: v for k, v in track_details.items() if k.startswith('FILESIZE_')}
    logger.debug(f'Available file sizes: {filesizes}')

    # Check if track is available for download
    rights = track_details.get('RIGHTS', {})
    if not rights.get('STREAM_ADS_AVAILABLE', True):
        logger.error('Track is not available for streaming/download')
        return False

    # Try new 2024 token-based URL format first
    download_url = None

    logger.info('Trying new 2024 token-based URL format...')
    token_urls = get_track_token_url(track_details, session, api_token)
    if token_urls:
        for url in token_urls:
            try:
                test_response = requests.head(url, timeout=10)
                if test_response.status_code == 200:
                    download_url = url
                    logger.info(f'Using token-based URL: {url[:80]}...')
                    break
                else:
                    logger.debug(f'Token URL not available (HTTP {test_response.status_code}): {url[:80]}...')
            except requests.exceptions.RequestException as e:
                logger.debug(f'Token URL not accessible ({str(e)[:50]}...): {url[:80]}...')
                continue

    # If token-based URLs don't work, try legacy format
    if not download_url:
        logger.info('Token-based URLs failed, trying legacy format...')
        quality_levels = ['MP3_320', 'MP3_256', 'MP3_128']

        for quality in quality_levels:
            url_candidates = get_track_download_url_legacy(track_details, quality)
            if url_candidates:
                for url in url_candidates:
                    try:
                        test_response = requests.head(url, timeout=10)
                        if test_response.status_code == 200:
                            download_url = url
                            logger.info(f'Using legacy quality: {quality} with URL: {url[:50]}...')
                            break
                        else:
                            logger.debug(f'Legacy URL not available (HTTP {test_response.status_code}): {url[:50]}...')
                    except requests.exceptions.RequestException as e:
                        logger.debug(f'Legacy URL not accessible ({str(e)[:50]}...): {url[:50]}...')
                        continue

                if download_url:
                    break

    # Check if we're using a preview URL (which doesn't need decryption)
    is_preview_url = False

    if not download_url:
        # Try fallback: use preview URL if available
        media_list = track_details.get('MEDIA', [])
        preview_url = None
        for media in media_list:
            if media.get('TYPE') == 'preview':
                preview_url = media.get('HREF')
                break

        if preview_url:
            logger.warning('Using preview URL as fallback (30-second preview only)')
            download_url = preview_url
            is_preview_url = True
        else:
            logger.error('Could not generate any download URL')
            return False

    # Generate decryption key (only needed for encrypted tracks, not previews)
    blowfish_key = generate_blowfish_key(track_id) if not is_preview_url else None

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive'
        }

        response = requests.get(download_url, stream=True, timeout=30, headers=headers)
        response.raise_for_status()

        # Create safe filename
        filename = sanitize_filename(f'{artist_name} - {track_title}.mp3')
        filepath = Path(output_dir) / filename

        # Ensure output directory exists
        filepath.parent.mkdir(parents=True, exist_ok=True)

        # Download and decrypt with progress
        total_size = int(response.headers.get('content-length', 0))
        downloaded = 0

        with open(filepath, 'wb') as file:
            if is_preview_url:
                # Preview URLs are plain MP3 files - no decryption needed
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        file.write(chunk)
                        downloaded += len(chunk)

                        if total_size > 0:
                            percent = (downloaded / total_size) * 100
                            print(f'\rDownloading: {percent:.1f}%', end='', flush=True)
            else:
                # Full tracks need Blowfish decryption
                buffer = bytearray()

                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        buffer.extend(chunk)
                        downloaded += len(chunk)

                        # Process complete 2048-byte blocks
                        while len(buffer) >= 2048:
                            block = bytes(buffer[:2048])
                            buffer = buffer[2048:]

                            # Decrypt if needed
                            decrypted_block = decrypt_track_chunk(block, blowfish_key)
                            file.write(decrypted_block)

                        if total_size > 0:
                            percent = (downloaded / total_size) * 100
                            print(f'\rDownloading: {percent:.1f}%', end='', flush=True)

                # Write remaining buffer
                if buffer:
                    decrypted_remaining = decrypt_track_chunk(bytes(buffer), blowfish_key)
                    file.write(decrypted_remaining)

        print()  # New line after progress
        logger.info(f'Downloaded: {filename}')
        return True

    except requests.exceptions.RequestException as e:
        logger.error(f'Failed to download track: {e}')
        return False
    except Exception as e:
        logger.error(f'Error during download/decryption: {e}')
        return False

def main():
    """Main function with command line argument parsing"""
    parser = argparse.ArgumentParser(description='Download tracks from Deezer')
    parser.add_argument('track_id', help='Deezer track ID or URL to download')
    parser.add_argument('-o', '--output', default='.', help='Output directory (default: current directory)')
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose logging')

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Validate ARL token
    is_valid, message = validate_arl_token(ARL_TOKEN)
    if not is_valid:
        logger.error(f'ARL token validation failed: {message}')
        logger.error('Please check your DEEZER_ARL_TOKEN environment variable')
        exit(1)

    logger.debug(f'ARL token validation: {message}')

    # Process track ID/URL
    track_id = args.track_id.strip()
    if not track_id:
        logger.error('Track ID cannot be empty')
        exit(1)

    # Extract track ID from URL if needed
    if 'deezer.com' in track_id:
        extracted_id = extract_track_id_from_url(track_id)
        if not extracted_id:
            logger.error('Could not extract track ID from URL')
            exit(1)
        track_id = extracted_id
        logger.info(f'Extracted track ID: {track_id}')

    # Validate track ID is numeric
    if not track_id.isdigit():
        logger.error('Track ID must be numeric')
        exit(1)

    # Download the track
    success = download_track(track_id, ARL_TOKEN, args.output)

    if success:
        logger.info('Download completed successfully')
    else:
        logger.error('Download failed')
        exit(1)

if __name__ == '__main__':
    main()
