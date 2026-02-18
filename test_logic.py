import unittest
from unittest.mock import MagicMock, patch
import os
import shutil
from logic import TidalManager

class TestTidalManager(unittest.TestCase):
    def setUp(self):
        self.test_dir = "test_data"
        if not os.path.exists(self.test_dir):
            os.makedirs(self.test_dir)
        self.manager = TidalManager(base_path=self.test_dir)

        # Mock sessions
        self.manager.session_source = MagicMock()
        self.manager.session_dest = MagicMock()

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_export_albums(self):
        # Setup mock data
        album1 = MagicMock()
        album1.name = "Album1"
        album1.id = "123"
        album1.artist.name = "Artist1"
        album1.user_date_added = 0

        source = self.manager.session_source.user.favorites
        source.get_albums_count.return_value = 1
        source.albums.return_value = [album1]

        self.manager.session_source.check_login.return_value = True

        # Run export
        self.manager.export_content(transfer_albums=True)

        # Check file created
        file_path = os.path.join(self.test_dir, "album_id_list.txt")
        self.assertTrue(os.path.exists(file_path))
        with open(file_path, "r") as f:
            content = f.read()
            self.assertIn("123 :: Album: Album1 | Artist: Artist1", content)

    def test_import_albums(self):
        # Create dummy file
        file_path = os.path.join(self.test_dir, "album_id_list.txt")
        with open(file_path, "w") as f:
            f.write("123 :: Album: Album1 | Artist: Artist1\n")

        dest = self.manager.session_dest.user.favorites
        self.manager.session_dest.check_login.return_value = True

        # Run import
        self.manager.import_content(transfer_albums=True)

        # Check add_album called
        dest.add_album.assert_called_with("123")

if __name__ == '__main__':
    unittest.main()
