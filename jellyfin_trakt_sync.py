import os
import json
import time
import logging
from datetime import datetime, timedelta
import requests

from jellyfin_apiclient_python import JellyfinClient

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("sync.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('jellyfin-trakt-sync')

CONFIG_FILE = 'config.json'
CACHE_FILE = 'sync_cache.json'

def load_config():
    """Load or create config file"""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    else:
        # Create default config
        default_config = {
            'jellyfin': {
                'server_url': 'http://your-jellyfin-server:8096',
                'username': '',
                'password': '',
                'device_id': 'sync-script-' + str(int(time.time()))
            },
            'trakt': {
                'client_id': '',
                'client_secret': '',
                'access_token': None,
                'refresh_token': None,
                'token_expires_at': 0
            },
            'sync': {
                'days_to_look_back': 7,
                'last_sync': 0
            }
        }
        
        with open(CONFIG_FILE, 'w') as f:
            json.dump(default_config, f, indent=4)
            
        logger.info(f"Created default config file at {CONFIG_FILE}. Please edit it.")
        return default_config

def save_config(config):
    """Save config to file"""
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)

def load_cache():
    """Load or create sync cache"""
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'r') as f:
            return json.load(f)
    else:
        default_cache = {
            'synced_items': {}
        }
        with open(CACHE_FILE, 'w') as f:
            json.dump(default_cache, f, indent=4)
        return default_cache

def save_cache(cache):
    """Save cache to file"""
    with open(CACHE_FILE, 'w') as f:
        json.dump(cache, f, indent=4)

def setup_jellyfin(config):
    """Setup and authenticate with Jellyfin"""
    try:
        client = JellyfinClient()
        client.config.app('JellyfinTraktSync', '1.0.0', 'Dell Server', config['jellyfin']['device_id'])
        client.config.data["auth.ssl"] = config['jellyfin']['server_url'].startswith('https')
        
        client.auth.connect_to_address(config['jellyfin']['server_url'])
        result = client.auth.login(
            config['jellyfin']['server_url'],
            config['jellyfin']['username'],
            config['jellyfin']['password']
        )
        
        if not result:
            logger.error("Failed to connect to Jellyfin server")
            return None
            
        logger.info(f"Connected to Jellyfin as {config['jellyfin']['username']}")
        return client
    except Exception as e:
        logger.error(f"Error connecting to Jellyfin: {str(e)}")
        return None

def trakt_auth(config):
    """Manual OAuth with Trakt API"""
    # Check if we already have a valid token
    now = int(time.time())
    if (config['trakt']['access_token'] and 
        config['trakt']['token_expires_at'] > now + 600):  # 10-minute buffer
        logger.info("Using existing Trakt token")
        return True
    
    # If we have a refresh token, try to refresh
    if (config['trakt']['refresh_token'] and 
        config['trakt']['access_token']):
        try:
            logger.info("Attempting to refresh Trakt token")
            # Refresh token endpoint
            url = 'https://api.trakt.tv/oauth/token'
            payload = {
                'refresh_token': config['trakt']['refresh_token'],
                'client_id': config['trakt']['client_id'],
                'client_secret': config['trakt']['client_secret'],
                'redirect_uri': 'urn:ietf:wg:oauth:2.0:oob',
                'grant_type': 'refresh_token'
            }
            
            response = requests.post(url, json=payload)
            if response.status_code == 200:
                token_data = response.json()
                config['trakt']['access_token'] = token_data['access_token']
                config['trakt']['refresh_token'] = token_data['refresh_token']
                config['trakt']['token_expires_at'] = now + token_data['expires_in']
                save_config(config)
                
                logger.info("Successfully refreshed Trakt token")
                return True
            else:
                logger.warning("Failed to refresh token, proceeding to full authentication")
        except Exception as e:
            logger.error(f"Error refreshing token: {str(e)}")
    
    # Full authentication flow
    try:
        logger.info("Starting new Trakt authentication")
        url = 'https://api.trakt.tv/oauth/device/code'
        payload = {
            'client_id': config['trakt']['client_id']
        }
        
        # Step 1: Get device code
        response = requests.post(url, json=payload)
        if response.status_code != 200:
            logger.error(f"Failed to get device code: {response.text}")
            return False
            
        device_data = response.json()
        
        device_code = device_data['device_code']
        user_code = device_data['user_code']
        verification_url = device_data['verification_url']
        expires_in = device_data['expires_in']
        interval = device_data['interval']
        
        print(f"\n==== Trakt Authentication ====")
        print(f"Please go to: {verification_url}")
        print(f"And enter the code: {user_code}")
        print("Waiting for authorization...")
        
        # Step 2: Poll for authorization
        url = 'https://api.trakt.tv/oauth/device/token'
        payload = {
            'code': device_code,
            'client_id': config['trakt']['client_id'],
            'client_secret': config['trakt']['client_secret']
        }
        
        start_time = time.time()
        while time.time() - start_time < expires_in:
            time.sleep(interval)
            
            response = requests.post(url, json=payload)
            if response.status_code == 200:
                token_data = response.json()
                config['trakt']['access_token'] = token_data['access_token']
                config['trakt']['refresh_token'] = token_data['refresh_token']
                config['trakt']['token_expires_at'] = now + token_data['expires_in']
                save_config(config)
                
                print("Successfully authenticated with Trakt!")
                logger.info("Successfully authenticated with Trakt")
                return True
            elif response.status_code == 400:
                # Still waiting for the user
                print(".", end="", flush=True)
            else:
                logger.error(f"Authentication failed: {response.text}")
                return False
                
        logger.error("Authentication timed out")
        return False
    except Exception as e:
        logger.error(f"Error during Trakt authentication: {str(e)}")
        return False

