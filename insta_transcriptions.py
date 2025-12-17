import requests
from bs4 import BeautifulSoup
import subprocess
import json
import re
import time

# --- Configuration ---
# User-Agent to mimic a browser. It's good practice to use a realistic one.
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9'
}
# Timeout for requests in seconds
REQUEST_TIMEOUT = 15
# Delay between requests to be polite to the server (in seconds)
REQUEST_DELAY = 2.5  # Slightly increased delay


# --- Method 1: requests + BeautifulSoup ---
def get_caption_bs(reel_url):
    """
    Attempts to extract caption using requests and BeautifulSoup.
    WARNING: This method is HIGHLY DEPENDENT on Instagram's current HTML structure
    and data embedding, which change frequently. It is very likely to break.
    """
    print(f"  [BS Attempt] Fetching {reel_url}...")
    try:
        session = requests.Session()
        session.headers.update(HEADERS)
        response = session.get(reel_url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)

        time.sleep(REQUEST_DELAY / 2)

        soup = BeautifulSoup(response.text, 'html.parser')

        caption = None

        # Strategy 1: Look for JSON embedded in <script type="application/ld+json">
        # This is often used for structured data and can be more stable than other methods.
        script_ld_json = soup.find('script', type='application/ld+json')
        if script_ld_json and script_ld_json.string:
            try:
                json_data = json.loads(script_ld_json.string)
                if isinstance(json_data, list):
                    json_data = json_data[0] if json_data else {}

                caption_text = json_data.get('caption') or \
                               json_data.get('description') or \
                               json_data.get('articleBody')

                if isinstance(caption_text, dict) and caption_text.get('text'):
                    caption_text = caption_text.get('text')
                elif isinstance(caption_text, list):
                    caption_text = " ".join(str(part) for part in caption_text if isinstance(part, str))

                if caption_text and isinstance(caption_text, str):
                    print("  [BS Success] Found caption in ld+json script.")
                    return caption_text.strip()
            except json.JSONDecodeError:
                print("  [BS Info] ld+json script found but failed to parse.")
            except Exception as e:
                print(f"  [BS Warning] Error processing ld+json: {e}")

        # Strategy 2: Look for JSON embedded in other <script> tags.
        # VERY FRAGILE: Instagram often embeds a lot of data in JavaScript variables.
        # The patterns, variable names, and JSON structures (e.g., 'xdt_api__v1__media__shortcode__web_info',
        # 'gql_data', 'items', 'edge_media_to_caption') are internal and change without notice.
        script_tags = soup.find_all('script')
        for script in script_tags:
            if not script.string:
                continue

            # Attempt to find known patterns that might contain the main data blob
            # These patterns are based on past observations and are subject to change.
            if 'xdt_api__v1__media__shortcode__web_info' in script.string or \
                    'gql_data' in script.string or \
                    'shortcode_media' in script.string:
                try:
                    # Try to extract a large JSON blob. This is a heuristic.
                    # Look for JSON-like structures. This regex is a general attempt.
                    json_match = re.search(r'(?<={\s*").*?(?=\s*"})', script.string,
                                           re.DOTALL)  # Simpler regex, might need refinement
                    # A more common pattern is data assigned to window._sharedData or similar
                    shared_data_match = re.search(r'window\._sharedData\s*=\s*(\{.*?\});', script.string)
                    if shared_data_match:
                        potential_json_str = shared_data_match.group(1)
                    elif 'gql_data' in script.string:  # Try to find a specific known structure
                        # This is highly speculative and depends on current IG structure
                        gql_match = re.search(r'\{\s*"gql_data"\s*:\s*(\{.*?\})\s*\}', script.string)
                        if gql_match:
                            potential_json_str = gql_match.group(1)
                        else:  # Fallback to a more general match if specific pattern fails
                            json_match = re.search(r'(\{.*?"shortcode_media":.*?})', script.string)
                            potential_json_str = json_match.group(1) if json_match else None
                    else:  # Fallback to the initial broader regex if specific patterns fail
                        json_match_general = re.search(r'(\{.*?\})(?:;?</script)', script.string, re.DOTALL)
                        potential_json_str = json_match_general.group(1) if json_match_general else None

                    if potential_json_str:
                        data = json.loads(potential_json_str)

                        # Navigate through potential JSON structures. These paths WILL CHANGE.
                        # Path 1: data -> items -> 0 -> caption -> text
                        items = data.get('items')
                        if not items and data.get('entry_data', {}).get('PostPage'):
                            # Another common structure
                            post_page_data = data['entry_data']['PostPage']
                            if post_page_data and isinstance(post_page_data, list) and post_page_data[0].get('graphql',
                                                                                                             {}).get(
                                    'shortcode_media'):
                                items = [post_page_data[0]['graphql']['shortcode_media']]
                        elif not items and data.get('shortcode_media'):  # Direct shortcode_media
                            items = [data.get('shortcode_media')]

                        if items and isinstance(items, list) and len(items) > 0:
                            first_item = items[0]
                            if isinstance(first_item, dict):
                                # Try path: caption -> text
                                caption_node = first_item.get('caption')
                                if caption_node and isinstance(caption_node, dict) and 'text' in caption_node:
                                    caption = caption_node['text']
                                    if caption:
                                        print("  [BS Success] Found caption in embedded script (items->caption).")
                                        return caption.strip()

                                # Try path: edge_media_to_caption -> edges -> 0 -> node -> text
                                edge_media_to_caption = first_item.get('edge_media_to_caption', {}).get('edges', [])
                                if edge_media_to_caption and isinstance(edge_media_to_caption, list) and len(
                                        edge_media_to_caption) > 0:
                                    node = edge_media_to_caption[0].get('node')
                                    if node and isinstance(node, dict) and 'text' in node:
                                        caption = node['text']
                                        if caption:
                                            print("  [BS Success] Found caption (edge_media_to_caption).")
                                            return caption.strip()
                except json.JSONDecodeError:
                    # This is expected for many script tags that aren't JSON.
                    # print(f"  [BS Debug] Script not valid JSON or structure changed.")
                    pass
                except AttributeError:  # If regex match fails and .group(1) is called on None
                    # print(f"  [BS Debug] Regex did not find expected JSON structure in script.")
                    pass
                except Exception as e:
                    print(f"  [BS Warning] Error processing script tag for JSON: {e}")
                    pass  # Continue to the next script tag

        # Strategy 3: Fallback to common HTML element patterns (EXTREMELY UNRELIABLE)
        # Instagram uses obfuscated and frequently changing class names.
        # This strategy is a last-ditch effort and highly unlikely to work consistently.
        # Example class prefixes: _aacl, _aaco. These will change.
        print("  [BS Info] Trying generic HTML element patterns (very unreliable)...")
        possible_caption_elements = soup.find_all(['h1', 'div', 'span'], class_=lambda c: c and any(
            cls_part.startswith('_aa') for cls_part in c.split()))
        for el in possible_caption_elements:
            # The caption is often in a span, or a div that doesn't contain other complex structures.
            # Heuristic: look for text that isn't just a username or timestamp.
            text_content = el.get_text(separator=' ', strip=True)
            if text_content and len(
                    text_content) > 15 and "@" not in text_content and "Verified" not in text_content and "ago" not in text_content.lower():
                # Further check: ensure it's not just a collection of child element texts like "Follow" "Message" etc.
                if len(el.find_all(
                        ['button', 'a'])) < 2:  # Avoid elements that are clearly containers for action buttons
                    print(
                        f"  [BS Success/Heuristic] Found potential caption in generic HTML element: {text_content[:50]}...")
                    return text_content

        print("  [BS Info] Caption not found using any BeautifulSoup methods.")
        return None

    except requests.exceptions.Timeout:
        print(f"  [BS Error] Request timed out for {reel_url}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"  [BS Error] Request failed for {reel_url}: {e}")
        return None
    except Exception as e:
        print(f"  [BS Error] General parsing failed for {reel_url} with BeautifulSoup: {e}")
        return None


# --- Method 2: yt-dlp (Fallback) ---
def get_caption_ytdlp(reel_url):
    """
    Attempts to extract caption (usually as 'description') using yt-dlp.
    This is generally more reliable than direct HTML parsing for metadata.
    """
    print(f"  [yt-dlp Attempt] Trying yt-dlp for {reel_url}...")
    process = None  # Initialize process variable
    try:
        command = [
            'yt-dlp',
            '--skip-download',  # Don't download the video
            '--dump-json',  # Output metadata as JSON
            '--no-warnings',  # Suppress warnings
            '--ignore-errors',  # Continue on errors for individual videos
            reel_url
        ]
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8')
        stdout, stderr = process.communicate(timeout=45)  # Increased timeout for yt-dlp

        if process.returncode != 0:
            # print(f"  [yt-dlp Error] yt-dlp process failed. Stderr: {stderr.strip()}")
            if "Unsupported URL" in stderr or "Unable to extract" in stderr:
                print(f"  [yt-dlp Info] URL might be unsupported or content private/deleted: {reel_url}")
            return None

        if stdout:
            try:
                metadata = json.loads(stdout)
                # For Instagram, the caption is often in the 'description' field.
                # It can also sometimes be in 'title' or other fields if 'description' is missing/short.
                caption = metadata.get('description')
                if not caption or len(caption) < 10:  # If description is too short or missing, check title
                    alt_caption = metadata.get('title')
                    if alt_caption and len(alt_caption) > len(caption or ""):
                        caption = alt_caption

                if caption:
                    print("  [yt-dlp Success] Caption/Description found via yt-dlp.")
                    return caption.strip()
            except json.JSONDecodeError:
                print(f"  [yt-dlp Error] Failed to parse JSON output from yt-dlp.")
                return None
            except Exception as e:
                print(f"  [yt-dlp Error] Error processing yt-dlp output: {e}")
                return None

        print("  [yt-dlp Info] No suitable caption/description found in yt-dlp output.")
        return None

    except subprocess.TimeoutExpired:
        print(f"  [yt-dlp Error] yt-dlp command timed out for {reel_url}")
        if process:
            try:
                process.kill()
                process.wait(timeout=5)  # Wait for the process to terminate
            except Exception as kill_e:
                print(f"  [yt-dlp Error] Exception during process kill: {kill_e}")
        return None
    except FileNotFoundError:
        print("  [yt-dlp Error] yt-dlp command not found. Critical for fallback. Please install and add to PATH.")
        return "YT-DLP_NOT_FOUND"  # Special marker
    except Exception as e:
        print(f"  [yt-dlp Error] General error using yt-dlp: {e}")
        return None


# --- Core Logic ---
def get_reel_caption_with_fallbacks(reel_url, ytdlp_available=True):
    """
    Tries to get caption using BeautifulSoup, then falls back to yt-dlp if available.
    """
    print(f"\nProcessing Reel: {reel_url}")

    # Method 1: BeautifulSoup (Highly Unreliable)
    caption_bs = get_caption_bs(reel_url)
    if caption_bs:
        return caption_bs

    print("  BeautifulSoup method failed or no caption found.")
    time.sleep(REQUEST_DELAY / 2)

    # Method 2: yt-dlp (More Reliable Fallback)
    if ytdlp_available:
        caption_ytdlp = get_caption_ytdlp(reel_url)
        if caption_ytdlp == "YT-DLP_NOT_FOUND":
            return "YT-DLP_NOT_FOUND_MARKER"
        if caption_ytdlp:
            return caption_ytdlp
        print(f"  yt-dlp method also failed or no caption found for {reel_url}.")
    else:
        print("  Skipping yt-dlp method as it's marked unavailable or failed critically.")

    return None


def get_reel_links_from_account_page(account_reels_url):
    """
    VERY BASIC attempt to get some Reel links from an account's Reels page.
    This will only get initially loaded Reels and is very fragile due to dynamic loading
    (Infinite Scroll) and frequent HTML structure changes on Instagram.
    For reliable results, provide direct Reel URLs or use advanced tools like Selenium.
    """
    print(f"\nAttempting to fetch Reel links from account page: {account_reels_url}")
    print("  (This method is basic and may not find all Reels due to dynamic loading)")
    try:
        session = requests.Session()
        session.headers.update(HEADERS)
        response = session.get(account_reels_url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        time.sleep(REQUEST_DELAY)

        soup = BeautifulSoup(response.text, 'html.parser')
        reel_links = set()

        # Instagram's structure for links in a profile's reels tab:
        # Links are typically <a> tags with href starting with "/reel/"
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            if href.startswith('/reel/'):
                # Construct full URL and remove query parameters like '?igshid=...'
                full_url = f"https://www.instagram.com{href.split('?')[0]}"
                reel_links.add(full_url)

        if not reel_links:
            print("  [Account Page Info] Could not find any Reel links using basic parsing of initial HTML.")
            print("  This is likely due to dynamic content loading or HTML structure changes by Instagram.")
        else:
            print(f"  [Account Page Info] Found {len(reel_links)} potential Reel links from initial HTML.")
        return list(reel_links)

    except requests.exceptions.Timeout:
        print(f"  [Account Page Error] Request timed out for {account_reels_url}")
        return []
    except requests.exceptions.RequestException as e:
        print(f"  [Account Page Error] Failed to fetch account page {account_reels_url}: {e}")
        return []
    except Exception as e:
        print(f"  [Account Page Error] Error parsing account page {account_reels_url}: {e}")
        return []


# --- Setup Check ---
def check_ytdlp_availability():
    """Checks if yt-dlp is installed and executable."""
    try:
        process = subprocess.run(['yt-dlp', '--version'], capture_output=True, text=True, timeout=10)
        if process.returncode == 0:
            print("[Setup Check] yt-dlp found and working.")
            return True
        else:
            print(
                f"[Setup Check Warning] 'yt-dlp --version' command failed (code {process.returncode}). stderr: {process.stderr.strip()}")
            print("  yt-dlp might be installed but not configured correctly, or there's an issue with yt-dlp itself.")
            return False  # Treat as unavailable if --version fails
    except FileNotFoundError:
        print("[Setup Check Error] yt-dlp command not found. Please install yt-dlp and add it to your system's PATH.")
        return False
    except subprocess.TimeoutExpired:
        print("[Setup Check Error] 'yt-dlp --version' command timed out.")
        return False
    except Exception as e:
        print(f"[Setup Check Error] An unexpected error occurred while checking for yt-dlp: {e}")
        return False


# --- Main Program ---
def main():
    print("=" * 70)
    print(" Instagram Reel Caption Extractor (Unofficial & Highly Experimental)")
    print("=" * 70)
    print("\nIMPORTANT DISCLAIMERS:")
    print("1. This script scrapes Instagram. Instagram frequently changes its website,")
    print("   which WILL BREAK this script, especially the direct HTML parsing methods.")
    print("2. Use of this script might be against Instagram's Terms of Service.")
    print("   USE AT YOUR OWN RISK. The developers assume no liability.")
    print("3. This script is for educational purposes. No guarantees are provided for its")
    print("   functionality, accuracy, or reliability.")
    print("4. The yt-dlp fallback method is generally more reliable for fetching descriptions.")
    print("-" * 70)

    ytdlp_globally_available = check_ytdlp_availability()
    if not ytdlp_globally_available:
        print("WARNING: yt-dlp is not available or not working correctly.")
        print("  The more reliable fallback method for caption extraction will be disabled.")
        print("  The script will rely solely on direct page parsing, which is highly unstable.")
    print("-" * 70)

    while True:
        print("\nChoose an option:")
        print("1. Get captions from an account's Reels (attempts to find some public Reel links - very basic)")
        print("2. Get captions from a list of specific Reel URLs")
        print("3. Exit")
        choice = input("Enter your choice (1, 2, or 3): ").strip()

        results = []  # Store results for the current operation

        if choice == '1':
            account_username = input("Enter the Instagram account username (e.g., 'instagram'): ").strip()
            if not account_username:
                print("Account username cannot be empty.")
                continue
            account_reels_url = f"https://www.instagram.com/{account_username}/reels/"

            reel_urls = get_reel_links_from_account_page(account_reels_url)
            if not reel_urls:
                print(f"No Reel URLs found for account: {account_username} using the basic method.")
                print("You might need to provide specific Reel URLs using Option 2 for reliable results.")
                continue

            print(f"\n--- Processing {len(reel_urls)} Reel(s) for '{account_username}' ---")
            for i, url in enumerate(reel_urls):
                if i > 0: time.sleep(REQUEST_DELAY)
                caption_data = get_reel_caption_with_fallbacks(url, ytdlp_globally_available)

                current_caption = None
                if caption_data == "YT-DLP_NOT_FOUND_MARKER":
                    ytdlp_globally_available = False  # Mark as unavailable for subsequent calls
                    print("  yt-dlp marked as not found. Disabling for the rest of this session.")
                elif caption_data:
                    current_caption = caption_data

                results.append({'url': url, 'caption': current_caption})
                print(f"Reel {i + 1}/{len(reel_urls)} ({url}):")
                if current_caption:
                    print(f"Caption:\n{current_caption}\n")
                else:
                    print("Caption: Not found or failed to extract.\n")
                print("-" * 30)

        elif choice == '2':
            urls_input = input(
                "Enter Instagram Reel URLs separated by commas (or one per line, then press Enter twice):\n")
            raw_urls = []
            if ',' in urls_input:  # Comma-separated
                raw_urls = [url.strip() for url in urls_input.split(',') if url.strip()]
            else:  # Potentially multi-line input
                if urls_input.strip():  # Add first line if not empty
                    raw_urls.append(urls_input.strip())
                print("(Enter more URLs, one per line. Press Enter on an empty line to finish.)")
                while True:
                    line = input()
                    if not line.strip():
                        break
                    raw_urls.append(line.strip())

            reel_urls = [url for url in raw_urls if url.startswith('http') and 'instagram.com/reel/' in url]

            if not reel_urls:
                print("No valid Instagram Reel URLs provided. URLs should start with 'http' and contain '/reel/'.")
                continue

            print(f"\n--- Processing {len(reel_urls)} Provided Reel URL(s) ---")
            for i, url in enumerate(reel_urls):
                if i > 0: time.sleep(REQUEST_DELAY)
                caption_data = get_reel_caption_with_fallbacks(url, ytdlp_globally_available)

                current_caption = None
                if caption_data == "YT-DLP_NOT_FOUND_MARKER":
                    ytdlp_globally_available = False
                    print("  yt-dlp marked as not found. Disabling for the rest of this session.")
                elif caption_data:
                    current_caption = caption_data

                results.append({'url': url, 'caption': current_caption})
                print(f"Reel {i + 1}/{len(reel_urls)} ({url}):")
                if current_caption:
                    print(f"Caption:\n{current_caption}\n")
                else:
                    print("Caption: Not found or failed to extract.\n")
                print("-" * 30)

        elif choice == '3':
            print("Exiting program.")
            break
        else:
            print("Invalid choice. Please enter 1, 2, or 3.")

        if results:
            print("\n--- Summary of Results for this Operation ---")
            found_count = 0
            for res in results:
                status = "Found" if res['caption'] else "Not Found"
                if res['caption']: found_count += 1
                print(f"URL: {res['url']} - Caption: {status}")
            print(f"Successfully extracted captions for {found_count}/{len(results)} Reels in this batch.")

            # Option to save results to a file
            save_choice = input("Save these results to a file? (yes/no, default no): ").strip().lower()
            if save_choice == 'yes' or save_choice == 'y':
                filename = f"reel_captions_output_{time.strftime('%Y%m%d_%H%M%S')}.txt"
                try:
                    with open(filename, "w", encoding="utf-8") as f:
                        for res in results:
                            f.write(f"URL: {res['url']}\n")
                            f.write(
                                f"Caption: {res['caption'] if res['caption'] else 'Not Found or Failed to Extract'}\n")
                            f.write("-" * 50 + "\n\n")
                    print(f"Results saved to {filename}")
                except IOError as e:
                    print(f"Error saving results to file: {e}")
            print("-" * 70)


if __name__ == '__main__':
    main()
