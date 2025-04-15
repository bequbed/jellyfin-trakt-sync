
# Jellyfin-to-Trakt Sync

This project creates an automated system for users who don't have admin access to a Jellyfin server but want to sync their watched content to Trakt.tv. The solution is a Python script that runs on your own server, authenticates with both Jellyfin and Trakt, and syncs your watch history periodically.

## Setup Steps

### 1. Environment Setup


### 2. Script Creation

We created a Python script (`jellyfin_trakt_sync.py`) with the following components:

1. **Configuration Management**: Loads/saves user settings and maintains a cache of synced items
2. **Jellyfin Integration**: Authenticates with Jellyfin and retrieves watched items
3. **Trakt Integration**: Handles OAuth authentication and scrobbles content
4. **Syncing Logic**: Converts Jellyfin items to Trakt format and syncs them

### 3. Script Configuration

The script creates a `config.json` file on first run that you must edit to include:


### 4. Trakt API Registration

1. Create a Trakt application at https://trakt.tv/oauth/applications
2. Set the name to "Jellyfin Sync" (or your preferred name)
3. Set the redirect URI to `urn:ietf:wg:oauth:2.0:oob`
4. Enable permission for `/scrobble`
5. Save the Client ID and Client Secret for your config file

### 5. Authentication Process

When you run the script for the first time after configuration:

1. It authenticates with Jellyfin using your credentials
2. It initiates the Trakt device OAuth flow:
   - Displays a URL to visit and a code to enter
   - Waits for you to authorize the application
   - Stores the access and refresh tokens for future use

### 6. Troubleshooting Steps

We encountered and fixed several issues:

1. **User ID Resolution**: Changed from `client.auth.user_id` to `client.auth.config.data['auth.user_id']`
2. **API Compatibility**: Replaced `client.jellyfin.get_items()` with direct API requests
3. **Authentication Issues**: Ensured the Jellyfin URL format was correct (no trailing slash)
4. **Trakt Library Problems**: Created direct API calls instead of relying on the `trakt.py` library

### 7. Final Script Structure

The script follows this process flow:

1. Load configuration and cache
2. Authenticate with Jellyfin and Trakt
3. Retrieve recently played items from Jellyfin
4. Convert items to Trakt format
5. Check which items need to be synced (not in cache)
6. Scrobble items to Trakt
7. Update cache with successfully synced items
8. Log results

### 8. Automation Setup

To automate the script to run every 15 minutes:


## Key Features

1. **Non-Admin Compatible**: Works with regular Jellyfin user accounts
2. **Automatic Token Refresh**: Handles Trakt OAuth token refresh automatically
3. **Cache System**: Prevents duplicate syncing of content
4. **Detailed Logging**: Maintains logs for troubleshooting
5. **Direct API Calls**: Uses direct API calls for better compatibility

