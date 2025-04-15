#!/bin/bash
cd ~/jellyfin-trakt-sync
source venv/bin/activate
python3 jellyfin_trakt_sync.py
deactivate
