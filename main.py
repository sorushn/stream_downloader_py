import os
import requests
import random
import string
import re
import urllib.parse
import argparse
from tqdm import tqdm


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--url', type=str, help='URL of the video')
    parser.add_argument('--output_dir', default=os.path.join(
        os.getcwd(), 'xvideos_output'), type=str, help='Output directory')
    parser.add_argument('--output_filename', type=str, help='Output filename')
    parser.add_argument('--silent', action='store_true',
                        help='Disable progress bar')
    parser.add_argument('--ffmpeg_path', type=str,
                        default='ffmpeg', help='Path to ffmpeg')
    parser.add_argument('--quality_mode', choices=[
                        'best', 'prompt', 'worst'], help='Quality mode, best for best available quality, prompt for manual selection, worst for worst available quality', default='best')
    parser.add_argument('--cleanup', action='store_false',
                        help='remove segment files after download')
    return parser.parse_args()


def generate_random_filename():
    return ''.join(random.choices(string.ascii_letters, k=10)) + '.mp4'


def get_title_from_request(req):
    title_regex = re.compile(r'<title>(.*?)</title>', re.IGNORECASE)
    match = title_regex.search(req.text)
    if match:
        return match.group(1) + '.mp4'
    return None


def get_fractions_from_playlist_and_download(playlist_url, args):
    """
    Downloads segments from a playlist and concatenates them into a single file.

    Args:
        playlist_url (str): The URL of the playlist.
        args (Namespace): Command line arguments containing the output directory and filename.

    Returns:
        None

    Description:
        This function takes a playlist URL and downloads the segments from the playlist.
        The segments are filtered and downloaded sequentially, and each segment is saved in
        the specified output directory. The filenames of the downloaded segments are stored
        in a list. After downloading all the segments, a file list is written for ffmpeg to
        concatenate the segments into a single file. The resulting file is saved in the output
        directory with the specified filename.

    Note:
        - The function creates the output directory if it does not exist.
        - The function uses the requests library to make HTTP requests.
        - The function uses the tqdm library to display a progress bar for downloading segments.
        - The function uses the subprocess library to run the ffmpeg command for concatenation.
    """
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


def get_playlist_from_page(page_url):
    """
    Retrieves the main .m3u8 playlist from a given webpage.

    Args:
        page_url (str): The URL of the webpage to retrieve the playlist from.

    Returns:
        tuple: A tuple containing the following:
            - qualities (dict): A dictionary mapping quality values to playlist lines.
            - cdn_url (str): The CDN URL of the playlist.
            - title (str): The title of the playlist. If no title is found, a random filename is generated.

    Notes:
        - The function sends a GET request to the given page_url and retrieves the playlist URL from the response text.
        - The playlist URL is constructed by replacing the last segment of the URL with an empty string.
        - The function then sends another GET request to the playlist URL to retrieve the playlist content.
        - The playlist content is split into lines, and for each line, the function searches for a quality value using a regular expression.
        - The quality value and the line are added to the qualities dictionary.
        - The function then calls get_title_from_request to retrieve the title of the playlist.
        - If no title is found, a random filename is generated using the generate_random_filename function.
    """
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
    title = get_title_from_request(req)
    if not title:
        title = generate_random_filename()
    return qualities, cdn_url, get_title_from_request(req)


def select_quality(qualities, quality_mode):
    """
    returns the quality .m3u8 based on the given quality mode.

    Args:
        qualities (dict): A dictionary of qualities, where the keys are integers representing the quality and the values are the corresponding .m3u8 playlist filenames.
        quality_mode (str): The mode for selecting the quality. Can be 'best', 'prompt', or 'worst'.

    Returns:
        The selected quality based on the given quality mode.
    """
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
    qualities, cdn_url, title = get_playlist_from_page(args.url)
    if not args.output_filename:
        args.output_filename = title + '.mp4'
    qual = select_quality(qualities, args.quality_mode)
    get_fractions_from_playlist_and_download(
        urllib.parse.urljoin(cdn_url, qual), args)

    if args.cleanup:
        for filename in os.listdir(args.output_dir):
            if filename.endswith('.ts'):
                os.remove(os.path.join(args.output_dir, filename))


if __name__ == '__main__':
    main()
