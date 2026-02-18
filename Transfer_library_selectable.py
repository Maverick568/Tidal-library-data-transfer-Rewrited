import tidalapi
from tidalapi.exceptions import TidalAPIError
from tqdm import tqdm
import os
import json
import sys

# ─────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────
FAILED_LOG_FILE = "failed_items.txt"
PLAYLIST_EXPORT_FILE = "playlists_export.json"
SEPARATOR = " :: "  # Separator oddzielający ID od nazwy w plikach txt

# Słownik przechowujący nazwy dla ID (Globalny Cache)
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
    tqdm.write(f"\n[ERROR] Failed: {info}")
    with open(FAILED_LOG_FILE, "a", encoding="utf-8") as log:
        log.write(f"{info}\n   -> Reason: {error_msg}\n")

# ─────────────────────────────────────────────
# MENU - MODE SELECTION
# ─────────────────────────────────────────────
print("\nSelect Mode:")
print("1 - Full Transfer (Login Source -> Export -> Login destination account -> Import)")
print("2 - Export Only (Login Source -> Save to files -> Exit)")
print("3 - Import Only (Skip Source login, use local files)")

mode_choice = input("Enter mode (1/2/3): ").strip()

enable_export = mode_choice in ("1", "2")
enable_import = mode_choice in ("1", "3")

# ─────────────────────────────────────────────
# MENU - CONTENT SELECTION
# ─────────────────────────────────────────────
print("\nWhat content should be processed?")
print("1 - Favorite Tracks")
print("2 - Albums")
print("3 - Artists")
print("4 - Playlists")
print("5 - Everything")

choice = input("Enter number: ").strip()

transfer_tracks = choice in ("1", "5")
transfer_albums = choice in ("2", "5")
transfer_artists = choice in ("3", "5")
transfer_playlists = choice in ("4", "5")

# ─────────────────────────────────────────────
# LOGIN SOURCE & EXPORT (Conditional)
# ─────────────────────────────────────────────
if enable_export:
    session1 = tidalapi.Session()
    print('\n=== Login to SOURCE account (Export from) ===')
    session1.login_oauth_simple()
    source = session1.user.favorites

    print('\n--- EXPORTING DATA (Saving IDs and Names) ---')

    # --- 1. ALBUMS ---
    if transfer_albums:
        albums = fetch_all(source.albums, source.get_albums_count, "albums")
        albums.sort(key=lambda x: x.user_date_added or 0)
        with open("album_id_list.txt", "w", encoding="utf-8") as f:
            for item in albums:
                meta = f"Album: {item.name} | Artist: {get_artist_name(item)}"
                # Zapisujemy w formacie: ID :: Metadata
                f.write(f"{item.id}{SEPARATOR}{meta}\n")
                meta_cache[str(item.id)] = meta

    # --- 2. ARTISTS ---
    if transfer_artists:
        artists = fetch_all(source.artists, source.get_artists_count, "artists")
        artists.sort(key=lambda x: x.user_date_added or 0)
        with open("artist_id_list.txt", "w", encoding="utf-8") as f:
            for item in artists:
                meta = f"Artist: {item.name}"
                f.write(f"{item.id}{SEPARATOR}{meta}\n")
                meta_cache[str(item.id)] = meta

    # --- 3. TRACKS (FAVORITES) ---
    if transfer_tracks:
        tracks = fetch_all(source.tracks, source.get_tracks_count, "favorite tracks")
        tracks.sort(key=lambda x: x.user_date_added or 0)
        with open("track_id_list.txt", "w", encoding="utf-8") as f:
            for item in tracks:
                meta = f"Track: {item.name} | Artist: {get_artist_name(item)}"
                f.write(f"{item.id}{SEPARATOR}{meta}\n")
                meta_cache[str(item.id)] = meta

    # --- 4. PLAYLISTS (FULL EXPORT) ---
    if transfer_playlists:
        print("\n  Fetching playlists...")
        playlists = fetch_all(source.playlists, source.get_playlists_count, "playlists")
        
        playlists_data = []
        
        print("  Analyzing playlist content...")
        for pl in tqdm(playlists, desc="Scanning playlists"):
            try:
                pl_items = []
                offset = 0
                while True:
                    batch = pl.items(limit=100, offset=offset)
                    if not batch: break
                    pl_items.extend(batch)
                    offset += len(batch)
                
                # Zbieramy utwory jako obiekty {id, meta}
                track_objects = []
                for item in pl_items:
                    if hasattr(item, 'id'):
                        artist_name = "Unknown"
                        if hasattr(item, 'artist') and item.artist:
                            artist_name = item.artist.name
                        
                        meta_info = f"{item.name} - {artist_name}"
                        track_objects.append({
                            "id": str(item.id),
                            "meta": meta_info
                        })
                        
                        # Cache'ujemy też lokalnie
                        meta_cache[str(item.id)] = f"Track in PL '{pl.name}': {meta_info}"

                playlists_data.append({
                    "name": pl.name,
                    "description": pl.description,
                    "tracks": track_objects # Zapisujemy pełne obiekty
                })
            except Exception as e:
                print(f"  [WARN] Failed to fetch content for playlist {pl.name}: {e}")

        with open(PLAYLIST_EXPORT_FILE, "w", encoding="utf-8") as f:
            json.dump(playlists_data, f, ensure_ascii=False, indent=4)

    print("\nData exported successfully with Metadata.")

