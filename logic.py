import tidalapi
from tidalapi.exceptions import TidalAPIError
import os
import json
import time
import threading

# Custom exception for user cancellation
class OperationCancelled(Exception):
    pass

class TidalManager:
    def __init__(self, base_path=".", log_callback=None, progress_callback=None):
        self.base_path = base_path
        self.log_callback = log_callback
        self.progress_callback = progress_callback

        self.session_source = tidalapi.Session()
        self.session_dest = tidalapi.Session()

        self.meta_cache = {}
        self.cancel_flag = False

        # File paths
        self.failed_log_file = os.path.join(base_path, "failed_items.txt")
        self.playlist_export_file = os.path.join(base_path, "playlists_export.json")
        self.album_id_list = os.path.join(base_path, "album_id_list.txt")
        self.artist_id_list = os.path.join(base_path, "artist_id_list.txt")
        self.track_id_list = os.path.join(base_path, "track_id_list.txt")

        self.separator = " :: "

    def log(self, message):
        if self.log_callback:
            self.log_callback(message)
        else:
            print(message)

    def report_progress(self, current, total, message=""):
        if self.progress_callback:
            self.progress_callback(current, total, message)

    def cancel(self):
        self.cancel_flag = True

    def check_cancel(self):
        if self.cancel_flag:
            raise OperationCancelled("Operation cancelled by user.")

    # ─────────────────────────────────────────────
    # LOGIN
    # ─────────────────────────────────────────────
    def start_login_source(self):
        return self._start_login(self.session_source)

    def start_login_dest(self):
        return self._start_login(self.session_dest)

    def _start_login(self, session):
        login, future = session.login_oauth()
        return login.verification_uri_complete, future

    def is_source_logged_in(self):
        return self.session_source.check_login()

    def is_dest_logged_in(self):
        return self.session_dest.check_login()

    # ─────────────────────────────────────────────
    # FETCHING / PAGINATION
    # ─────────────────────────────────────────────
    def fetch_all(self, fetch_fn, count_fn, label, page_size=50):
        try:
            total = count_fn()
        except:
            total = 0

        self.log(f"Found {total} {label}.")

        if total == 0:
            return []

        items = []
        offset = 0

        self.report_progress(0, total, f"Fetching {label}...")

        while offset < total:
            self.check_cancel()
            batch = fetch_fn(limit=page_size, offset=offset)
            if not batch:
                break
            items.extend(batch)
            offset += len(batch)
            self.report_progress(offset, total, f"Fetching {label}: {offset}/{total}")

        return items

    # ─────────────────────────────────────────────
    # EXPORT
    # ─────────────────────────────────────────────
    def export_content(self, transfer_tracks=False, transfer_albums=False, transfer_artists=False, transfer_playlists=False):
        if not self.is_source_logged_in():
            self.log("Source account not logged in!")
            return

        source = self.session_source.user.favorites
        self.log("Starting Export...")

        # 1. ALBUMS
        if transfer_albums:
            self.log("Exporting Albums...")
            albums = self.fetch_all(source.albums, source.get_albums_count, "albums")
            albums.sort(key=lambda x: x.user_date_added or 0)
            with open(self.album_id_list, "w", encoding="utf-8") as f:
                for item in albums:
                    meta = f"Album: {item.name} | Artist: {self._get_artist_name(item)}"
                    f.write(f"{item.id}{self.separator}{meta}\n")
                    self.meta_cache[str(item.id)] = meta
            self.log(f"Exported {len(albums)} albums.")

        # 2. ARTISTS
        if transfer_artists:
            self.log("Exporting Artists...")
            artists = self.fetch_all(source.artists, source.get_artists_count, "artists")
            artists.sort(key=lambda x: x.user_date_added or 0)
            with open(self.artist_id_list, "w", encoding="utf-8") as f:
                for item in artists:
                    meta = f"Artist: {item.name}"
                    f.write(f"{item.id}{self.separator}{meta}\n")
                    self.meta_cache[str(item.id)] = meta
            self.log(f"Exported {len(artists)} artists.")

        # 3. TRACKS
        if transfer_tracks:
            self.log("Exporting Tracks...")
            tracks = self.fetch_all(source.tracks, source.get_tracks_count, "favorite tracks")
            tracks.sort(key=lambda x: x.user_date_added or 0)
            with open(self.track_id_list, "w", encoding="utf-8") as f:
                for item in tracks:
                    meta = f"Track: {item.name} | Artist: {self._get_artist_name(item)}"
                    f.write(f"{item.id}{self.separator}{meta}\n")
                    self.meta_cache[str(item.id)] = meta
            self.log(f"Exported {len(tracks)} tracks.")

        # 4. PLAYLISTS
        if transfer_playlists:
            self.log("Exporting Playlists...")
            playlists = self.fetch_all(source.playlists, source.get_playlists_count, "playlists")

            playlists_data = []
            count = 0
            total_pl = len(playlists)

            for pl in playlists:
                self.check_cancel()
                count += 1
                self.report_progress(count, total_pl, f"Scanning playlist: {pl.name}")

                try:
                    pl_items = []
                    offset = 0
                    while True:
                        self.check_cancel()
                        batch = pl.items(limit=100, offset=offset)
                        if not batch: break
                        pl_items.extend(batch)
                        offset += len(batch)

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
                            self.meta_cache[str(item.id)] = f"Track in PL '{pl.name}': {meta_info}"

                    playlists_data.append({
                        "name": pl.name,
                        "description": pl.description,
                        "tracks": track_objects
                    })
                except Exception as e:
                    self.log(f"WARN: Failed to fetch playlist {pl.name}: {e}")

            with open(self.playlist_export_file, "w", encoding="utf-8") as f:
                json.dump(playlists_data, f, ensure_ascii=False, indent=4)
            self.log(f"Exported {len(playlists_data)} playlists.")

        self.log("Export Completed.")

    # ─────────────────────────────────────────────
    # IMPORT
    # ─────────────────────────────────────────────
    def import_content(self, transfer_tracks=False, transfer_albums=False, transfer_artists=False, transfer_playlists=False):
        if not self.is_dest_logged_in():
            self.log("Destination account not logged in!")
            return

        dest = self.session_dest.user.favorites
        self.log("Starting Import...")

        if transfer_albums:
            self._add_simple_items(self.album_id_list, dest.add_album, "albums")

        if transfer_artists:
            self._add_simple_items(self.artist_id_list, dest.add_artist, "artists")

        if transfer_playlists:
            self._import_playlists_cloned()

        if transfer_tracks:
            self._add_simple_items(self.track_id_list, dest.add_track, "favorite tracks")

        self.log("Import Completed.")

    def _add_simple_items(self, filename, add_fn, label):
        if not os.path.exists(filename):
            self.log(f"File {filename} not found. Skipping {label}.")
            return

        with open(filename, "r", encoding="utf-8") as f:
            lines = f.readlines()

        ids_to_process = []
        for line in lines:
            line = line.strip()
            if not line: continue
            if self.separator in line:
                parts = line.split(self.separator, 1)
                item_id = parts[0].strip()
                meta = parts[1].strip()
                self.meta_cache[item_id] = meta
                ids_to_process.append(item_id)
            else:
                ids_to_process.append(line.strip())

        total = len(ids_to_process)
        self.log(f"Adding {total} {label}...")

        success = 0
        for i, item_id in enumerate(ids_to_process):
            self.check_cancel()
            self.report_progress(i+1, total, f"Adding {label}: {i+1}/{total}")
            try:
                add_fn(item_id)
                success += 1
            except Exception as e:
                info = self.meta_cache.get(str(item_id), f"ID: {item_id}")
                self._log_error(info, e)

        self.log(f"Added {success}/{total} {label}.")

    def _import_playlists_cloned(self):
        if not os.path.exists(self.playlist_export_file):
            self.log("Playlists export file not found.")
            return

        with open(self.playlist_export_file, "r", encoding="utf-8") as f:
            playlists_data = json.load(f)

        total = len(playlists_data)
        self.log(f"Cloning {total} playlists...")

        for i, pl_data in enumerate(playlists_data):
            self.check_cancel()
            self.report_progress(i+1, total, f"Cloning playlist: {pl_data['name']}")

            pl_name = pl_data['name']
            pl_desc = pl_data.get('description', '')
            raw_tracks = pl_data.get('tracks', [])

            try:
                new_pl = self.session_dest.user.create_playlist(pl_name, pl_desc)
                if not raw_tracks: continue

                track_ids_only = []
                for t in raw_tracks:
                    if isinstance(t, dict):
                        tid = t['id']
                        self.meta_cache[tid] = f"Track: {t['meta']} (in PL '{pl_name}')"
                        track_ids_only.append(tid)
                    else:
                        track_ids_only.append(t)

                try:
                    new_pl.add(track_ids_only)
                except Exception as e:
                    self.log(f"Batch add failed for '{pl_name}', trying one by one...")
                    for tid in track_ids_only:
                        self.check_cancel()
                        try:
                            new_pl.add([tid])
                        except Exception as inner_e:
                            info = self.meta_cache.get(tid, f"Track ID: {tid} in playlist '{pl_name}'")
                            self._log_error(info, inner_e)

            except Exception as e:
                self.log(f"CRITICAL: Failed to create playlist '{pl_name}'")
                self._log_error(f"Playlist: {pl_name}", e)

    # ─────────────────────────────────────────────
    # DELETE
    # ─────────────────────────────────────────────
    def delete_content(self, delete_tracks=False, delete_albums=False, delete_artists=False, delete_playlists=False):
        # Assumes user wants to delete from SOURCE session (or whatever session is active)
        # Or maybe we should prompt? The original script just says "Login to the account you want to CLEAN".
        # Let's assume we use session_source for deletion if logged in, otherwise error.

        session = self.session_source
        if not session.check_login():
            self.log("Account not logged in! Please login to Source account to delete items.")
            return

        favorites = session.user.favorites
        user_id = session.user.id
        self.log("Starting Deletion...")

        if delete_albums:
            albums = self.fetch_all(favorites.albums, favorites.get_albums_count, "albums")
            self._remove_items(albums, favorites.remove_album, "albums")

        if delete_artists:
            artists = self.fetch_all(favorites.artists, favorites.get_artists_count, "artists")
            self._remove_items(artists, favorites.remove_artist, "artists")

        if delete_tracks:
            tracks = self.fetch_all(favorites.tracks, favorites.get_tracks_count, "tracks")
            self._remove_items(tracks, favorites.remove_track, "tracks")

        if delete_playlists:
            playlists = self.fetch_all(favorites.playlists, favorites.get_playlists_count, "playlists")
            self._process_delete_playlists(session, playlists, user_id)

        self.log("Deletion Completed.")

    def _remove_items(self, items, remove_fn, label):
        if not items: return

        total = len(items)
        self.log(f"Deleting {total} {label}...")
        success = 0

        for i, item in enumerate(items):
            self.check_cancel()
            self.report_progress(i+1, total, f"Deleting {label}: {item.name}")
            try:
                remove_fn(item.id)
                success += 1
            except Exception as e:
                self.log(f"ERROR: Could not remove {item.name}: {e}")

        self.log(f"Removed {success}/{total} {label}.")

    def _process_delete_playlists(self, session, playlists, user_id):
        if not playlists: return

        total = len(playlists)
        self.log(f"Processing {total} playlists...")
        deleted = 0
        unfollowed = 0

        for i, pl in enumerate(playlists):
            self.check_cancel()
            self.report_progress(i+1, total, f"Processing playlist: {pl.name}")
            try:
                is_owner = False
                if hasattr(pl, 'creator') and pl.creator:
                    if str(pl.creator.id) == str(user_id):
                        is_owner = True

                if is_owner:
                    session.request.request('DELETE', f'playlists/{pl.id}')
                    deleted += 1
                else:
                    session.user.favorites.remove_playlist(pl.id)
                    unfollowed += 1
            except Exception as e:
                self.log(f"ERROR: Issue with playlist '{pl.name}': {e}")

        self.log(f"Playlists: {deleted} deleted, {unfollowed} unfollowed.")

    # ─────────────────────────────────────────────
    # HELPERS
    # ─────────────────────────────────────────────
    def _get_artist_name(self, item):
        if hasattr(item, 'artist') and item.artist:
            return item.artist.name
        return "Unknown Artist"

    def _log_error(self, info, error_msg):
        self.log(f"ERROR: {info} -> {error_msg}")
        with open(self.failed_log_file, "a", encoding="utf-8") as log:
            log.write(f"{info}\n   -> Reason: {error_msg}\n")
