import kivy
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.checkbox import CheckBox
from kivy.uix.gridlayout import GridLayout
from kivy.uix.tabbedpanel import TabbedPanel, TabbedPanelItem
from kivy.uix.progressbar import ProgressBar
from kivy.clock import Clock
from kivy.properties import StringProperty, NumericProperty, BooleanProperty
from kivy.logger import Logger

import threading
import webbrowser
import os
from logic import TidalManager

kivy.require('2.0.0')

class TidalApp(App):
    log_text = StringProperty("Welcome to Tidal Transfer Tool!\n")
    progress_val = NumericProperty(0)
    progress_max = NumericProperty(100)
    status_text = StringProperty("Ready")

    source_logged_in = BooleanProperty(False)
    dest_logged_in = BooleanProperty(False)

    def build(self):
        self.title = "Tidal Transfer Tool"

        # Initialize Logic
        # Use user_data_dir for file storage on Android
        data_dir = self.user_data_dir
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)

        self.manager = TidalManager(
            base_path=data_dir,
            log_callback=self.update_log,
            progress_callback=self.update_progress
        )

        # Root Layout
        root = BoxLayout(orientation='vertical', padding=10, spacing=10)

        # Header / Status
        header = BoxLayout(size_hint_y=None, height=40)
        self.status_label = Label(text=self.status_text)
        header.add_widget(self.status_label)
        root.add_widget(header)

        # Tabs
        self.tabs = TabbedPanel(do_default_tab=False)

        # Tab 1: Transfer
        tab_transfer = TabbedPanelItem(text='Transfer')
        tab_transfer.content = self.build_transfer_ui()
        self.tabs.add_widget(tab_transfer)

        # Tab 2: Delete
        tab_delete = TabbedPanelItem(text='Delete')
        tab_delete.content = self.build_delete_ui()
        self.tabs.add_widget(tab_delete)

        root.add_widget(self.tabs)

        # Progress Bar
        self.pb = ProgressBar(max=100, size_hint_y=None, height=20)
        root.add_widget(self.pb)

        # Log Area
        log_scroll = ScrollView(size_hint=(1, 0.3))
        self.log_label = Label(text=self.log_text, size_hint_y=None, markup=True, halign='left', valign='top')
        self.log_label.bind(texture_size=self.log_label.setter('size'))
        self.log_label.bind(text=self.on_log_text) # Auto scroll
        log_scroll.add_widget(self.log_label)
        root.add_widget(log_scroll)

        return root

    def on_log_text(self, instance, value):
        # Auto-scroll not easily doable with simple binding, but acceptable for now
        pass

    def build_transfer_ui(self):
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)

        # Login Section
        login_box = BoxLayout(orientation='vertical', size_hint_y=None, height=100, spacing=5)

        # Source Login
        src_box = BoxLayout()
        self.btn_login_src = Button(text="Login Source")
        self.btn_login_src.bind(on_release=self.login_source)
        self.lbl_src_status = Label(text="Not Logged In")
        src_box.add_widget(self.btn_login_src)
        src_box.add_widget(self.lbl_src_status)
        login_box.add_widget(src_box)

        # Dest Login
        dst_box = BoxLayout()
        self.btn_login_dst = Button(text="Login Destination")
        self.btn_login_dst.bind(on_release=self.login_dest)
        self.lbl_dst_status = Label(text="Not Logged In")
        dst_box.add_widget(self.btn_login_dst)
        dst_box.add_widget(self.lbl_dst_status)
        login_box.add_widget(dst_box)

        layout.add_widget(login_box)

        # Content Selection
        layout.add_widget(Label(text="Select Content to Transfer:", size_hint_y=None, height=30))

        selection_grid = GridLayout(cols=2, size_hint_y=None, height=100)

        self.chk_tracks = CheckBox(active=True)
        selection_grid.add_widget(Label(text="Favorite Tracks"))
        selection_grid.add_widget(self.chk_tracks)

        self.chk_albums = CheckBox(active=False)
        selection_grid.add_widget(Label(text="Albums"))
        selection_grid.add_widget(self.chk_albums)

        self.chk_artists = CheckBox(active=False)
        selection_grid.add_widget(Label(text="Artists"))
        selection_grid.add_widget(self.chk_artists)

        self.chk_playlists = CheckBox(active=False)
        selection_grid.add_widget(Label(text="Playlists"))
        selection_grid.add_widget(self.chk_playlists)

        layout.add_widget(selection_grid)

        # Actions
        actions_box = BoxLayout(size_hint_y=None, height=50, spacing=10)

        btn_export = Button(text="Export Only")
        btn_export.bind(on_release=lambda x: self.start_operation('export'))
        actions_box.add_widget(btn_export)

        btn_import = Button(text="Import Only")
        btn_import.bind(on_release=lambda x: self.start_operation('import'))
        actions_box.add_widget(btn_import)

        btn_full = Button(text="Full Transfer")
        btn_full.bind(on_release=lambda x: self.start_operation('full'))
        actions_box.add_widget(btn_full)

        layout.add_widget(actions_box)
        layout.add_widget(Label()) # Spacer

        return layout

    def build_delete_ui(self):
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)

        layout.add_widget(Label(text="DELETE MODE - USE WITH CAUTION", color=(1,0,0,1), size_hint_y=None, height=30))

        # Reuse source login or check login
        # Content Selection
        layout.add_widget(Label(text="Select Content to DELETE:", size_hint_y=None, height=30))

        selection_grid = GridLayout(cols=2, size_hint_y=None, height=100)

        self.chk_del_tracks = CheckBox(active=False)
        selection_grid.add_widget(Label(text="Favorite Tracks"))
        selection_grid.add_widget(self.chk_del_tracks)

        self.chk_del_albums = CheckBox(active=False)
        selection_grid.add_widget(Label(text="Albums"))
        selection_grid.add_widget(self.chk_del_albums)

        self.chk_del_artists = CheckBox(active=False)
        selection_grid.add_widget(Label(text="Artists"))
        selection_grid.add_widget(self.chk_del_artists)

        self.chk_del_playlists = CheckBox(active=False)
        selection_grid.add_widget(Label(text="Playlists"))
        selection_grid.add_widget(self.chk_del_playlists)

        layout.add_widget(selection_grid)

        btn_delete = Button(text="DELETE SELECTED", background_color=(1,0,0,1))
        btn_delete.bind(on_release=lambda x: self.start_operation('delete'))
        layout.add_widget(btn_delete)

        layout.add_widget(Label()) # Spacer

        return layout

    # ─────────────────────────────────────────────
    # LOGIC INTEGRATION
    # ─────────────────────────────────────────────

    def update_log(self, message):
        Clock.schedule_once(lambda dt: self._append_log(message))

    def _append_log(self, message):
        self.log_text += message + "\n"

    def update_progress(self, current, total, message):
        Clock.schedule_once(lambda dt: self._set_progress(current, total, message))

    def _set_progress(self, current, total, message):
        if total > 0:
            self.pb.max = total
            self.pb.value = current
        self.status_label.text = message

    # ─────────────────────────────────────────────
    # THREADING WRAPPERS
    # ─────────────────────────────────────────────

    def login_source(self, instance):
        threading.Thread(target=self._login_source_thread).start()

    def _login_source_thread(self):
        try:
            url, future = self.manager.start_login_source()
            self.update_log(f"Opening login page: {url}")
            webbrowser.open(url)
            future.result()
            self.update_log("Source Logged In Successfully!")
            Clock.schedule_once(lambda dt: setattr(self.lbl_src_status, 'text', 'Logged In'))
            self.source_logged_in = True
        except Exception as e:
            self.update_log(f"Login Failed: {e}")

    def login_dest(self, instance):
        threading.Thread(target=self._login_dest_thread).start()

    def _login_dest_thread(self):
        try:
            url, future = self.manager.start_login_dest()
            self.update_log(f"Opening login page: {url}")
            webbrowser.open(url)
            future.result()
            self.update_log("Destination Logged In Successfully!")
            Clock.schedule_once(lambda dt: setattr(self.lbl_dst_status, 'text', 'Logged In'))
            self.dest_logged_in = True
        except Exception as e:
            self.update_log(f"Login Failed: {e}")

    def start_operation(self, op_type):
        # Capture UI state in main thread
        if op_type == 'delete':
            params = {
                'tracks': self.chk_del_tracks.active,
                'albums': self.chk_del_albums.active,
                'artists': self.chk_del_artists.active,
                'playlists': self.chk_del_playlists.active
            }
        else:
            params = {
                'tracks': self.chk_tracks.active,
                'albums': self.chk_albums.active,
                'artists': self.chk_artists.active,
                'playlists': self.chk_playlists.active
            }

        threading.Thread(target=self._run_operation, args=(op_type, params)).start()

    def _run_operation(self, op_type, params):
        try:
            if op_type == 'export':
                self.manager.export_content(
                    params['tracks'], params['albums'], params['artists'], params['playlists']
                )
            elif op_type == 'import':
                self.manager.import_content(
                    params['tracks'], params['albums'], params['artists'], params['playlists']
                )
            elif op_type == 'full':
                self.manager.export_content(
                    params['tracks'], params['albums'], params['artists'], params['playlists']
                )
                self.manager.import_content(
                    params['tracks'], params['albums'], params['artists'], params['playlists']
                )
            elif op_type == 'delete':
                self.manager.delete_content(
                    params['tracks'], params['albums'], params['artists'], params['playlists']
                )
        except Exception as e:
            Clock.schedule_once(lambda dt: self._append_log(f"Operation Failed: {e}"))

if __name__ == '__main__':
    TidalApp().run()