def setup_trakt(config):
    """Setup and authenticate with Trakt"""
    try:
        # Authenticate
        if not trakt_auth(config):
            return False
        
        # Test authentication with a simple API call
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {config["trakt"]["access_token"]}',
            'trakt-api-version': '2',
            'trakt-api-key': config['trakt']['client_id']
        }
        
        response = requests.get('https://api.trakt.tv/users/me', headers=headers)
        if response.status_code == 200:
            user_data = response.json()
            logger.info(f"Connected to Trakt as {user_data['username']}")
            return True
        else:
            logger.error(f"Failed to verify Trakt authentication: {response.text}")
            return False
    except Exception as e:
        logger.error(f"Error setting up Trakt: {str(e)}")
        return False

def get_jellyfin_recently_played(client, days_to_look_back=7):
    """Get recently played items from Jellyfin"""
    try:
        # Get user_id
        user_id = client.auth.config.data['auth.user_id']
        
        # Make a direct API call instead of using the client method
        headers = {
            'X-Emby-Token': client.auth.config.data['auth.token'],
        }
        
        params = {
            'userId': user_id,
            'SortBy': 'DatePlayed',
            'SortOrder': 'Descending',
            'IncludeItemTypes': 'Movie,Episode',
            'Recursive': 'true',
            'Fields': 'Path,Overview,ProviderIds,DateCreated,MediaSources,UserData',
            'IsPlayed': 'true',
            'Limit': '100'
        }
        
        url = f"{client.config.data['auth.server']}/Items"
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code != 200:
            logger.error(f"Failed to get items: {response.text}")
            return []
            
        data = response.json()
        
        watched_items = []
        if 'Items' in data:
            for item in data['Items']:
                # Only include items that have been played
                if item.get('UserData', {}).get('Played', False):
                    watched_items.append(item)
                    
        logger.info(f"Found {len(watched_items)} recently played items on Jellyfin")
        return watched_items
    except Exception as e:
        logger.error(f"Error getting recently played items: {str(e)}")
        return []

def prepare_item_for_trakt(item):
    """Convert Jellyfin item to Trakt format"""
    if item['Type'] == 'Movie':
        # Handle movie
        movie = {
            'title': item['Name'],
            'year': item.get('ProductionYear'),
            'ids': {}
        }
        
        # Add IDs if available
        provider_ids = item.get('ProviderIds', {})
        if provider_ids.get('Imdb'):
            movie['ids']['imdb'] = provider_ids['Imdb']
        if provider_ids.get('Tmdb'):
            movie['ids']['tmdb'] = str(provider_ids['Tmdb'])  # Ensure it's a string
            
        watched_at = item.get('UserData', {}).get('LastPlayedDate')
        
        return {
            'type': 'movie',
            'data': movie,
            'watched_at': watched_at,
            'jellyfin_id': item['Id']
        }
        
    elif item['Type'] == 'Episode':
        # Handle TV episode
        show = {
            'title': item.get('SeriesName'),
            'ids': {}
        }
        
        # Add series IDs if available
        if 'SeriesId' in item:
            # We might need to make another API call to get the series provider IDs
            # This is simplified for now
            pass
            
        episode = {
            'season': item.get('ParentIndexNumber'),
            'number': item.get('IndexNumber'),
            'title': item.get('Name'),
            'ids': {}
        }
        
        # Add episode IDs if available
        provider_ids = item.get('ProviderIds', {})
        if provider_ids.get('Imdb'):
            episode['ids']['imdb'] = provider_ids['Imdb']
        if provider_ids.get('Tmdb'):
            episode['ids']['tmdb'] = str(provider_ids['Tmdb'])
            
        watched_at = item.get('UserData', {}).get('LastPlayedDate')
        
        return {
            'type': 'episode',
            'data': {
                'show': show,
                'episode': episode
            },
            'watched_at': watched_at,
            'jellyfin_id': item['Id']
        }
        
    return None

