from curl_cffi import requests
import json
import random
import time
from datetime import datetime
from datetime import timedelta
import schedule
import telebot
import html
import threading
import schedule
from threading import Lock
import os
from dotenv import load_dotenv
from flask import Flask

# Load environment variables from .env file
load_dotenv()

API_TOKEN = os.getenv('TELEBOT_API_TOKEN')
bot_link = os.getenv('BOT_LINK')
CHANNEL_ID = os.getenv('CHANNEL_ID')

global selected_tokens
global messageID
global latest_market_caps
global posting_lock

posting_lock = Lock()


# Cookie and header configuration for authentication and avoiding detection
cookies = {
    '_ga': 'GA1.1.862199785.1717694499',
    'cf_clearance': 'URQoLET4BOtUomxLPXJGSZjNHWPVbGZIQDpT14oiZAg-1718466640-1.0.1.1-PVSbHxenqFQgwIQO6liOOLC0HxomMy6PcQe0bbmrm8hof.R20FlnwmPasd31RysG6LIM6FYvy2lspJwPSe2.6A',
    '__cflb': '0H28vzQ7jjUXq92cxrkXEKALtbS6AuECbgnpuJ8NjnV',
    '__cf_bm': 'eOh8CD0pFQsLivb4z6gkbS3Xfa74LdR0Xo8cOKNmfds-1718466679-1.0.1.1-XbWSEnlkJPFw0k9_KdeWF8tkA2nwlQPClkAMCrS0hzxycR24JeeAxgPEJxldyPD0qRlBJ1uFsiSnv8v4CO5Q.TlEza0KCJVMaTDX.KLFqDM',
    '_ga_532KFVB4WT': 'GS1.1.1718466640.7.1.1718466745.60.0.0',
}

headers = {
    'accept': 'application/json, text/plain, */*',
    'accept-language': 'en-GB,en-US;q=0.9,en;q=0.8',
    'cache-control': 'no-cache',
    'origin': 'https://dexscreener.com',
    'pragma': 'no-cache',
    'referer': 'https://dexscreener.com/',
    'sec-ch-ua': '"Google Chrome";v="125", "Chromium";v="125", "Not.A/Brand";v="24"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-site',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
    'upgrade-insecure-requests': '1',
}



def fetch_and_analyze_trending_tokens(output_file: str = 'filtered_trending_analysis.json'):
    """Fetches trending token data from Dexscreener, analyzes it, and filters based on the conditions"""
    try:
        # Fetch the trending tokens page
        url = "https://api.dexscreener.com/token-profiles/latest/v1"
        response = requests.get(url, cookies=cookies, headers=headers)
        
        # Parse the JSON content
        token_entries = response.json()
        
        if not isinstance(token_entries, list):
            raise ValueError("Expected token_entries to be a list, but got {}".format(type(token_entries)))
        
        # Sort the entries by chainId and tokenAddress
        token_entries = sorted(token_entries, key=lambda x: (x.get('chainId', ''), x.get('tokenAddress', '')))

        filtered_tokens = []
        
        for entry in token_entries:
            if entry.get('chainId') != 'solana':
                continue  # Skip non-Solana tokens
            
            token_name = entry.get('description', '').split('\n')[0].strip() if entry.get('description') else ''
            contract_address = entry.get('tokenAddress', '')
            
            # Extract Dexscreener link
            dexscreener_link = entry.get('url', '')
            icon = entry.get('icon', '')
            
            # Extract  links
            telegram_links = [link['url'] for link in entry.get('links', []) if link.get('type') == 'telegram']
            telegram_link = telegram_links[0] if telegram_links else None
            twitter_links = [link['url'] for link in entry.get('links', []) if link.get('type') == 'twitter']
            twitter_link = twitter_links[0] if twitter_links else None
            Website_links = [link['url'] for link in entry.get('links', []) if link.get('type') == 'Website']
            Website_link = Website_links[0] if Website_links else None

            
            # Get market cap, liquidity, and volume using Dexscreener API
            dexscreener_api_url = f"https://api.dexscreener.com/latest/dex/tokens/{contract_address}"
            dexscreener_response = requests.get(dexscreener_api_url, headers=headers)
            if dexscreener_response.status_code == 200:
                dexscreener_data = dexscreener_response.json()
                market_cap = dexscreener_data['pairs'][0].get('marketCap', 0)
                liquidity_usd = dexscreener_data['pairs'][0].get('liquidity', {}).get('usd', 0)
                h24_volume = dexscreener_data['pairs'][0].get('volume', {}).get('h24', 0)
                priceChange_h6 = dexscreener_data['pairs'][0].get('priceChange', {}).get('h6', 0)
                openGraph = dexscreener_data['pairs'][0].get('info', {}).get('openGraph', 0)
                symbol = dexscreener_data['pairs'][0].get('baseToken', {}).get('symbol', 0)
                boosts = dexscreener_data["pairs"][0].get("boosts", None)
                
                # Check if the data meets the filtering criteria
                if (market_cap >= 8000 and
                     market_cap <= 1000000 and
                    h24_volume >= 5000 and
                    liquidity_usd >= 4000 and
                    priceChange_h6 > -20 and
                    (market_cap > liquidity_usd and market_cap / liquidity_usd <= 5)):
                    
                    token_info = {
                        'name': token_name,
                        'contract_address': contract_address,
                        'dexscreener_link': dexscreener_link,
                        'telegram_link': telegram_link,
                        'twitter_link': twitter_link,
                        'Website_link': Website_link,
                        'market_cap': market_cap,
                        'liquidity_usd': liquidity_usd,
                        'h24_volume': h24_volume,
                        'openGraph' : openGraph,
                        'symbol' : symbol,
                        'boosts': boosts
                    }
                    filtered_tokens.append(token_info)
                else:
                     print(f"Token {token_name} doesn't meet the filtering criteria.")
            else:
                print(f"Failed to get data for {token_name}. Status code: {dexscreener_response.status_code}")
        
        # Save the filtered data to a JSON file
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(filtered_tokens, f, indent=4)
        
        print(f"Filtered token analysis successfully written to {output_file}")
    
    except Exception as e:
        print(f"An error occurred: {e}")

