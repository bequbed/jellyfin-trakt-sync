# Jellyfin-to-Trakt Sync (Non-Admin)

Do you use Jellyfin but don't have administrator access to the server? Do you also use Trakt.tv to keep track of everything you watch? This script is for you!

This project provides a Python script that you can run on your own computer or server. It automatically syncs your personal watch history from Jellyfin directly to your Trakt.tv profile, without needing any special permissions on the Jellyfin server itself.

## How it Works

The script logs into your Jellyfin account, fetches your recently watched movies and episodes, and then securely logs into your Trakt.tv account to "scrobble" (add) that watch history. It runs periodically in the background, ensuring your Trakt profile stays up-to-date automatically.

## Key Features

* **No Admin Needed:** Works perfectly with a standard Jellyfin user account.
* **Automatic Syncing:** Set it up once and it runs in the background (using cron or Task Scheduler).
* **Secure Authentication:** Uses standard OAuth for Trakt.tv and your Jellyfin login. Handles token refreshing automatically.
* **Prevents Duplicates:** Keeps track of what's already synced to avoid adding the same item multiple times.
* **Configurable:** You can set how often it syncs and how far back it checks your history.

## Prerequisites

Before you start, make sure you have:

1.  **A Place to Run It:** A computer, Raspberry Pi, or server that is generally always on and can run Python scripts.
2.  **Python:** Python 3 installed on that machine.
3.  **Jellyfin Access:** Your Jellyfin server's web address (URL), your username, and your password.
4.  **Trakt.tv Account:** A free account on Trakt.tv.

## Setup Instructions

Follow these steps to get the sync script running:

**1. Get the Code:**

* Download the script files (`jellyfin_trakt_sync.py`, `requirements.txt`, `config.json.example`, `run_sync.sh`) into a dedicated directory on your machine.
* *Alternatively, if familiar with Git:* Clone the repository:
    ```bash
    git clone <repository_url>
    cd jellyfin-trakt-sync
    ```

**2. Set Up the Python Environment:**

* Open a terminal or command prompt in the project directory.
* **Create a virtual environment:** This keeps the script's dependencies separate.
    ```bash
    python3 -m venv venv
    ```
* **Activate the virtual environment:**
    * On Linux or macOS: `source venv/bin/activate`
    * On Windows: `.\venv\Scripts\activate`
    (You should see `(venv)` appear at the beginning of your command prompt line).
* **Install required packages:**
    ```bash
    pip install -r requirements.txt
    ```
    (This installs `jellyfin-apiclient-python` and `requests`).

**3. Register a Trakt Application:**

* You need to tell Trakt about your script so it can get permission to scrobble for you.
* Go to `https://trakt.tv/oauth/applications/new` in your web browser (log in if needed).
* Fill out the form:
    * **Name:** Give it a descriptive name, like `My Jellyfin Sync` or `Home Server Sync`.
    * **Redirect URI:** Enter exactly `urn:ietf:wg:oauth:2.0:oob`
    * **Permissions:** Check the box next to `/scrobble`. Leave others unchecked unless you know you need them.
* Click "Save App".
* **IMPORTANT:** You will now see a **Client ID** and a **Client Secret**. Copy these down securely – you'll need them in the next step. *Treat the Client Secret like a password!*

**4. Configure the Script:**

* Find the `config.json.example` file in the project directory.
* **Rename or copy** it to `config.json`.
* **Edit `config.json`** using a text editor and fill in your details:

    ```json
    {
        "jellyfin": {
            "server_url": "https://your-jellyfin-server.com",  // <-- Replace with your server's address. NO trailing slash / !
            "username": "your-jellyfin-username",         // <-- Replace with your Jellyfin username
            "password": "your-jellyfin-password",         // <-- Replace with your Jellyfin password
            "device_id": "jellyfin-sync-script-unique-name" // <-- Can leave as is, or make it unique
        },
        "trakt": {
            "client_id": "YOUR_TRAKT_CLIENT_ID_HERE",     // <-- Paste the Client ID from Step 3
            "client_secret": "YOUR_TRAKT_CLIENT_SECRET_HERE", // <-- Paste the Client Secret from Step 3
            "access_token": null,                       // <-- Leave as null
            "refresh_token": null,                      // <-- Leave as null
            "token_expires_at": 0                       // <-- Leave as 0
        },
        "sync": {
            "days_to_look_back": 7,                       // How many days of history to check each time (7 is usually fine)
            "last_sync": 0                              // Leave as 0, the script manages this
        }
    }
    ```
