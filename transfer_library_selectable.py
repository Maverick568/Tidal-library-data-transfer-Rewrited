import tidalapi
from tidalapi.exceptions import TidalAPIError
from tqdm import tqdm
import os
import json
import time

# ─────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────
FAILED_LOG_FILE = "failed_items.txt"
PLAYLIST_EXPORT_FILE = "playlists_export.json"
meta_cache = {}

# Initialize error log file
with open(FAILED_LOG_FILE, "w", encoding="utf-8") as f:
    f.write("Failed Transfer Report:\n=======================\n")

# ─────────────────────────────────────────────
# PAGINATION (Universal)
# ─────────────────────────────────────────────
def fetch_all(fetch_fn, count_fn, label, page_size=50):
    try:
        total = count_fn()
    except:
        total = 0
        
    print(f'  Found {total} {label}.')

    if total == 0:
        return []

    items = []
    with tqdm(total=total, desc=f'  Downloading {label}', unit='items') as pbar:
        offset = 0
        while offset < total:
            batch = fetch_fn(limit=page_size, offset=offset)
            if not batch:
                break
            items.extend(batch)
            offset += len(batch)
            pbar.update(len(batch))
    return items

# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────
def get_artist_name(item):
    if hasattr(item, 'artist') and item.artist:
        return item.artist.name
    return "Unknown Artist"

def get_album_name(item):
    if hasattr(item, 'album') and item.album:
        return item.album.name
    return "Unknown Album"

def log_error(info, error_msg):
    # Print to console
    tqdm.write(f"\n[ERROR] Failed: {info}")
    # Write to file
    with open(FAILED_LOG_FILE, "a", encoding="utf-8") as log:
        log.write(f"{info}\n   -> Reason: {error_msg}\n")

# ─────────────────────────────────────────────
# MENU
# ─────────────────────────────────────────────
print("\nWhat do you want to transfer?")
print("1 - Favorite Tracks")
print("2 - Albums")
print("3 - Artists")
print("4 - Playlists (Cloned with custom order)")
print("5 - Everything")

choice = input("Enter number: ").strip()

transfer_tracks = choice in ("1", "5")
transfer_albums = choice in ("2", "5")
transfer_artists = choice in ("3", "5")
transfer_playlists = choice in ("4", "5")

# ─────────────────────────────────────────────
# LOGIN SOURCE
# ─────────────────────────────────────────────
session1 = tidalapi.Session()
print('\nLogin to SOURCE account (Export from):')
session1.login_oauth_simple()
source = session1.user.favorites

# ─────────────────────────────────────────────
# EXPORT
# ─────────────────────────────────────────────
print('\n--- EXPORTING DATA ---')

# --- 1. ALBUMS ---
if transfer_albums:
    albums = fetch_all(source.albums, source.get_albums_count, "albums")
    albums.sort(key=lambda x: x.user_date_added or 0)
    with open("album_id_list.txt", "w") as f:
        for item in albums:
            f.write(f"{item.id}\n")
            meta_cache[str(item.id)] = f"Album: {item.name} | Artist: {get_artist_name(item)}"

# --- 2. ARTISTS ---
if transfer_artists:
    artists = fetch_all(source.artists, source.get_artists_count, "artists")
    artists.sort(key=lambda x: x.user_date_added or 0)
    with open("artist_id_list.txt", "w") as f:
        for item in artists:
            f.write(f"{item.id}\n")
            meta_cache[str(item.id)] = f"Artist: {item.name}"

# --- 3. TRACKS (FAVORITES) ---
if transfer_tracks:
    tracks = fetch_all(source.tracks, source.get_tracks_count, "favorite tracks")
    tracks.sort(key=lambda x: x.user_date_added or 0)
    with open("track_id_list.txt", "w") as f:
        for item in tracks:
            f.write(f"{item.id}\n")
            meta_cache[str(item.id)] = f"Track: {item.name} | Artist: {get_artist_name(item)} | Album: {get_album_name(item)}"