# Initialize the bot
bot = telebot.TeleBot(API_TOKEN)

# # Global variables to store selected tokens and their market caps
selected_tokens = []
first_market_caps = {}
latest_market_caps = {}

def select_random_token_with_telegram_link():
    """Selects a random token from the filtered tokens list and returns it"""
    with open('filtered_trending_analysis.json', 'r') as f:
        tokens = json.load(f)
    
    # Filter tokens that have a Telegram link
    tokens_with_telegram = [token for token in tokens if token.get('telegram_link')]
    
    if tokens_with_telegram:
        return random.choice(tokens_with_telegram)
    return None

def post_token_on_telegram_bot(token):
    chat_id = CHANNEL_ID
    openGraph = token.get('openGraph', None)
    boosts = token.get('boosts')

    symbol_link = f"<a href='{html.escape(token['dexscreener_link'])}'>{token['symbol']}</a>"
    fomo_link = f"<a href='{html.escape(bot_link)}'>FOMO Trending</a>"
    snipe = "<a href='https://t.me/GMGN_sol04_bot?start'>GMGN</a>"
    message = (
        f"{symbol_link} is on {fomo_link}\n\n"
        f"CA: <code>{token['contract_address']}</code>\n\n"
        f"Market Cap: ${token['market_cap']:,.2f}\n\n"
        f"Liquidity: ${token['liquidity_usd']:,.2f}\n\n\n"
        f"🔒 Lock in your snipes with {snipe} on Telegram!\n\n"
    )
    if token.get('Website_link'):
        website_link = f"<a href='{html.escape(token['Website_link'])}'>Website</a>"
        message += f"{website_link}\n\n"
    if token.get('twitter_link'):
        twitter_link = f"<a href='{html.escape(token['twitter_link'])}'>Twitter</a>"
        message += f"{twitter_link}\n\n"
    if token.get('telegram_link'):
        telegram_link = f"<a href='{html.escape(token['telegram_link'])}'>Telegram</a>"
        message += f"{telegram_link}\n\n"
    if token.get('boosts'):
        message += f"Dexscreener Paid:✅\n\n"

    gmgn_link = f"https://gmgn.ai/sol/token/{token['contract_address']}?chain=sol"

    markup = telebot.types.InlineKeyboardMarkup()
    markup.row_width = 2
    markup.add(telebot.types.InlineKeyboardButton("Dexscreener", url=token['dexscreener_link']),
               telebot.types.InlineKeyboardButton("GMGN", url=gmgn_link))

    if openGraph:
        # Send the image along with the message
        sent_message = bot.send_photo(chat_id, openGraph, caption=message, reply_markup=markup, parse_mode="HTML")
    else:
        # Send only the message
        sent_message = bot.send_message(chat_id, message, reply_markup=markup, parse_mode="HTML")
    
    # Return the message ID of the sent message
    return sent_message.message_id


