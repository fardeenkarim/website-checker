import csv
import requests
from bs4 import BeautifulSoup
import time
import re

def check_website(url):
    results = {
        'url': url,
        'is_wordpress': False,
        'plugin_count': 0,
        'plugin_names': "",
        'load_time_seconds': 0,
        'status': 'Error',
        'site_title': "",
        'meta_description': "",
        'theme': "",
        'copyright_year': "",
        'has_woocommerce': False,
        'has_shopify': False,
        'has_elementor': False,
        'has_beaver_builder': False,
        'has_analytics': False,
        'has_pixel': False,
        'is_https': False,
        'has_viewport': False
    }
    
    try:
        if not url.startswith('http'):
            url = 'https://' + url
            
        results['is_https'] = url.startswith('https')

        start_time = time.time()
        response = requests.get(url, timeout=10)
        end_time = time.time()
        results['load_time_seconds'] = round(end_time - start_time, 2)
        results['status'] = response.status_code

        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            html_content = response.text.lower() # Lowercase for easier searching
            
            # --- Personalization Signals ---
            # Title
            if soup.title:
                results['site_title'] = soup.title.string.strip() if soup.title.string else ""
            
            # Meta Description
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            if meta_desc and meta_desc.get('content'):
                results['meta_description'] = meta_desc['content'].strip()
            
            # Check for WordPress
            if 'wp-content' in html_content:
                results['is_wordpress'] = True
            elif soup.find('meta', attrs={'name': 'generator', 'content': re.compile(r'WordPress', re.I)}):
                results['is_wordpress'] = True
                
            # Active Theme
            # Look for /wp-content/themes/theme-name/
            theme_pattern = r'wp-content/themes/([a-z0-9_\-]+)/'
            theme_match = re.search(theme_pattern, html_content)
            if theme_match:
                results['theme'] = theme_match.group(1)
            
            # Copyright Year
            # Regex to find 4 digit years from 2000-2099 near "copyright" or "©"
            copyright_pattern = r'(?:copyright|©).*?(20\d{2})'
            copyright_match = re.search(copyright_pattern, html_content)
            if copyright_match:
                results['copyright_year'] = copyright_match.group(1)

            # --- Plugin Detection ---
            # Refined regex to match only valid directory names (alphanumeric, -, _)
            plugin_pattern = r'wp-content/plugins/([a-zA-Z0-9_\-]+)/'
            plugins = re.findall(plugin_pattern, html_content)
            unique_plugins = list(set(plugins))
            results['plugin_count'] = len(unique_plugins)
            results['plugin_names'] = ", ".join(unique_plugins)
            
            # --- High-Value Tech Detection ---
            results['has_woocommerce'] = 'woocommerce' in html_content
            results['has_shopify'] = 'shopify' in html_content
            results['has_elementor'] = 'elementor' in html_content
            results['has_beaver_builder'] = 'beaver-builder' in html_content
            results['has_analytics'] = 'googletagmanager' in html_content or 'google-analytics' in html_content
            results['has_pixel'] = 'facebook-pixel' in html_content or 'fbevents.js' in html_content
            
            # --- Technical Health ---
            # SSL is checked at start
            # Mobile Viewport
            viewport = soup.find('meta', attrs={'name': 'viewport'})
            if viewport:
                results['has_viewport'] = True

    except Exception as e:
        results['status'] = f"Error: {str(e)}"
        results['plugin_names'] = ""

    return results

def main():
    input_file = 'websites.csv'
    output_file = 'results.csv'
    BATCH_SIZE = 100
    
    print(f"Reading from {input_file}...")
    
    websites = []
    try:
        with open(input_file, 'r') as f:
            reader = csv.reader(f)
            for row in reader:
                if row:
                    websites.append(row[0].strip())
    except FileNotFoundError:
        print(f"Error: {input_file} not found.")
        return

    total_websites = len(websites)
    print(f"Found {total_websites} websites. Starting check...")

    # Initialize output file with headers
    fieldnames = [
        'url', 'status', 'load_time_seconds',
        'site_title', 'meta_description', 'copyright_year',
        'is_wordpress', 'theme', 'plugin_count', 'plugin_names',
        'has_woocommerce', 'has_shopify', 'has_elementor', 'has_beaver_builder',
        'has_analytics', 'has_pixel',
        'is_https', 'has_viewport'
    ]
    
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

    batch_results = []
    
    for index, url in enumerate(websites, 1):
        # Progress UI
        print(f"\n{'='*60}")
        print(f"Progress: [{index}/{total_websites}] ({round(index/total_websites*100, 1)}%)")
        print(f"Checking: {url}")
        print(f"{'='*60}")
        
        result = check_website(url)
        
        # Ensure all keys exist
        for key in fieldnames:
            if key not in result:
                result[key] = ""
        
        batch_results.append(result)
        
        # Detailed output
        print(f"  Title:    {result['site_title'][:50]}..." if len(result['site_title']) > 50 else f"  Title:    {result['site_title']}")
        print(f"  WP:       {result['is_wordpress']}")
        print(f"  Theme:    {result['theme']}")
        print(f"  Plugins:  {result['plugin_count']} ({result['plugin_names'][:60]}...)")
        print(f"  Tech:     Woo: {'YES' if result['has_woocommerce'] else 'No'} | Shop: {'YES' if result['has_shopify'] else 'No'} | GA: {'YES' if result['has_analytics'] else 'No'} | Pixel: {'YES' if result['has_pixel'] else 'No'}")
        print(f"  Health:   HTTPS: {'YES' if result['is_https'] else 'No'} | Mobile: {'YES' if result['has_viewport'] else 'No'} | Time: {result['load_time_seconds']}s")

        # Batch Save
        if len(batch_results) >= BATCH_SIZE or index == total_websites:
            print(f"\n[Saving Batch of {len(batch_results)} results to {output_file} ...]")
            with open(output_file, 'a', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                for res in batch_results:
                    writer.writerow(res)
            batch_results = [] # Clear batch

    print(f"\n{'='*60}")
    print(f"DONE! All {total_websites} websites checked.")
    print(f"Results saved to {output_file}")
    print(f"{'='*60}")

if __name__ == '__main__':
    main()
