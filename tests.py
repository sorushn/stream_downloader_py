import unittest
from unittest.mock import patch, mock_open, MagicMock
import os

# Assuming all functions are imported from the module
from your_module import download_playlist, read_playlist, download_segment, write_filelist, generate_random_filename, concatenate_segments


class TestVideoDownloader(unittest.TestCase):

    @patch('requests.get')
    def test_download_playlist(self, mock_get):
        mock_get.return_value.ok = True
        mock_get.return_value.content = b"Test content"
        playlist_path = 'test_playlist.m3u8'

        download_playlist('http://example.com/playlist.m3u8', playlist_path)

        mock_get.assert_called_once_with('http://example.com/playlist.m3u8')
        with open(playlist_path, 'rb') as file:
            self.assertEqual(file.read(), b"Test content")

        os.remove(playlist_path)

    def test_read_playlist(self):
        playlist_content = "#EXTM3U\nhttp://example.com/segment1.ts\n#EXTINF\nhttp://example.com/segment2.ts"
        with patch('builtins.open', mock_open(read_data=playlist_content)):
            segments = read_playlist('test_playlist.m3u8')
            self.assertEqual(
                segments, ['http://example.com/segment1.ts', 'http://example.com/segment2.ts'])

    @patch('requests.get')
    def test_download_segment(self, mock_get):
        mock_get.return_value.ok = True
        mock_get.return_value.content = b"Segment content"
        prefix = 'test_prefix'
        segment_url = 'http://example.com/segment1.ts'

        os.makedirs(prefix, exist_ok=True)

        segment_filename = download_segment(segment_url, prefix)
        expected_filename = 'segment1.ts'

        self.assertEqual(segment_filename, expected_filename)
        mock_get.assert_called_once_with(segment_url)

        segment_path = os.path.join(prefix, expected_filename)
        with open(segment_path, 'rb') as file:
            self.assertEqual(file.read(), b"Segment content")

        os.remove(segment_path)
        os.rmdir(prefix)

    def test_write_filelist(self):
        segment_filenames = ['segment1.ts', 'segment2.ts']
        filelist_path = 'test_filelist.txt'

        write_filelist(segment_filenames, filelist_path)

        with open(filelist_path, 'r') as file:
            content = file.read()
            self.assertEqual(
                content, "file 'segment1.ts'\nfile 'segment2.ts'\n")

        os.remove(filelist_path)

    def test_generate_random_filename(self):
        filename = generate_random_filename()
        self.assertTrue(len(filename) == 14)  # 10 chars + '.mp4'
        self.assertTrue(filename.endswith('.mp4'))

    @patch('subprocess.run')
    def test_concatenate_segments(self, mock_run):
        filelist_path = 'test_filelist.txt'
        output_filepath = 'output.mp4'

        concatenate_segments(filelist_path, output_filepath)

        mock_run.assert_called_once_with(
            ['ffmpeg', '-f', 'concat', '-safe', '0', '-i', filelist_path, '-c', 'copy', output_filepath], check=True)


if __name__ == '__main__':
    unittest.main()
