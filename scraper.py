import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.edge.options import Options as EdgeOptions
from webdriver_manager.microsoft import EdgeChromiumDriverManager
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import datetime
import os
import random

# --- Configuration ---
ACCOUNTS_FILE = 'accounts.csv'
PROXY_FILE = 'proxylist.csv'

# --- Functions ---

def login_to_twitter(driver, email, username, password):
    """Handles the login process for Twitter. Returns True on success, False on failure."""
    try:
        print(f"Attempting login with email: {email}")
        driver.get("https://twitter.com/login")
        wait = WebDriverWait(driver, 15)
        time.sleep(random.uniform(1.0, 2.5)) # Small delay after page load

        # --- Step 1: Enter Email/Username ---
        try:
            email_input = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "input[name='text']")))
            time.sleep(random.uniform(0.5, 1.2))
            email_input.send_keys(email)
            time.sleep(random.uniform(0.3, 0.8))
            next_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[.//span[text()='Next']]")))
            time.sleep(random.uniform(0.2, 0.6))
            next_button.click()
            print("Email/Username entered and 'Next' clicked.")
            time.sleep(random.uniform(1.5, 2.8)) # Wait for potential next step
        except TimeoutException:
            print("Error: Timeout waiting for email/username input field or 'Next' button.")
            return False
        except Exception as e:
            print(f"Error entering email/username or clicking 'Next': {e}")
            return False

        # --- Step 2: Handle Potential Username/Phone Verification ---
        try:
            username_input = WebDriverWait(driver, 5).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, "input[name='text'][type='text']"))
            )
            prompt_label = driver.find_element(By.XPATH, "//label[.//input[@name='text']]//span[contains(text(),'Phone, email, or username') or contains(text(),'username')]")
            print("Username/Phone verification step detected.")
            input_value = username if username and username.strip() else email
            print(f"Entering verification value: {input_value}")
            time.sleep(random.uniform(0.5, 1.2))
            username_input.send_keys(input_value)
            time.sleep(random.uniform(0.3, 0.8))
            next_button_verify = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[.//span[text()='Next']]")))
            time.sleep(random.uniform(0.2, 0.6))
            next_button_verify.click()
            print("Verification value entered and 'Next' clicked.")
            time.sleep(random.uniform(1.5, 2.8)) # Wait for password field

        except (TimeoutException, NoSuchElementException):
            print("Username/Phone verification step not detected, proceeding to password.")
            pass
        except Exception as e:
            print(f"Warning: Error during optional username/phone verification step: {e}")
            pass

        # --- Step 3: Enter Password ---
        try:
            password_input = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "input[name='password']")))
            time.sleep(random.uniform(0.5, 1.2))
            password_input.send_keys(password)
            time.sleep(random.uniform(0.3, 0.8))
            login_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[.//span[text()='Log in']]")))
            time.sleep(random.uniform(0.2, 0.6))
            login_button.click()
            print("Password entered and 'Log in' clicked.")
        except TimeoutException:
            print("Error: Timeout waiting for password input field or 'Log in' button.")
            return False
        except Exception as e:
            print(f"Error entering password or clicking 'Log in': {e}")
            return False

        # --- Step 4: Verify Login Success (Wait for Timeline) OR Handle CAPTCHA ---
        try:
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-testid='primaryColumn']"))
            )
            print(f"Login successful for {email}. Timeline verified.")
            return True
        except TimeoutException:
            print("-" * 30)
            print(f"!! Login confirmation failed for {email} (Timeline not found). !!")
            print("!! This might be due to a CAPTCHA or other verification step. !!")
            print("!! If the CAPTCHA keeps reappearing after you solve it, Twitter might be detecting automation. !!")
            print("!! In that case, this account/proxy might not work. Try solving it one more time. !!")
            print("!! Please check the browser window MANUALLY. !!")
            input(">> Press ENTER here in the terminal AFTER you have manually solved any CAPTCHA or completed verification steps in the browser... <<")
            print("Resuming script, checking for timeline again...")
            print("-" * 30)
            time.sleep(3)

            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-testid='primaryColumn']"))
                )
                print(f"Login successful for {email} after manual intervention.")
                return True
            except TimeoutException:
                print(f"Login STILL failed for {email} after manual intervention. Timeline not found.")
                try:
                    error_message = driver.find_element(By.CSS_SELECTOR, "[data-testid='error-detail'], [role='alert']").text
                    print(f"Detected error message on page: {error_message}")
                except NoSuchElementException:
                    print("No specific error message detected on page after manual intervention.")
                return False

    except Exception as e:
        print(f"An unexpected error occurred during the login process for {email}: {e}")
        return False