# Check if we should stop here (Export Only mode)
if not enable_import:
    print("\n--- EXPORT ONLY MODE FINISHED ---")
    print("Files saved locally with titles/artists. Exiting.")
    input("Press Enter to exit...")
    sys.exit()

# If we are in Import Only mode, check files
if enable_import and not enable_export:
    print("\n--- SKIPPING EXPORT (Loading from local files) ---")
    files_to_check = []
    if transfer_albums: files_to_check.append("album_id_list.txt")
    if transfer_artists: files_to_check.append("artist_id_list.txt")
    if transfer_tracks: files_to_check.append("track_id_list.txt")
    if transfer_playlists: files_to_check.append(PLAYLIST_EXPORT_FILE)
    
    missing = [f for f in files_to_check if not os.path.exists(f)]
    if missing:
        print(f"[WARNING] The following files are missing: {missing}")
        input("Press Enter to continue anyway...")


# ─────────────────────────────────────────────
# LOGIN DESTINATION
# ─────────────────────────────────────────────
session2 = tidalapi.Session()
print('\n=== Login to DESTINATION account (Import to) ===')
session2.login_oauth_simple()
dest = session2.user.favorites


# ─────────────────────────────────────────────
# IMPORT FUNCTION (Simple Items with Metadata Parsing)
# ─────────────────────────────────────────────
def add_simple_items(filename, add_fn, label):
    if not os.path.exists(filename):
        print(f"File {filename} not found. Skipping {label}.")
        return

    # Wczytujemy linie
    with open(filename, "r", encoding="utf-8") as f:
        lines = f.readlines()

    ids_to_process = []
    
    # Parsujemy plik: oddzielamy ID od Metadanych
    for line in lines:
        line = line.strip()
        if not line: continue
        
        # Sprawdzamy czy linia ma separator " :: "
        if SEPARATOR in line:
            parts = line.split(SEPARATOR, 1)
            item_id = parts[0].strip()
            meta_info = parts[1].strip()
            
            # Zapisujemy metadane do cache, żeby log_error mógł ich użyć
            meta_cache[item_id] = meta_info
            ids_to_process.append(item_id)
        else:
            # Stary format (tylko ID) - kompatybilność wsteczna
            item_id = line.strip()
            ids_to_process.append(item_id)

    print(f"\nAdding {label}...")
    for item_id in tqdm(ids_to_process):
        try:
            add_fn(item_id)
        except Exception as e:
            # Pobieramy nazwę z cache (którą przed chwilą wczytaliśmy z pliku)
            info = meta_cache.get(str(item_id), f"ID: {item_id} (No metadata in file)")
            log_error(info, e)


# ─────────────────────────────────────────────
# IMPORT FUNCTION (Playlists with Metadata Parsing)
# ─────────────────────────────────────────────
def import_playlists_cloned():
    if not os.path.exists(PLAYLIST_EXPORT_FILE):
        print(f"File {PLAYLIST_EXPORT_FILE} not found. Skipping playlists.")
        return

    with open(PLAYLIST_EXPORT_FILE, "r", encoding="utf-8") as f:
        playlists_data = json.load(f)

    print(f"\nCloning {len(playlists_data)} playlists...")

    for pl_data in tqdm(playlists_data, desc="Creating playlists"):
        pl_name = pl_data['name']
        pl_desc = pl_data.get('description', '')
        raw_tracks = pl_data.get('tracks', []) # To jest teraz lista słowników lub stringów

        try:
            new_pl = session2.user.create_playlist(pl_name, pl_desc)
            
            if not raw_tracks:
                continue
            
            # Przygotowanie listy ID i Cache'a
            track_ids_only = []
            
            for t in raw_tracks:
                if isinstance(t, dict):
                    # Nowy format JSON: {"id": "...", "meta": "..."}
                    tid = t['id']
                    meta = t['meta']
                    meta_cache[tid] = f"Track: {meta} (in PL '{pl_name}')"
                    track_ids_only.append(tid)
                else:
                    # Stary format JSON: "12345" (string)
                    track_ids_only.append(t)

            # Próba dodania
            try:
                new_pl.add(track_ids_only)
            except Exception as e:
                tqdm.write(f"  Batch add failed for '{pl_name}', trying one by one...")
                for tid in track_ids_only:
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