def scrobble_to_trakt(item_data, config):
    """Scrobble an item to Trakt using direct API call"""
    try:
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {config["trakt"]["access_token"]}',
            'trakt-api-version': '2',
            'trakt-api-key': config['trakt']['client_id']
        }
        
        # Common payload structure
        payload = {
            'progress': 100,  # 100% watched
            'app_version': '1.0.0',
            'app_date': datetime.now().strftime('%Y-%m-%d')
        }
        
        if item_data['type'] == 'movie':
            payload['movie'] = item_data['data']
            url = 'https://api.trakt.tv/scrobble/stop'
            
            response = requests.post(url, json=payload, headers=headers)
            if response.status_code == 201:
                logger.info(f"Scrobbled movie: {item_data['data']['title']}")
                return response.json()
            else:
                logger.error(f"Failed to scrobble movie: {response.text}")
                return None
                
        elif item_data['type'] == 'episode':
            payload['show'] = item_data['data']['show']
            payload['episode'] = item_data['data']['episode']
            url = 'https://api.trakt.tv/scrobble/stop'
            
            response = requests.post(url, json=payload, headers=headers)
            if response.status_code == 201:
                show_title = item_data['data']['show']['title']
                season = item_data['data']['episode']['season']
                episode = item_data['data']['episode']['number']
                logger.info(f"Scrobbled episode: {show_title} S{season}E{episode}")
                return response.json()
            else:
                logger.error(f"Failed to scrobble episode: {response.text}")
                return None
                
    except Exception as e:
        logger.error(f"Error scrobbling to Trakt: {str(e)}")
        return None

def sync_items_to_trakt(jellyfin_items, cache, config):
    """Sync multiple items to Trakt"""
    synced_count = 0
    already_synced = 0
    errors = 0
    
    for item in jellyfin_items:
        jellyfin_id = item['Id']
        
        # Check if this item has already been synced
        if jellyfin_id in cache['synced_items']:
            already_synced += 1
            continue
            
        # Prepare item for Trakt
        trakt_item = prepare_item_for_trakt(item)
        if not trakt_item:
            logger.warning(f"Failed to prepare item for Trakt: {item['Name']}")
            continue
            
        # Scrobble to Trakt
        response = scrobble_to_trakt(trakt_item, config)
        
        if response:
            # Add to cache
            cache['synced_items'][jellyfin_id] = {
                'timestamp': int(time.time()),
                'name': item['Name'],
                'type': item['Type']
            }
            synced_count += 1
        else:
            errors += 1
            
        # Be nice to the API
        time.sleep(1)
        
    # Save updated cache
    save_cache(cache)
    
    return synced_count, already_synced, errors

def main():
    """Main function"""
    logger.info("Starting Jellyfin to Trakt sync")
    
    # Load config
    config = load_config()
    
    # Check if config has been filled out
    if (not config['jellyfin']['username'] or
        not config['jellyfin']['password'] or
        not config['jellyfin']['server_url'] or
        not config['trakt']['client_id'] or
        not config['trakt']['client_secret']):
        logger.error("Please fill out the config file before running the script")
        return
        
    # Load cache
    cache = load_cache()
    
    # Setup clients
    jellyfin_client = setup_jellyfin(config)
    if not jellyfin_client:
        return
        
    if not setup_trakt(config):
        return
        
    # Get recently played items from Jellyfin
    days_to_look_back = config['sync'].get('days_to_look_back', 7)
    jellyfin_items = get_jellyfin_recently_played(jellyfin_client, days_to_look_back)
    
    # Sync items to Trakt
    synced, already_synced, errors = sync_items_to_trakt(jellyfin_items, cache, config)
    
    # Update last sync time
    config['sync']['last_sync'] = int(time.time())
    save_config(config)
    
    logger.info(f"Sync completed: {synced} items synced, {already_synced} already synced, {errors} errors")

if __name__ == "__main__":
    main()