def build_search_url(query, start_date, end_date, mode, search_type='latest'):
    """Builds the Twitter search URL."""
    base_url = "https://twitter.com/search?q="
    query_parts = []

    if mode == 'hashtag':
        query_parts.append(f"%23{query}")
    elif mode == 'user':
        query_parts.append(f"from%3A{query}")
    else:
        import urllib.parse
        query_parts.append(urllib.parse.quote(query))

    if start_date:
        query_parts.append(f"since%3A{start_date.strftime('%Y-%m-%d')}")
    if end_date:
        end_date_inclusive = end_date + datetime.timedelta(days=1)
        query_parts.append(f"until%3A{end_date_inclusive.strftime('%Y-%m-%d')}")

    search_query = "%20".join(query_parts)

    if search_type.lower() == 'latest':
        full_url = f"{base_url}{search_query}&src=typed_query&f=live"
    else:
        full_url = f"{base_url}{search_query}&src=typed_query"

    print(f"Constructed Search URL: {full_url}")
    return full_url

def scrape_tweets(driver, search_url, max_tweets=100, scroll_pause_base=3, scroll_pause_max=6, long_pause_min_sec=300, long_pause_max_sec=720):
    """Navigates to the search URL and scrapes tweets with rate limit handling."""
    driver.get(search_url)
    try:
        # Wait for the first batch of tweets to appear
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "article[data-testid='tweet']"))
        )
        print("Search results page loaded.")
    except TimeoutException:
        print("Error: Timed out waiting for initial tweets to load. Check search URL or selectors.")
        return [] # Return empty list if no tweets load initially

    tweets_data = []
    last_height = driver.execute_script("return document.body.scrollHeight")
    tweets_gathered = 0
    consecutive_scroll_failures = 0
    max_consecutive_failures = 5 # Increased threshold slightly

    while tweets_gathered < max_tweets:
        new_tweets_found_in_pass = 0 # Reset for each pass
        try:
            # --- Extract Tweets ---
            tweet_elements = driver.find_elements(By.CSS_SELECTOR, "article[data-testid='tweet']")
            processed_ids_in_pass = set() # Track IDs processed in this specific scroll pass

            for tweet in reversed(tweet_elements): # Process from bottom up, might help get newer ones first
                if tweets_gathered >= max_tweets:
                    break
                try:
                    # Use more robust way to get timestamp and user handle to create a unique ID
                    timestamp_element = tweet.find_element(By.CSS_SELECTOR, "time")
                    timestamp_str = timestamp_element.get_attribute('datetime')
                    user_handle_elements = tweet.find_elements(By.CSS_SELECTOR, "a[href*='/status/'] div[dir='ltr'] > span") # Find handle within link
                    user_handle = "unknown_user"
                    for handle_elem in user_handle_elements:
                        if handle_elem.text.startswith('@'):
                            user_handle = handle_elem.text
                            break

                    tweet_id = f"{user_handle}_{timestamp_str}" # Create a more reliable unique ID

                    # Avoid reprocessing the same element multiple times within one scroll pass
                    if tweet_id in processed_ids_in_pass:
                        continue
                    processed_ids_in_pass.add(tweet_id)

                    # Check if tweet already collected (using the reliable ID)
                    if tweet_id not in {t['id'] for t in tweets_data}:
                        tweet_text_element = tweet.find_element(By.CSS_SELECTOR, "div[data-testid='tweetText']")
                        tweet_text_raw = tweet_text_element.text
                        tweet_text = ' '.join(tweet_text_raw.split()) # Clean whitespace

                        tweet_info = {
                            'id': tweet_id, # Keep ID for duplicate check
                            'user': user_handle,
                            'timestamp': timestamp_str,
                            'text': tweet_text
                        }
                        tweets_data.append(tweet_info)
                        tweets_gathered += 1
                        new_tweets_found_in_pass += 1

                except NoSuchElementException:
                    pass
                except Exception as e:
                    print(f"Error parsing a tweet element: {e}")

            print(f"Pass complete. Gathered {new_tweets_found_in_pass} new tweets. Total: {tweets_gathered}/{max_tweets}")

            if tweets_gathered >= max_tweets:
                print("Reached max_tweets limit.")
                break

            # Reset failure counter if new tweets were found in this pass
            if new_tweets_found_in_pass > 0:
                consecutive_scroll_failures = 0

        except Exception as e:
            print(f"Error finding or processing tweet elements on page: {e}")
            consecutive_scroll_failures += 1 # Count this as a failure
            time.sleep(random.uniform(scroll_pause_base, scroll_pause_max)) # Wait even if error

        # --- Scroll ---
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        scroll_pause = random.uniform(scroll_pause_base, scroll_pause_max) # Random pause between scrolls
        time.sleep(scroll_pause)

        new_height = driver.execute_script("return document.body.scrollHeight")

        # --- Check if Scroll Worked / Handle Rate Limit ---
        if new_height == last_height:
            if new_tweets_found_in_pass == 0:
                consecutive_scroll_failures += 1
                print(f"Scroll height unchanged AND no new tweets found. Failure count: {consecutive_scroll_failures}/{max_consecutive_failures}")

                if consecutive_scroll_failures >= max_consecutive_failures:
                    print("--- RATE LIMIT SUSPECTED or END OF RESULTS ---")
                    long_pause_duration = random.uniform(long_pause_min_sec, long_pause_max_sec)
                    print(f"Pausing for {long_pause_duration / 60:.1f} minutes before retrying...")
                    time.sleep(long_pause_duration)
                    print("Resuming scroll attempts...")
                    consecutive_scroll_failures = 0 # Reset counter after long pause
                else:
                    time.sleep(random.uniform(scroll_pause_base * 1.5, scroll_pause_max * 1.5))
            else:
                 print("Scroll height unchanged, but new tweets were found in last pass. Continuing...")
        else:
            last_height = new_height

    for tweet in tweets_data:
        if 'id' in tweet:
            del tweet['id']

    print(f"Scraping finished. Returning {len(tweets_data)} tweets.")
    return tweets_data[:max_tweets] # Ensure we don't return more than requested

