import os
import requests
import random
import string
import subprocess
import re
import urllib.parse
import argparse
from tqdm import tqdm


def generate_random_filename():
    return ''.join(random.choices(string.ascii_letters, k=10)) + '.mp4'


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--url', type=str, help='URL of the video')
    parser.add_argument('--output_dir', default=os.path.join(
        os.getcwd(), 'xvideos_output'), type=str, help='Output directory')
    parser.add_argument('--output_filename', default=generate_random_filename(
    ), type=str, help='Output filename')
    # parser.add_argument('playlist_url', type=str, help='URL of the playlist')
    parser.add_argument('--silent', action='store_true',
                        help='Disable progress bar')
    parser.add_argument('--ffmpeg_path', type=str,
                        default='ffmpeg', help='Path to ffmpeg')
    parser.add_argument('--quality_mode', choices=[
                        'best', 'prompt', 'worst'], help='Quality mode', default='best')
    return parser.parse_args()


def get_fractions_from_playlist_and_download(playlist_url, args):
    prefix = playlist_url.replace(playlist_url.split('/')[-1], '')
    filelist_path = os.path.join(args.output_dir, 'filelist.txt')
    output_filepath = os.path.join(args.output_dir, args.output_filename)
    # Create the download directory if it does not exist
    os.makedirs(args.output_dir, exist_ok=True)

    # request the playlist file
    response = requests.get(playlist_url)
    # Read the playlist
    lines = response.content.decode().split('\n')

    # Filter and download each segment
    segment_filenames = []
    for line in tqdm(lines, disable=args.silent, desc='Downloading segments'):
        if not line.startswith('#') and line:
            segment_filename = line.strip()
            segment_url = urllib.parse.urljoin(prefix, segment_filename)
            segment_path = os.path.join(args.output_dir, segment_filename)

            # Download the segment
            segment_response = requests.get(segment_url)
            with open(segment_path, 'wb') as segment_file:
                segment_file.write(segment_response.content)

            # Add to segment filenames list
            segment_filenames.append(segment_filename)
    # Write the file list for ffmpeg
    with open(filelist_path, 'w') as filelist:
        for segment_filename in segment_filenames:
            filelist.write(f"file '{segment_filename}'\n")

    subprocess.run(['ffmpeg', '-f', 'concat', '-safe', '0', '-i',
                    filelist_path, '-c', 'copy', output_filepath])

# Generate a random output filename


def get_playlist_from_page(page_url):
    req = requests.get(page_url)
    url_regex = re.compile(r'(https?://[^ ]+m3u8)', re.IGNORECASE)
    match = url_regex.search(req.text)
    if match:
        url = match.group(0)
        playlist_req = requests.get(url)
        cdn_url = url.replace(url.split('/')[-1], '')

    qualities = {}
    for line in playlist_req.content.decode().split('\n'):
        if not line.startswith('#'):
            quality_regex = re.compile(r'\d{3,4}(?=p)', re.IGNORECASE)
            match = quality_regex.search(line)
            if match:
                m = match.group(0)
                qualities[int(m)] = line
    return qualities, cdn_url


def select_quality(qualities, quality_mode):
    if quality_mode == 'best':
        return qualities[max(qualities)]
    elif quality_mode == 'prompt':
        print('Available qualities:')
        for quality in qualities:
            print(quality)
        return qualities[int(input('Enter quality: '))]
    elif quality_mode == 'worst':
        return qualities[min(qualities)]


def main():
    args = parse_args()
    qualities, cdn_url = get_playlist_from_page(args.url)
    qual = select_quality(qualities, args.quality_mode)
    get_fractions_from_playlist_and_download(
        urllib.parse.urljoin(cdn_url, qual), args)


if __name__ == '__main__':
    main()