def post_market_cap_update_on_telegram(token, new_market_cap, increase_percentage, reply_to_message_id):
    chat_id = CHANNEL_ID
    message = (
        f"Update for {token['symbol']}:\n"
        f"Market Cap: ${new_market_cap:,.2f}\n"
        f"Increase: {increase_percentage:.2f}%"
    )
    gmgn_link = f"https://gmgn.ai/sol/token/{token['contract_address']}?chain=sol"

    markup = telebot.types.InlineKeyboardMarkup()
    markup.row_width = 2
    markup.add(telebot.types.InlineKeyboardButton("Dexscreener", url=token['dexscreener_link']),
               telebot.types.InlineKeyboardButton("GMGN", url=gmgn_link))

    # Send the update as a reply to the original message
    bot.send_message(chat_id, message, reply_to_message_id=reply_to_message_id, reply_markup=markup)

def check_and_post_market_cap_increase(selected_token):
    """Checks the market cap increase for the selected token, posts if it exceeds 15%"""
    global selected_tokens, first_market_caps, latest_market_caps, messageID

    if selected_token:
        dexscreener_api_url = f"https://api.dexscreener.com/latest/dex/tokens/{selected_token['contract_address']}"
        dexscreener_response = requests.get(dexscreener_api_url, headers={'Accept': 'application/json'})
        
        if dexscreener_response.status_code == 200:
            dexscreener_data = dexscreener_response.json()
            new_market_cap = dexscreener_data['pairs'][0].get('marketCap', 0)
            
            if selected_token['name'] not in first_market_caps:
                first_market_caps[selected_token['name']] = new_market_cap
            increase_percentage = ((new_market_cap - first_market_caps[selected_token['name']]) / first_market_caps[selected_token['name']]) * 100  
            if increase_percentage >= 15: 
                if (new_market_cap * 10)  > (first_market_caps[selected_token['name']] + (latest_market_caps[selected_token['name']] *10)):
                    latest_market_caps[selected_token['name']] = new_market_cap
                    post_market_cap_update_on_telegram(selected_token, latest_market_caps[selected_token['name']], increase_percentage, messageID)

   
            elif increase_percentage <= -30:
                print(f"Market cap decrease is within -30%. Stopping checks for {selected_token['name']}.")
                selected_tokens.remove(selected_token)
                return
            else:
                print(f"No significant market cap change for {selected_token['name']}.")
        else:
            print(f"Failed to fetch data for {selected_token['name']}.")


def schedule_random_post():
    global messageID
    while True:
        with posting_lock:
            # Fetch and analyze trending tokens
            fetch_and_analyze_trending_tokens()

            # Select a random token
            selected_token = select_random_token_with_telegram_link()
            token_exists = any(token['contract_address'] == selected_token['contract_address'] for token in selected_tokens)
            if token_exists:
                selected_token = select_random_token_with_telegram_link()
                print("Token already choosen!")
            elif selected_token:
                messageID = post_token_on_telegram_bot(selected_token)
                print(f"Scheduled token post for: {selected_token['name']}")
                
                # Add the selected token to the list of selected tokens
                latest_market_caps[selected_token['name']] = 0
                selected_tokens.append(selected_token)

                
                # Schedule market cap checks for the selected token every 5 minutes
                schedule.every(5).minutes.do(check_and_post_market_cap_increase, selected_token)
        
        # Wait for a random time between 1 and 6 hours
        random_time = random.randint(3600, 21600)  # Convert hours to seconds
        time.sleep(random_time)

# Start the random post scheduler in a daemon thread
random_post_thread = threading.Thread(target=schedule_random_post)
random_post_thread.daemon = True
random_post_thread.start()

# Main loop to run pending scheduled tasks
while True:
    schedule.run_pending()
    time.sleep(1)


app = Flask(__name__)
@app.route('/')
def home():
    return "Hello, Render"

if __name__ == "__main__":
    # Start the main program
    port = int(os.environ.get("PORT", 8000))
    # Start the Flask app
    app.run(host="0.0.0.0", port=port)