def filter_by_date(tweets, start_date, end_date):
    """Filters tweets based on the date range (inclusive)."""
    filtered_tweets = []
    start_dt = datetime.datetime.combine(start_date, datetime.datetime.min.time()).replace(tzinfo=datetime.timezone.utc) if start_date else None
    end_dt = datetime.datetime.combine(end_date, datetime.datetime.max.time()).replace(tzinfo=datetime.timezone.utc) if end_date else None

    for tweet in tweets:
        try:
            if not tweet.get('timestamp'):
                print(f"Skipping tweet with missing timestamp: {tweet.get('user')}")
                continue

            tweet_dt = datetime.datetime.fromisoformat(tweet['timestamp'].replace('Z', '+00:00'))

            in_range = True
            if start_dt and tweet_dt < start_dt:
                in_range = False
            if end_dt and tweet_dt > end_dt:
                in_range = False

            if in_range:
                filtered_tweets.append(tweet)
        except ValueError:
            print(f"Could not parse timestamp '{tweet['timestamp']}' for filtering (ValueError). Skipping tweet.")
        except Exception as e:
            print(f"Could not parse timestamp '{tweet['timestamp']}' for filtering: {e}. Skipping tweet.")

    return filtered_tweets

# --- Main Execution ---
if __name__ == "__main__":
    print("Twitter Scraper")
    print("---------------")

    # --- Proxy Setup ---
    use_proxy = input("Use proxy? (y/n): ").lower()
    selected_proxy = None
    if use_proxy == 'y':
        try:
            proxy_df = pd.read_csv(PROXY_FILE, delimiter=';')
            http_proxies = proxy_df[proxy_df['http'] == 1]
            if not http_proxies.empty:
                random_proxy = http_proxies.sample(n=1).iloc[0]
                proxy_ip = random_proxy['ip']
                proxy_port = random_proxy['port']
                selected_proxy = f"{proxy_ip}:{proxy_port}"
                print(f"Using proxy: {selected_proxy}")
            else:
                print(f"Warning: No valid HTTP proxies found in {PROXY_FILE}. Proceeding without proxy.")
        except FileNotFoundError:
            print(f"Warning: Proxy file not found at {PROXY_FILE}. Proceeding without proxy.")
        except KeyError as e:
            print(f"Warning: Column {e} not found in {PROXY_FILE}. Check CSV format (ip;port;http). Proceeding without proxy.")
        except Exception as e:
            print(f"Warning: Error reading or processing proxy file {PROXY_FILE}: {e}. Proceeding without proxy.")
    else:
        print("Proceeding without proxy.")
    # --- End Proxy Setup ---

    try:
        accounts_df = pd.read_csv(ACCOUNTS_FILE)
        accounts_df['username'] = accounts_df['username'].fillna('')
        accounts = accounts_df.to_dict('records')
        if not accounts:
            print(f"Error: No accounts found in {ACCOUNTS_FILE}. Please check the file.")
            exit()
        print(f"Loaded {len(accounts)} accounts from {ACCOUNTS_FILE}.")
    except FileNotFoundError:
        print(f"Error: Accounts file not found at {ACCOUNTS_FILE}")
        print("Please create an accounts.csv file with columns: email,username,password")
        exit()
    except Exception as e:
        print(f"Error reading accounts file {ACCOUNTS_FILE}: {e}")
        exit()

    mode = input("Select mode (hashtag, message, user): ").lower()
    while mode not in ['hashtag', 'message', 'user']:
        print("Invalid mode.")
        mode = input("Select mode (hashtag, message, user): ").lower()

    query = input(f"Enter the {mode} to search for: ")

    search_type = 'latest'
    if mode in ['hashtag', 'message']:
        search_type_input = input("Search for 'Top' or 'Latest' tweets? (Default: Latest): ").lower()
        if search_type_input == 'top':
            search_type = 'top'

    while True:
        try:
            start_date_str = input("Enter start date (YYYY-MM-DD, leave blank if none): ")
            start_date = datetime.datetime.strptime(start_date_str, '%Y-%m-%d').date() if start_date_str else None
            break
        except ValueError:
            print("Invalid date format. Please use YYYY-MM-DD.")

    while True:
        try:
            end_date_str = input("Enter end date (YYYY-MM-DD, leave blank if none): ")
            end_date = datetime.datetime.strptime(end_date_str, '%Y-%m-%d').date() if end_date_str else None
            if start_date and end_date and end_date < start_date:
                print("End date cannot be before start date.")
                continue
            break
        except ValueError:
            print("Invalid date format. Please use YYYY-MM-DD.")

    max_tweets_str = input("Enter maximum number of tweets to scrape (e.g., 100): ")
    try:
        max_tweets = int(max_tweets_str)
    except ValueError:
        print("Invalid number, defaulting to 100.")
        max_tweets = 100

    driver = None
    login_successful = False
    for account in accounts:
        print("-" * 20)
        print("Initializing WebDriver (Edge)...")
        options = EdgeOptions()
        options.use_chromium = True
        # Stealth Options (Keep existing and add more)
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_argument("--incognito")
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
        options.add_argument("--lang=en-US") # Set language
        options.add_argument("--disable-infobars") # Disable "Chrome is being controlled..." bar
        options.add_argument("--start-maximized") # Start maximized
        options.add_argument("--disable-extensions") # Disable extensions
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu') # Sometimes helps with stability/detection

        if selected_proxy:
            options.add_argument(f'--proxy-server={selected_proxy}')
            print(f"WebDriver configured to use proxy: {selected_proxy}")

        try:
            service = EdgeService(EdgeChromiumDriverManager().install())
            driver = webdriver.Edge(service=service, options=options)
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            print("WebDriver (Edge) initialized with enhanced options.")

            # --- NUOVO RITARDO INIZIALE ---
            initial_delay = random.uniform(5, 10) # Attendi tra 5 e 10 secondi
            print(f"Waiting for {initial_delay:.1f} seconds before loading login page...")
            time.sleep(initial_delay)
            # --- FINE NUOVO RITARDO ---

            if login_to_twitter(driver, account['email'], account.get('username'), account['password']):
                login_successful = True
                logged_in_account = account['email']
                print(f"Login successful with {logged_in_account}. Proceeding to scrape...")
                break
            else:
                print(f"Login failed for {account['email']}. Possible CAPTCHA or incorrect credentials.")
                print("\n>>> ATTENZIONE: Login fallito. <<<")
                print(">>> Se è apparso un CAPTCHA, prova a risolverlo manualmente nel browser ora. <<<")
                print(">>> Lo script attenderà 60 secondi prima di chiudere questo browser e provare l'account successivo. <<<\n")
                time.sleep(60)
                print("Timeout scaduto o CAPTCHA non risolto. Provo l'account successivo...")
                if driver:
                    driver.quit()
                driver = None

        except Exception as e:
            print(f"An error occurred setting up WebDriver or during login for {account['email']}: {e}")
            if driver:
                driver.quit()
            driver = None
            continue

    if not login_successful or not driver:
        print("-" * 20)
        print("Exiting: Could not log in with any of the provided accounts.")
        exit()

    try:
        search_url = build_search_url(query, start_date, end_date, mode, search_type)
        print(f"Starting scrape for '{query}' (Type: {search_type.capitalize()})...")
        scraped_tweets = scrape_tweets(driver, search_url, max_tweets=max_tweets)
        print(f"Scraped {len(scraped_tweets)} tweets initially.")

        if start_date or end_date:
            print("Filtering tweets by precise date range...")
            final_tweets = filter_by_date(scraped_tweets, start_date, end_date)
            print(f"Filtered down to {len(final_tweets)} tweets within the specified date range.")
        else:
            final_tweets = scraped_tweets

        if final_tweets:
            df = pd.DataFrame(final_tweets)
            safe_query = "".join(c if c.isalnum() else "_" for c in query)
            output_filename = f"twitter_scrape_{mode}_{safe_query}.csv"
            df.to_csv(output_filename, index=False, encoding='utf-8-sig')
            print(f"Results saved to {output_filename}")
        else:
            print("No tweets found matching the criteria.")

    except Exception as e:
        print(f"An error occurred during scraping or saving: {e}")
    finally:
        if driver:
            print("Closing WebDriver (Edge).")
            driver.quit()