* Save the `config.json` file.

**5. First Run & Trakt Authentication:**

* Make sure your virtual environment is still active (`(venv)` should be visible in your terminal).
* Run the script manually for the first time:
    ```bash
    python3 jellyfin_trakt_sync.py
    ```
* The script will:
    * Attempt to connect to your Jellyfin server using the credentials you provided.
    * If successful, it will initiate the Trakt authentication. It will print a message like:
        `Please go to https://trakt.tv/activate and enter the code: XXXXXXXX`
* **Action Required:** Open the `https://trakt.tv/activate` URL in your browser. Log in to Trakt if prompted. Enter the exact code displayed in your terminal. Click "Continue" and then "Allow" or "Authorize" to grant the script permission to scrobble to your account.
* Once you authorize it, the script running in your terminal will detect this, securely save the necessary tokens to your `config.json` file, and perform the first sync.
* Check the script's output for "Sync complete" or any error messages.

**6. Automate the Sync (Recommended):**

You don't want to run the script manually all the time. Here's how to automate it:

* **Use the Wrapper Script:** The included `run_sync.sh` script simplifies running the sync within its environment. You might need to edit the `cd` command inside it if your project directory isn't `~/jellyfin-trakt-sync`.
* **Make it Executable (Linux/macOS):**
    ```bash
    chmod +x run_sync.sh
    ```
* **Schedule it:**
    * **On Linux/macOS (using cron):**
        * Edit your user's crontab: `crontab -e`
        * Add a line to run the script periodically. To run every 15 minutes:
            ```cron
            */15 * * * * /full/path/to/your/jellyfin-trakt-sync/run_sync.sh >> /full/path/to/your/jellyfin-trakt-sync/cron.log 2>&1
            ```
            *(Make sure to replace `/full/path/to/your/jellyfin-trakt-sync/` with the actual absolute path to the directory where you placed the script)*. This line also saves the script's output to `cron.log` in the same directory, which is helpful for checking if it's working.
        * Save and close the crontab editor.
    * **On Windows (using Task Scheduler):**
        * Open Task Scheduler.
        * Create a new Basic Task.
        * Set a trigger (e.g., Daily, repeat task every 15 minutes).
        * Set the action to "Start a program".
        * Program/script: Point it to your Python executable (e.g., `C:\path\to\your\project\venv\Scripts\python.exe`).
        * Add arguments: `jellyfin_trakt_sync.py`
        * Start in: Set this to the full path of your project directory (e.g., `C:\path\to\your\project\`).

## Troubleshooting Tips

* **Jellyfin URL Error:** Double-check the `server_url` in `config.json`. Make sure it's correct and **does not** have a slash (`/`) at the very end.
* **Authentication Failed:** Verify your Jellyfin username/password and Trakt Client ID/Secret in `config.json`.
* **Script Not Running (Automation):** Check the log file (`cron.log` or Task Scheduler history) for errors. Ensure the paths in your cron job or Task Scheduler task are correct. Make sure the virtual environment is correctly handled (the `run_sync.sh` script helps with this on Linux/macOS).
* **Trakt Auth Issues:** If Trakt authentication repeatedly fails, try deleting the token lines (`access_token`, `refresh_token`, `token_expires_at`) from `config.json` and running the script manually (`python3 jellyfin_trakt_sync.py`) to re-do the authorization flow (Step 5).

Enjoy having your Jellyfin watch history automatically synced to Trakt!
