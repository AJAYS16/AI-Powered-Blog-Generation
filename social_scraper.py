import os
import logging
import time
import re
import random
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SocialScraper:
    def __init__(self, max_tabs=3):
        """
        Initialize the social media scraper
        
        Args:
            max_tabs (int): Maximum number of browser tabs to use for parallel scraping
        """
        self.driver = None
        self.wait = None
        self.max_tabs = max_tabs
        self.tab_handles = []
        self.last_activity = {}  # Track last activity time for each tab

    def setup_driver(self):
        """Set up Chrome driver with optimized settings for scraping"""
        if self.driver is not None:
            return self.driver

        try:
            chrome_options = Options()
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--headless=new")  # Run in headless mode
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument("--disable-infobars")
            chrome_options.add_argument("--disable-notifications")
            chrome_options.add_argument("--disable-popup-blocking")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--start-maximized")
            chrome_options.add_argument("--ignore-certificate-errors")
            
            # Use common user agent to avoid detection
            chrome_options.add_argument(f"user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
            
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.wait = WebDriverWait(self.driver, 10)
            logger.info("Chrome driver initialized successfully")
            
            # Initialize tabs
            self.tab_handles = [self.driver.current_window_handle]
            for _ in range(max(0, self.max_tabs - 1)):
                self.driver.execute_script("window.open('about:blank', '_blank');")
                time.sleep(0.5)
                
            self.tab_handles = self.driver.window_handles
            logger.info(f"Initialized {len(self.tab_handles)} browser tabs")
            
            # Record initial activity timestamp
            for handle in self.tab_handles:
                self.last_activity[handle] = time.time()
                
            return self.driver
        except Exception as e:
            logger.error(f"Error setting up Chrome driver: {str(e)}")
            return None

    def get_available_tab(self):
        """Get the least recently used tab handle"""
        if not self.driver:
            self.setup_driver()
            
        # Find the least recently used tab
        handle = min(self.last_activity.items(), key=lambda x: x[1])[0]
        # Switch to the tab
        self.driver.switch_to.window(handle)
        # Update activity timestamp
        self.last_activity[handle] = time.time()
        
        return handle

    def fetch_social_content(self, topic, count=5, platforms=None):
        """
        Fetch content from social media platforms related to the topic
        
        Args:
            topic (str): The topic to search for
            count (int): Number of posts to fetch from each platform
            platforms (list): List of platforms to search ["twitter", "reddit"]
            
        Returns:
            dict: Dictionary with content from each platform
        """
        if platforms is None:
            platforms = ["twitter", "reddit"]
            
        try:
            # Set up driver if not already done
            if not self.driver:
                self.setup_driver()
            
            results = {}
            
            # Use ThreadPoolExecutor for parallel scraping
            with ThreadPoolExecutor(max_workers=len(platforms)) as executor:
                futures = []
                
                if "twitter" in platforms:
                    futures.append(executor.submit(self.fetch_tweets, topic, count))
                
                if "reddit" in platforms:
                    futures.append(executor.submit(self.fetch_reddit_posts, topic, count))
                
                # Collect results as they complete
                for i, future in enumerate(futures):
                    platform = platforms[i]
                    try:
                        results[platform] = future.result()
                        logger.info(f"Collected {len(results[platform])} posts from {platform}")
                    except Exception as e:
                        logger.error(f"Error fetching from {platform}: {str(e)}")
                        results[platform] = []
            
            # If we didn't get enough content from any platform, use mock data
            if all(len(posts) == 0 for posts in results.values()):
                logger.warning("No content found on any platform, using mock data")
                results["mock"] = self.generate_mock_content(topic, count)
                
            return results
            
        except Exception as e:
            logger.error(f"Error in fetch_social_content: {str(e)}")
            return {"mock": self.generate_mock_content(topic, count)}

    def fetch_tweets(self, query, count=5):
        """
        Fetch tweets related to the query by searching Google and finding X.com (Twitter) links
        
        Args:
            query (str): Search query
            count (int): Number of tweets to fetch
            
        Returns:
            list: List of tweet dictionaries
        """
        tweets = []
        handle = self.get_available_tab()
        
        try:
            # Format search query to specifically find recent tweets
            search_query = f"{query} site:x.com OR site:twitter.com recent"
            search_query = search_query.replace(' ', '+')
            url = f"https://www.google.com/search?q={search_query}"
            
            logger.info(f"Navigating to Google search for tweets: {url}")
            self.driver.get(url)
            
            # Wait for page to load
            time.sleep(3)
            
            # Handle cookie popups if they appear
            self._dismiss_popups()
            
            # Extract links to Twitter/X posts from Google results
            page_source = self.driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # Find all links in Google search results
            links = []
            for a in soup.find_all('a'):
                href = a.get('href', '')
                # Look for Twitter/X status links in Google search results
                if ('twitter.com/status/' in href or 'x.com/status/' in href) and '/search?' not in href:
                    # Extract the actual URL from Google's redirect URL
                    if href.startswith('/url?q='):
                        href = href.split('/url?q=')[1].split('&')[0]
                    links.append(href)
            
            logger.info(f"Found {len(links)} Twitter/X links in Google search")
            
            # Process found links (limit to count)
            for i, link in enumerate(links[:count]):
                try:
                    logger.info(f"Processing Twitter/X link: {link}")
                    
                    # Navigate to the tweet
                    self.driver.get(link)
                    time.sleep(3)  # Wait for page to load
                    
                    # Handle possible login/cookie popups
                    self._dismiss_popups()
                    
                    # Extract tweet content
                    tweet_source = self.driver.page_source
                    tweet_soup = BeautifulSoup(tweet_source, 'html.parser')
                    
                    # Find tweet author
                    author_element = tweet_soup.find('a', {'role': 'link', 'tabindex': '-1'})
                    author = author_element.text if author_element else "Unknown"
                    
                    # Find tweet text
                    # Look for the main article that contains the tweet
                    article = tweet_soup.find('article')
                    text = "No text available"
                    
                    if article:
                        # Try to find the div with language attribute (usually contains the tweet text)
                        text_element = article.find('div', {'lang': True})
                        if text_element:
                            text = text_element.text
                        else:
                            # Alternative: look for text in paragraphs in the article
                            paragraphs = article.find_all(['p', 'span'])
                            for p in paragraphs:
                                if len(p.text.strip()) > 20:  # Only consider substantial text
                                    text = p.text.strip()
                                    break
                    
                    # Extract timestamp
                    time_element = tweet_soup.find('time')
                    timestamp = time_element.get('datetime') if time_element else ""
                    
                    # Create tweet object with extracted data
                    tweets.append({
                        "platform": "twitter",
                        "author": author if author.startswith("@") else f"@{author}",
                        "text": text,
                        "date": timestamp,
                        "url": link
                    })
                    
                except Exception as e:
                    logger.error(f"Error processing tweet at {link}: {str(e)}")
                    continue
            
            logger.info(f"Successfully extracted {len(tweets)} tweets")
            return tweets
            
        except Exception as e:
            logger.error(f"Error in fetch_tweets: {str(e)}")
            return []

    def fetch_reddit_posts(self, query, count=5):
        """
        Fetch Reddit posts related to the query
        
        Args:
            query (str): Search query
            count (int): Number of posts to fetch
            
        Returns:
            list: List of Reddit post dictionaries
        """
        posts = []
        handle = self.get_available_tab()
        
        try:
            # Format search query
            search_query = query.replace(' ', '+')
            url = f"https://www.reddit.com/search/?q={search_query}&sort=new"
            
            logger.info(f"Navigating to Reddit search: {url}")
            self.driver.get(url)
            
            # Wait for page to load
            time.sleep(3)
            
            # Dismiss any popups (like cookie consent)
            self._dismiss_popups()
            
            # Scroll down to load more content
            for _ in range(min(3, count)):
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(1)
            
            # Extract posts from the page
            page_source = self.driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # Find post containers - this varies based on Reddit's current DOM structure
            # Look for post cards or similar elements
            post_elements = soup.find_all("div", {"data-testid": "post-container"})
            
            if not post_elements:
                # Try alternative selectors
                post_elements = soup.find_all("div", class_=re.compile("Post|post-container|Post__post|Post-item"))
            
            logger.info(f"Found {len(post_elements)} Reddit post elements")
            
            for i, post_element in enumerate(post_elements[:count]):
                try:
                    # Extract post title
                    title_element = post_element.find(["h1", "h2", "h3"], class_=re.compile("title|Title"))
                    title = title_element.text.strip() if title_element else "No title"
                    
                    # Extract username
                    author_element = post_element.find("a", class_=re.compile("author|AuthorLink"))
                    author = author_element.text.strip() if author_element else "Unknown"
                    
                    # Extract post URL
                    if title_element and title_element.find_parent("a"):
                        url = title_element.find_parent("a").get("href", "")
                        if url and not url.startswith("http"):
                            url = f"https://www.reddit.com{url}"
                    else:
                        url = ""
                    
                    # Extract timestamp
                    time_element = post_element.find(["time", "span"], class_=re.compile("time|Time|date|Date|ago"))
                    date_text = time_element.text.strip() if time_element else ""
                    
                    # Convert relative time to timestamp
                    timestamp = self._parse_reddit_date(date_text)
                    
                    # Extract content preview
                    content_element = post_element.find(["div", "p"], class_=re.compile("content|Content|body|Body|text-body"))
                    content = content_element.text.strip() if content_element else title
                    
                    posts.append({
                        "platform": "reddit",
                        "author": f"u/{author}" if not author.startswith("u/") else author,
                        "text": f"{title}\n\n{content[:150]}...",
                        "date": timestamp,
                        "url": url
                    })
                    
                    if len(posts) >= count:
                        break
                except Exception as e:
                    logger.error(f"Error parsing Reddit post {i+1}: {str(e)}")
                    continue
            
            return posts
        except Exception as e:
            logger.error(f"Error in fetch_reddit_posts: {str(e)}")
            return []

    def _dismiss_popups(self):
        """Attempt to dismiss common popups on social media sites"""
        try:
            # Try different strategies for dismissing popups
            # 1. Look for close buttons
            close_selectors = [
                "button[aria-label='Close']",
                "[data-testid='dialog-close-button']",
                ".close-button",
                ".modal__close",
                "[data-testid='modal-close']"
            ]
            
            for selector in close_selectors:
                try:
                    close_buttons = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if close_buttons:
                        close_buttons[0].click()
                        time.sleep(0.5)
                        return
                except:
                    continue
                    
            # 2. Look for "Not Now", "No Thanks", "I Agree", etc. buttons
            no_thanks_texts = ["Not Now", "No Thanks", "I Agree", "Accept", "Close", "Skip", "Continue"]
            for text in no_thanks_texts:
                try:
                    buttons = self.driver.find_elements(By.XPATH, 
                        f"//*[contains(text(), '{text}')]")
                    if buttons:
                        buttons[0].click()
                        time.sleep(0.5)
                        return
                except:
                    continue
                    
            # 3. Try pressing Escape key
            try:
                webdriver.ActionChains(self.driver).send_keys(Keys.ESCAPE).perform()
                time.sleep(0.5)
            except:
                pass
                
        except Exception as e:
            logger.warning(f"Error dismissing popups: {str(e)}")

    def _parse_reddit_date(self, date_text):
        """Convert Reddit relative time to timestamp"""
        now = datetime.now()
        
        if not date_text:
            return now.isoformat()
            
        try:
            # Handle common formats like "5 hours ago", "2 days ago", etc.
            time_map = {
                'second': timedelta(seconds=1),
                'minute': timedelta(minutes=1),
                'hour': timedelta(hours=1),
                'day': timedelta(days=1),
                'week': timedelta(days=7),
                'month': timedelta(days=30),
                'year': timedelta(days=365)
            }
            
            # Extract number and unit
            match = re.search(r'(\d+)\s+(\w+)', date_text)
            if match:
                num = int(match.group(1))
                unit = match.group(2).lower().rstrip('s')  # Remove plural 's'
                
                if unit in time_map:
                    delta = time_map[unit] * num
                    timestamp = (now - delta).isoformat()
                    return timestamp
            
            # If we can't parse it, return current time
            return now.isoformat()
        except:
            return now.isoformat()

    def generate_mock_content(self, topic, count):
        """
        Generate mock social media content when real content can't be fetched
        
        Args:
            topic (str): Topic to generate content about
            count (int): Number of mock posts to generate
            
        Returns:
            list: List of mock post dictionaries
        """
        mock_content = []
        
        # Popular accounts to attribute mock content to
        tech_accounts = [
            {"platform": "twitter", "handle": "@OpenAI"},
            {"platform": "twitter", "handle": "@elonmusk"},
            {"platform": "twitter", "handle": "@Microsoft"},
            {"platform": "twitter", "handle": "@Google"},
            {"platform": "twitter", "handle": "@TechCrunch"},
            {"platform": "reddit", "handle": "u/technology_mod"},
            {"platform": "reddit", "handle": "u/tech_enthusiast"},
            {"platform": "reddit", "handle": "u/AI_researcher"},
            {"platform": "reddit", "handle": "u/code_master"},
            {"platform": "reddit", "handle": "u/digital_nomad"}
        ]
        
        # Current time for timestamps
        now = datetime.now()
        
        # Clean up topic for use in templates
        clean_topic = topic.replace('#', '').replace('@', '')
        
        # Templates for different types of posts
        twitter_templates = [
            f"Just read an interesting article about {clean_topic}. The future looks promising! #Technology #Innovation",
            f"Our team has been analyzing recent developments in {clean_topic}. Stay tuned for our report next week!",
            f"The latest advancements in {clean_topic} are truly game-changing. Here's why it matters for the industry.",
            f"Just attended a fascinating talk on {clean_topic} at the conference. So many new possibilities!",
            f"Exciting news about {clean_topic} today! This could revolutionize how we think about technology."
        ]
        
        reddit_templates = [
            f"[Discussion] What do you think about the recent developments in {clean_topic}?",
            f"I've been researching {clean_topic} for my thesis and wanted to share some fascinating insights I've found.",
            f"[Analysis] Breaking down the latest advancements in {clean_topic} and what they mean for the future.",
            f"Can someone explain like I'm five: Why is {clean_topic} suddenly getting so much attention?",
            f"Just finished a deep dive into {clean_topic} and compiled my findings in this post. Thought it might help others!"
        ]
        
        # Generate mock posts
        for i in range(count):
            # Randomly decide platform for this mock post
            account = random.choice(tech_accounts)
            platform = account["platform"]
            
            # Generate content based on platform
            if platform == "twitter":
                text = random.choice(twitter_templates)
                url = f"https://twitter.com/{account['handle'][1:]}/status/{random.randint(1000000000000000000, 9999999999999999999)}"
            else:  # reddit
                title = random.choice(reddit_templates)
                text = f"{title}\n\nI've been following this topic for a while now, and the recent developments are truly remarkable. What are your thoughts on how this will impact the industry over the next few years?"
                url = f"https://www.reddit.com/r/technology/comments/{self._random_reddit_id()}/discussion_{clean_topic.replace(' ', '_')}/"
            
            # Create post with randomized timestamp (1-72 hours ago)
            hours_ago = random.randint(1, 72)
            timestamp = (now - timedelta(hours=hours_ago)).isoformat()
            
            mock_content.append({
                "platform": platform,
                "author": account["handle"],
                "text": text,
                "date": timestamp,
                "url": url
            })
        
        return mock_content

    def _random_reddit_id(self, length=6):
        """Generate a random Reddit post ID (alphanumeric string)"""
        chars = "abcdefghijklmnopqrstuvwxyz0123456789"
        return ''.join(random.choice(chars) for _ in range(length))

    def format_social_content_markdown(self, content, max_items=3):
        """
        Format social media content into Markdown for inclusion in blogs
        
        Args:
            content (dict): Dictionary with content from each platform
            max_items (int): Maximum number of items to include per platform
            
        Returns:
            str: Markdown formatted content
        """
        if not content or all(len(posts) == 0 for posts in content.values()):
            return ""
            
        markdown = "## Recent Social Media Updates\n\n"
        
        # Sort platforms to prioritize those with content
        platforms = sorted(content.keys(), key=lambda p: len(content[p]), reverse=True)
        
        for platform in platforms:
            posts = content[platform][:max_items]
            if not posts:
                continue
                
            # Add platform header
            platform_name = platform.capitalize()
            if platform == "mock":
                platform_name = "Social Media"
                
            markdown += f"### Recent {platform_name} Posts\n\n"
            
            for post in posts:
                author = post.get("author", "Unknown")
                markdown += f"**{author}**\n\n"
                
                text = post.get("text", "").replace("\n", "\n\n")
                markdown += f"{text}\n\n"
                
                # Format date if available
                date = post.get("date", "")
                if date:
                    try:
                        date_obj = datetime.fromisoformat(date.replace('Z', '+00:00'))
                        formatted_date = date_obj.strftime("%b %d, %Y")
                        markdown += f"*{formatted_date}*\n\n"
                    except:
                        markdown += f"*{date}*\n\n"
                
                # Add link to original post
                url = post.get("url", "")
                if url:
                    markdown += f"[View Original Post]({url})\n\n"
                    
                markdown += "---\n\n"
            
        return markdown

    def close(self):
        """Close the driver if it exists"""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("Browser closed successfully")
            except Exception as e:
                logger.error(f"Error closing browser: {str(e)}")

def test_social_scraper():
    """Test function for the social scraper"""
    scraper = SocialScraper(max_tabs=2)
    try:
        # Test topic
        topic = "GPT-4 AI model"
        
        print(f"Fetching social content for topic: {topic}")
        content = scraper.fetch_social_content(topic, count=3)
        
        # Display results
        for platform, posts in content.items():
            print(f"\n--- {platform.upper()} ({len(posts)} posts) ---")
            for i, post in enumerate(posts):
                print(f"\nPost {i+1}:")
                print(f"Author: {post['author']}")
                print(f"Text: {post['text'][:100]}...")
                print(f"Date: {post['date']}")
                print(f"URL: {post['url']}")
        
        # Test formatting
        print("\nFormatted as Markdown:")
        markdown = scraper.format_social_content_markdown(content, max_items=2)
        print(markdown[:500] + "...\n")
        
    finally:
        scraper.close()

if __name__ == "__main__":
    test_social_scraper() 