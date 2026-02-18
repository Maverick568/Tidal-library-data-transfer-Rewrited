import tidalapi
from tidalapi.exceptions import TidalAPIError
from tqdm import tqdm
import sys

# ─────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────
SHOW_ERRORS = True

# ─────────────────────────────────────────────
# PAGINATION
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
    with tqdm(total=total, desc=f'  Fetching list of {label}', unit='items') as pbar:
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
# MENU
# ─────────────────────────────────────────────
print("\n" + "="*40)
print("  TIDAL ACCOUNT CLEANER (DESTRUCTIVE)")
print("="*40)
print("What do you want to DELETE from your account?")
print("1 - Favorite Tracks (Songs)")
print("2 - Favorite Albums")
print("3 - Favorite Artists")
print("4 - Playlists (Deletes yours, unfollows others)")
print("5 - EVERYTHING ABOVE (Wipe account)")

choice = input("Enter number: ").strip()

delete_tracks = choice in ("1", "5")
delete_albums = choice in ("2", "5")
delete_artists = choice in ("3", "5")
delete_playlists = choice in ("4", "5")

if not any([delete_tracks, delete_albums, delete_artists, delete_playlists]):
    print("Invalid choice. Exiting.")
    sys.exit()

# ─────────────────────────────────────────────
# SAFETY CHECK
# ─────────────────────────────────────────────
print("\n" + "!"*50)
print("WARNING: THIS ACTION CANNOT BE UNDONE!")
print("You are about to PERMANENTLY remove items from your library.")
print("!"*50)
confirm = input("Type 'DELETE' to confirm: ").strip()

if confirm != "DELETE":
    print("Confirmation failed. Aborting.")
    sys.exit()

# ─────────────────────────────────────────────
# LOGIN
# ─────────────────────────────────────────────
session = tidalapi.Session()
print('\nLogin to the account you want to CLEAN:')
session.login_oauth_simple()
favorites = session.user.favorites
user_id = session.user.id

# ─────────────────────────────────────────────
# REMOVE FUNCTIONS
# ─────────────────────────────────────────────

def remove_items(items, remove_fn, label):
    if not items:
        return

    print(f"\nDeleting {len(items)} {label}...")
    success_count = 0
    
    for item in tqdm(items, desc=f"Removing {label}"):
        try:
            remove_fn(item.id)
            success_count += 1
        except Exception as e:
            if SHOW_ERRORS:
                tqdm.write(f"  [ERROR] Could not remove {item.name}: {e}")

    print(f"Removed {success_count}/{len(items)} {label}.")

def process_playlists(playlists):
    if not playlists:
        return

    print(f"\nProcessing {len(playlists)} playlists...")
    
    deleted_count = 0
    unfollowed_count = 0

    for pl in tqdm(playlists, desc="Deleting/Unfollowing Playlists"):
        try:
            # Check ownership
            is_owner = False
            if hasattr(pl, 'creator') and pl.creator:
                if str(pl.creator.id) == str(user_id):
                    is_owner = True
            
            if is_owner:
                # FIX 2: Use session.request.request(...) for double nested call
                # This accesses the raw API request method correctly
                session.request.request('DELETE', f'playlists/{pl.id}')
                deleted_count += 1
            else:
                # Unfollow (Remove from favorites)
                favorites.remove_playlist(pl.id)
                unfollowed_count += 1
                
        except Exception as e:
            if SHOW_ERRORS:
                tqdm.write(f"  [ERROR] Issue with playlist '{pl.name}': {e}")

    print(f"Summary: {deleted_count} deleted (yours), {unfollowed_count} unfollowed (others).")

# ─────────────────────────────────────────────
# MAIN EXECUTION
# ─────────────────────────────────────────────

# 1. Albums
if delete_albums:
    print("\n--- ALBUMS ---")
    albums = fetch_all(favorites.albums, favorites.get_albums_count, "albums")
    remove_items(albums, favorites.remove_album, "albums")

# 2. Artists
if delete_artists:
    print("\n--- ARTISTS ---")
    artists = fetch_all(favorites.artists, favorites.get_artists_count, "artists")
    remove_items(artists, favorites.remove_artist, "artists")

# 3. Tracks
if delete_tracks:
    print("\n--- TRACKS ---")
    tracks = fetch_all(favorites.tracks, favorites.get_tracks_count, "tracks")
    remove_items(tracks, favorites.remove_track, "tracks")

# 4. Playlists
if delete_playlists:
    print("\n--- PLAYLISTS ---")
    playlists = fetch_all(favorites.playlists, favorites.get_playlists_count, "playlists")
    process_playlists(playlists)

print("\n" + "="*40)
print("CLEANUP COMPLETED!")
print("="*40)
input("Press Enter to exit...")