# --- 4. PLAYLISTS (FULL EXPORT) ---
if transfer_playlists:
    print("\n  Fetching playlists...")
    playlists = fetch_all(source.playlists, source.get_playlists_count, "playlists")
    
    playlists_data = []
    
    print("  Analyzing playlist content (this might take a while)...")
    for pl in tqdm(playlists, desc="Scanning playlists"):
        try:
            # FIX: Fetch tracks in batches of 100 instead of 5000 at once
            pl_items = []
            offset = 0
            while True:
                # Request 100 items at a time
                batch = pl.items(limit=100, offset=offset)
                if not batch:
                    break
                pl_items.extend(batch)
                offset += len(batch)
            
            track_ids_list = []
            for item in pl_items:
                # Ensure item is a track/video with an ID
                if hasattr(item, 'id'):
                    track_ids_list.append(str(item.id))
                    # Cache metadata for playlist tracks too
                    if str(item.id) not in meta_cache:
                        # Safe extraction of artist name
                        artist_name = "Unknown Artist"
                        if hasattr(item, 'artist') and item.artist:
                            artist_name = item.artist.name
                        
                        meta_cache[str(item.id)] = f"Track in playlist '{pl.name}': {item.name} | {artist_name}"

            playlists_data.append({
                "name": pl.name,
                "description": pl.description,
                "tracks": track_ids_list
            })
        except Exception as e:
            print(f"  [WARN] Failed to fetch content for playlist {pl.name}: {e}")

    # Save structure to JSON
    with open(PLAYLIST_EXPORT_FILE, "w", encoding="utf-8") as f:
        json.dump(playlists_data, f, ensure_ascii=False, indent=4)

print("\nData exported successfully.")


# ─────────────────────────────────────────────
# LOGIN DESTINATION
# ─────────────────────────────────────────────
session2 = tidalapi.Session()
print('\nLogin to DESTINATION account (Import to):')
session2.login_oauth_simple()
dest = session2.user.favorites


# ─────────────────────────────────────────────
# IMPORT FUNCTION (Simple Items)
# ─────────────────────────────────────────────
def add_simple_items(filename, add_fn, label):
    if not os.path.exists(filename):
        return

    with open(filename) as f:
        ids = [line.strip() for line in f if line.strip()]

    print(f"\nAdding {label}...")
    for id in tqdm(ids):
        try:
            add_fn(id)
        except Exception as e:
            info = meta_cache.get(str(id), f"ID: {id} ({label})")
            log_error(info, e)


# ─────────────────────────────────────────────
# IMPORT FUNCTION (Playlists - Cloned)
# ─────────────────────────────────────────────
def import_playlists_cloned():
    if not os.path.exists(PLAYLIST_EXPORT_FILE):
        return

    with open(PLAYLIST_EXPORT_FILE, "r", encoding="utf-8") as f:
        playlists_data = json.load(f)

    print(f"\nCloning {len(playlists_data)} playlists...")

    for pl_data in tqdm(playlists_data, desc="Creating playlists"):
        pl_name = pl_data['name']
        pl_desc = pl_data.get('description', '')
        track_ids = pl_data.get('tracks', [])

        try:
            # 1. Create new playlist on destination account
            new_pl = session2.user.create_playlist(pl_name, pl_desc)
            
            if not track_ids:
                continue

            # 2. Add tracks to the new playlist
            try:
                # Try adding in batch (faster)
                new_pl.add(track_ids)
            except Exception as e:
                # If batch fails, fallback to one-by-one to catch specific errors
                tqdm.write(f"  Batch add failed for '{pl_name}', trying one by one...")
                for tid in track_ids:
                    try:
                        new_pl.add([tid])
                    except Exception as inner_e:
                        info = meta_cache.get(tid, f"Track ID: {tid} in playlist '{pl_name}'")
                        log_error(info, inner_e)

        except Exception as e:
            tqdm.write(f"  [CRITICAL] Failed to create playlist '{pl_name}'")
            log_error(f"Entire Playlist: {pl_name}", e)

# ─────────────────────────────────────────────
# RUN IMPORT
# ─────────────────────────────────────────────

if transfer_albums:
    add_simple_items("album_id_list.txt", dest.add_album, "albums")

if transfer_artists:
    add_simple_items("artist_id_list.txt", dest.add_artist, "artists")

if transfer_playlists:
    import_playlists_cloned()

if transfer_tracks:
    add_simple_items("track_id_list.txt", dest.add_track, "favorite tracks")

print("\nProcess Completed!")
print(f"Check '{FAILED_LOG_FILE}' for any failed items.")
input("Press Enter to exit...")