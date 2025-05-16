import requests
import json
import os
import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
from dotenv import load_dotenv
import time
import random
from bs4 import BeautifulSoup
from pathlib import Path
import docx
from selenium.webdriver.common.keys import Keys

# Load environment variables and setup logging
load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SocialMediaPoster:
    def __init__(self):
        """Initialize the social media poster with API tokens and credentials"""
        # Medium credentials and tokens
        self.medium_token = os.getenv('MEDIUM_TOKEN')
        
        # LinkedIn credentials
        self.linkedin_email = os.getenv('LINKEDIN_EMAIL')
        self.linkedin_password = os.getenv('LINKEDIN_PASSWORD')
        
        # Setup Selenium driver
        self.driver = None
    
    def setup_driver(self):
        """Setup Chrome driver with appropriate settings"""
        if self.driver is not None:
            return
            
        try:
            chrome_options = Options()
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument("--disable-infobars")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--start-maximized")
            
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.wait = WebDriverWait(self.driver, 15)
            logger.info("Chrome driver initialized successfully")
            
            # Add longer initial wait time after browser launch
            time.sleep(random.uniform(3, 5))
            
        except Exception as e:
            logger.error(f"Error setting up Chrome driver: {str(e)}")
            raise
    
    def post_to_medium(self, title, content, tags=None, publish_status="draft"):
        """
        Post content to Medium using the Medium API or Selenium if token not available
        
        Args:
            title (str): The title of the blog post
            content (str): The HTML content of the blog post
            tags (list): List of tags to associate with the post
            publish_status (str): 'public', 'draft', or 'unlisted'
            
        Returns:
            dict: Response from Medium API or error information
        """
        # If token is available, use API method
        if self.medium_token:
            try:
                # Prepare the request
                url = "https://api.medium.com/v1/users/me/posts"
                headers = {
                    "Authorization": f"Bearer {self.medium_token}",
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                }
                
                # Format tags correctly
                tags_list = tags if tags else []
                if isinstance(tags, str):
                    tags_list = [tag.strip() for tag in tags.split(",")]
                
                data = {
                    "title": title,
                    "contentFormat": "html",
                    "content": content,
                    "tags": tags_list,
                    "publishStatus": publish_status
                }
                
                # Send the request
                response = requests.post(url, headers=headers, data=json.dumps(data))
                
                if response.status_code in (200, 201):
                    result = response.json()
                    logger.info(f"Successfully posted to Medium with ID: {result.get('data', {}).get('id')}")
                    return {"success": True, "data": result.get('data', {})}
                else:
                    logger.error(f"Failed to post to Medium: {response.status_code} - {response.text}")
                    return {"success": False, "error": f"API Error: {response.status_code}", "details": response.text}
                    
            except Exception as e:
                logger.error(f"Error posting to Medium via API: {str(e)}")
                # Fall back to Selenium method
                logger.info("Falling back to Selenium method for Medium posting")
                return self.post_to_medium_with_selenium(title, content, tags, publish_status)
        else:
            # No token, use Selenium method
            logger.info("No Medium API token found, using Selenium method")
            return self.post_to_medium_with_selenium(title, content, tags, publish_status)
    
    def post_to_medium_with_selenium(self, title, content, tags=None, publish_status="draft"):
        """
        Post content to Medium using Selenium automation with Google login
        
        Args:
            title (str): The title of the blog post
            content (str): The HTML or text content of the blog post
            tags (list): List of tags to associate with the post
            publish_status (str): 'public', 'draft', or 'unlisted'
            
        Returns:
            dict: Status information about the posting attempt
        """
        # Get Google credentials from environment
        google_email = os.getenv('GOOGLE_EMAIL')
        google_password = os.getenv('GOOGLE_PASSWORD')
        
        if not google_email or not google_password:
            logger.error("Google credentials not found in environment variables")
            return {"success": False, "error": "Google credentials not configured for Medium login"}
        
        try:
            # Setup the driver if not already done
            if not self.driver:
                self.setup_driver()
            
            # Navigate to Medium
            logger.info("Navigating to Medium")
            self.driver.get("https://medium.com/")
            time.sleep(3)
            
            # Click the "Sign in" button in the top right
            try:
                sign_in_btn = self.wait.until(EC.element_to_be_clickable(
                    (By.XPATH, "//a[text()='Sign in']")
                ))
                sign_in_btn.click()
                time.sleep(2)
            except Exception as e:
                logger.warning(f"Could not find 'Sign in' button: {str(e)}")
                # Try alternative selector
                try:
                    sign_in_btns = self.driver.find_elements(By.CSS_SELECTOR, "a[href*='signin']")
                    if sign_in_btns:
                        sign_in_btns[0].click()
                        time.sleep(2)
                except:
                    logger.error("Could not find any sign in button")
                    return {"success": False, "error": "Could not find sign in button on Medium"}
            
            # Find and click on "Continue with Google" button
            try:
                google_btn = self.wait.until(EC.element_to_be_clickable(
                    (By.XPATH, "//button[contains(., 'Sign in with Google')]")
                ))
                google_btn.click()
                time.sleep(3)
            except Exception as e:
                logger.warning(f"Could not find 'Sign in with Google' button: {str(e)}")
                # Try alternative selectors for Google sign in
                try:
                    # Try the first button which is typically Google
                    google_btns = self.driver.find_elements(By.CSS_SELECTOR, 
                        "button img[alt*='Google'], button[aria-label*='Google'], [role='button']:has-text('Google'), button:nth-child(1)")
                    if google_btns:
                        google_btns[0].click()
                        time.sleep(3)
                    else:
                        # Try finding by image with Google logo
                        google_imgs = self.driver.find_elements(By.CSS_SELECTOR, "img[src*='google'], img[alt*='Google']")
                        if google_imgs:
                            parent = google_imgs[0]
                            # Navigate up to find the clickable button
                            for _ in range(3):  # Try up to 3 levels up
                                try:
                                    parent = parent.find_element(By.XPATH, "./..")
                                    if parent.tag_name == 'button' or parent.get_attribute('role') == 'button':
                                        parent.click()
                                        time.sleep(3)
                                        break
                                except:
                                    break
                        else:
                            # Last resort - try clicking the first button on the page
                            first_buttons = self.driver.find_elements(By.CSS_SELECTOR, "button, [role='button']")
                            if first_buttons:
                                first_buttons[0].click()
                                time.sleep(3)
                            else:
                                raise Exception("No Google login button found")
                except Exception as e:
                    logger.error(f"Could not find Google login button: {str(e)}")
                    return {"success": False, "error": "Could not find Google login button"}
            
            # Switch to Google login popup window
            main_window = self.driver.current_window_handle
            popup_found = False
            for handle in self.driver.window_handles:
                if handle != main_window:
                    self.driver.switch_to.window(handle)
                    popup_found = True
                    break
            
            if not popup_found:
                logger.warning("No Google login popup found, continuing in main window")
            
            # Enter Google email
            logger.info("Entering Google email")
            try:
                email_input = self.wait.until(EC.presence_of_element_located((By.ID, "identifierId")))
                email_input.send_keys(google_email)
                email_input.send_keys(Keys.RETURN)
                time.sleep(3)
            except Exception as e:
                logger.error(f"Error entering Google email: {str(e)}")
                # Try alternative selectors for email input
                try:
                    email_inputs = self.driver.find_elements(By.CSS_SELECTOR, "input[type='email']")
                    if email_inputs:
                        email_inputs[0].clear()
                        email_inputs[0].send_keys(google_email)
                        email_inputs[0].send_keys(Keys.RETURN)
                        time.sleep(3)
                    else:
                        raise Exception("No email input field found")
                except Exception as e:
                    logger.error(f"Could not enter Google email: {str(e)}")
                    return {"success": False, "error": "Could not enter Google email"}
            
            # Enter Google password
            logger.info("Entering Google password")
            try:
                password_input = self.wait.until(EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "input[type='password'][name='password']")
                ))
                password_input.send_keys(google_password)
                password_input.send_keys(Keys.RETURN)
                time.sleep(5)
            except Exception as e:
                logger.error(f"Error entering Google password: {str(e)}")
                # Try alternative selectors for password input
                try:
                    password_inputs = self.driver.find_elements(By.CSS_SELECTOR, "input[type='password']")
                    if password_inputs:
                        password_inputs[0].clear()
                        password_inputs[0].send_keys(google_password)
                        password_inputs[0].send_keys(Keys.RETURN)
                        time.sleep(5)
                    else:
                        raise Exception("No password input field found")
                except Exception as e:
                    logger.error(f"Could not enter Google password: {str(e)}")
                    return {"success": False, "error": "Could not enter Google password"}
            
            # Check for and handle 2FA if needed
            try:
                # Check if 2FA input is present
                twofa_input = self.driver.find_elements(By.CSS_SELECTOR, "input[aria-label*='2-step'], input[type='tel']")
                if twofa_input:
                    logger.info("2FA verification required for Google. Waiting for manual input...")
                    verification_wait_time = 120  # 2 minutes
                    
                    # Add message to inform user
                    self.driver.execute_script("""
                        var div = document.createElement('div');
                        div.style.position = 'fixed';
                        div.style.top = '10px';
                        div.style.left = '10px';
                        div.style.padding = '20px';
                        div.style.backgroundColor = 'yellow';
                        div.style.border = '2px solid red';
                        div.style.zIndex = '9999';
                        div.innerHTML = '<h3>Please enter your Google 2FA verification code</h3><p>Waiting 2 minutes for code input...</p>';
                        document.body.appendChild(div);
                    """)
                    
                    # Wait for completion of verification process
                    WebDriverWait(self.driver, verification_wait_time).until(
                        lambda driver: "medium.com" in driver.current_url 
                        or "signin" not in driver.current_url
                        or "myaccount.google.com" in driver.current_url
                    )
                    logger.info("Google 2FA verification completed or timed out, proceeding...")
            except Exception as e:
                logger.warning(f"Error during 2FA check: {str(e)}")
            
            # Return to the main window if needed
            if popup_found:
                try:
                    self.driver.switch_to.window(main_window)
                    time.sleep(5)
                except Exception as e:
                    logger.warning(f"Error switching back to main window: {str(e)}")
                    # Try to find and switch to the Medium window
                    try:
                        for handle in self.driver.window_handles:
                            self.driver.switch_to.window(handle)
                            if "medium.com" in self.driver.current_url:
                                break
                    except:
                        logger.error("Could not find Medium window")
            
            # Verify we're logged in to Medium
            if "medium.com" not in self.driver.current_url:
                logger.info("Redirecting to Medium homepage")
                self.driver.get("https://medium.com/")
                time.sleep(5)
            
            # Check if we're logged in by looking for "Write" link
            write_links = self.driver.find_elements(By.XPATH, "//a[text()='Write']")
            if not write_links:
                logger.error("Medium login verification failed - 'Write' link not found")
                return {"success": False, "error": "Medium login failed - Write link not found"}
            
            # Click on the Write link
            write_links[0].click()
            time.sleep(5)
            
            # Verify we're on the editor page
            if "new-story" not in self.driver.current_url:
                logger.info("Redirecting to new story page")
                self.driver.get("https://medium.com/new-story")
                time.sleep(5)
            
            try:
                # Check for and dismiss any welcome dialogs or tooltips
                dismiss_btns = self.driver.find_elements(By.CSS_SELECTOR, "button[data-action='dismiss-welcome-modal']")
                if dismiss_btns:
                    dismiss_btns[0].click()
                    time.sleep(1)
            except:
                pass
            
            # Enter title
            logger.info("Entering post title")
            try:
                # First look for the title field (various selectors as Medium's UI changes)
                title_selectors = [
                    "h3[data-placeholder='Title']",
                    "h1[data-placeholder='Title']",
                    ".section-content h1",
                    "h1.graf--title",
                    "[data-testid='post-title']"
                ]
                
                title_field = None
                for selector in title_selectors:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        title_field = elements[0]
                        break
                
                if not title_field:
                    # If we can't find a specific title field, just click at the top of the editor
                    # and trust that's where the title goes
                    editor_elements = self.driver.find_elements(By.CSS_SELECTOR, ".section-content, [contenteditable='true']")
                    if editor_elements:
                        editor_elements[0].click()
                        editor_elements[0].send_keys(title)
                        editor_elements[0].send_keys(Keys.RETURN)
                        time.sleep(2)
                    else:
                        # Try JavaScript insertion as a last resort
                        self.driver.execute_script("""
                            var titleElement = document.querySelector('[contenteditable="true"]');
                            if (titleElement) {
                                titleElement.focus();
                                titleElement.innerHTML = arguments[0];
                            }
                        """, title)
                else:
                    title_field.click()
                    title_field.send_keys(title)
                    title_field.send_keys(Keys.RETURN)
                    time.sleep(2)
            except Exception as title_err:
                logger.error(f"Error entering title: {str(title_err)}")
                # Continue anyway as some Medium interfaces have different layouts
            
            # Enter content
            logger.info("Entering post content")
            try:
                # Process HTML content to plain text if needed
                plain_content = content
                if content.startswith('<'):
                    # Attempt to convert HTML to plain text
                    soup = BeautifulSoup(content, 'html.parser')
                    plain_content = soup.get_text("\n\n")
                
                # Find the editor area and input the content
                editor_elements = self.driver.find_elements(By.CSS_SELECTOR, "[contenteditable='true']")
                if editor_elements:
                    editor = editor_elements[-1]  # Usually the last contenteditable is the main editor
                    editor.click()
                
                    # Type the content paragraph by paragraph for more reliability
                    paragraphs = plain_content.split('\n\n')
                    for paragraph in paragraphs:
                        if paragraph.strip():
                            editor.send_keys(paragraph)
                            editor.send_keys(Keys.RETURN)
                            editor.send_keys(Keys.RETURN)
                            time.sleep(0.5)
                else:
                    logger.error("Could not find editable area")
                    return {"success": False, "error": "Could not find editable area"}
            except Exception as content_err:
                logger.error(f"Error entering content: {str(content_err)}")
                return {"success": False, "error": f"Could not enter content: {str(content_err)}"}
            
            # Add tags if provided
            if tags:
                try:
                    logger.info("Adding tags to post")
                    # Look for "Add a tag" button or input
                    add_tag_buttons = self.driver.find_elements(By.XPATH, "//button[contains(text(), 'Add a tag')]")
                    
                    if add_tag_buttons:
                        add_tag_buttons[0].click()
                        time.sleep(1)
                        
                        # Find tag input field
                        tag_input = self.wait.until(EC.presence_of_element_located(
                            (By.CSS_SELECTOR, "input[placeholder='Add a tag...']")
                        ))
                        
                        # Process tags
                        tag_list = tags if isinstance(tags, list) else [t.strip() for t in tags.split(',')]
                        for tag in tag_list[:5]:  # Medium usually limits to 5 tags
                            if tag:
                                tag_input.clear()
                                tag_input.send_keys(tag)
                                time.sleep(1)
                                tag_input.send_keys(Keys.RETURN)
                                time.sleep(1)
                except Exception as tag_err:
                    logger.warning(f"Error adding tags: {str(tag_err)}")
                    # Continue anyway since tags are optional
            
            # Find and click publish button based on requested publish status
            try:
                logger.info(f"Setting publish status to {publish_status}")
                
                # Look for the Publish button (UI changed recently)
                publish_button_selectors = [
                    "button[data-action='show-post-menu']",
                    "button:has-text('Publish')",
                    "button.publish-button",
                    "[data-testid='publish-button']"
                ]
                
                publish_button = None
                for selector in publish_button_selectors:
                    try:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        if elements:
                            publish_button = elements[0]
                            break
                    except:
                        continue
                
                if not publish_button:
                    # Try XPath as a fallback
                    publish_buttons = self.driver.find_elements(By.XPATH, "//button[contains(text(), 'Publish')]")
                    if publish_buttons:
                        publish_button = publish_buttons[0]
                
                if publish_button:
                    publish_button.click()
                    time.sleep(2)
                else:
                    logger.error("Could not find publish button")
                    return {"success": False, "error": "Could not find publish button"}
                
                # Choose appropriate publish option based on publish_status
                status_options = {
                    "public": "//span[text()='Publish now']",
                    "draft": "//span[text()='Save as draft']",
                    "unlisted": "//span[text()='Share link only']"
                }
                
                # Try to find the specific publish option
                option_xpath = status_options.get(publish_status.lower(), status_options["draft"])
                try:
                    publish_option = self.wait.until(EC.element_to_be_clickable(
                        (By.XPATH, option_xpath)
                    ))
                    publish_option.click()
                    time.sleep(2)
                except Exception as e:
                    logger.warning(f"Could not find specific publish option: {str(e)}")
                    # Try to find any submit button as fallback
                    submit_buttons = self.driver.find_elements(By.XPATH, "//button[contains(text(), 'Publish') or contains(text(), 'Save')]")
                    if submit_buttons:
                        submit_buttons[0].click()
                        time.sleep(3)
                    else:
                        logger.error("Could not find any publish/save buttons")
                        return {"success": False, "error": "Could not find publish/save buttons"}
                
                # If publishing, might need to confirm with an additional dialog
                if publish_status.lower() == "public":
                    try:
                        confirm_btn = self.wait.until(EC.element_to_be_clickable(
                            (By.XPATH, "//button[contains(text(), 'Publish')]")
                        ))
                        confirm_btn.click()
                        time.sleep(3)
                    except:
                        logger.warning("No publish confirmation dialog found, continuing")
                
                logger.info(f"Successfully {publish_status}ed post on Medium")
                return {"success": True, "message": f"Posted to Medium with status: {publish_status}"}
                
            except Exception as publish_err:
                logger.error(f"Error publishing post: {str(publish_err)}")
                return {"success": False, "error": f"Failed to publish: {str(publish_err)}"}
                
        except Exception as e:
            logger.error(f"Error posting to Medium with Selenium: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def post_to_linkedin(self, title, content, images=None):
        """
        Post content to LinkedIn using Selenium automation
        
        Args:
            title (str): The title of the post
            content (str): The content of the post
            images (list): Optional list of image paths to upload
            
        Returns:
            dict: Status information about the posting attempt
        """
        if not self.linkedin_email or not self.linkedin_password:
            logger.error("LinkedIn credentials not found in environment variables")
            return {"success": False, "error": "LinkedIn credentials not configured"}
        
        try:
            # Setup the driver if not already done
            if not self.driver:
                self.setup_driver()
            
            # Navigate to LinkedIn
            logger.info("Navigating to LinkedIn")
            self.driver.get("https://www.linkedin.com/login")
            time.sleep(2)
            
            # Login to LinkedIn
            logger.info("Logging in to LinkedIn")
            self.wait.until(EC.presence_of_element_located((By.ID, "username"))).send_keys(self.linkedin_email)
            self.wait.until(EC.presence_of_element_located((By.ID, "password"))).send_keys(self.linkedin_password)
            self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit']"))).click()
            
            # Wait for login to proceed
            time.sleep(10)  # Increased initial wait time
            
            # Check for verification code input
            try:
                # Look for PIN verification form
                pin_input = self.driver.find_elements(By.ID, "input__phone_verification_pin")
                if pin_input:
                    logger.info("Verification code required. Waiting for manual input...")
                    # Wait longer for user to enter verification code manually
                    verification_wait_time = 120  # 2 minutes to enter code
                    
                    # Add a message to the page to inform user
                    self.driver.execute_script("""
                        var div = document.createElement('div');
                        div.style.position = 'fixed';
                        div.style.top = '10px';
                        div.style.left = '10px';
                        div.style.padding = '20px';
                        div.style.backgroundColor = 'yellow';
                        div.style.border = '2px solid red';
                        div.style.zIndex = '9999';
                        div.innerHTML = '<h3>Please enter the verification code sent to your device</h3><p>Waiting 2 minutes for code input...</p>';
                        document.body.appendChild(div);
                    """)
                    
                    # Wait for redirection
                    WebDriverWait(self.driver, verification_wait_time).until(
                        lambda driver: "feed" in driver.current_url
                    )
                    logger.info("Verification code accepted, proceeding...")
                
                # Also check for other verification methods (SMS, email, etc.)
                verification_elements = self.driver.find_elements(By.CSS_SELECTOR, "[data-litms-control-urn='verification_control']")
                if verification_elements:
                    logger.info("Alternative verification method required. Waiting for manual completion...")
                    # Wait longer for user to complete verification
                    verification_wait_time = 180  # 3 minutes to complete verification
                    
                    # Add a message to the page
                    self.driver.execute_script("""
                        var div = document.createElement('div');
                        div.style.position = 'fixed';
                        div.style.top = '10px';
                        div.style.left = '10px';
                        div.style.padding = '20px';
                        div.style.backgroundColor = 'yellow';
                        div.style.border = '2px solid red';
                        div.style.zIndex = '9999';
                        div.innerHTML = '<h3>Please complete the LinkedIn verification process</h3><p>Waiting 3 minutes for verification...</p>';
                        document.body.appendChild(div);
                    """)
                    
                    # Wait for redirection
                    WebDriverWait(self.driver, verification_wait_time).until(
                        lambda driver: "feed" in driver.current_url
                    )
                    logger.info("Verification completed, proceeding...")
            
            except TimeoutException:
                # If timeout occurs during verification, abort
                logger.error("Verification timeout - user didn't complete verification in time")
                return {"success": False, "error": "LinkedIn verification timeout"}
            except Exception as e:
                # If another error occurs, log and continue (it might have been successful)
                logger.warning(f"Error during verification check: {str(e)}")
            
            # Check if login was successful (look for the feed page)
            if "feed" not in self.driver.current_url:
                logger.error("LinkedIn login failed - not redirected to feed page")
                return {"success": False, "error": "LinkedIn login failed"}
            
            logger.info("Successfully logged into LinkedIn")
            
            # Navigate to create post page
            logger.info("Creating new post")
            self.driver.get("https://www.linkedin.com/feed/")
            time.sleep(3)
            
            # Click on start post button
            start_post_btn = self.wait.until(EC.element_to_be_clickable(
                (By.CSS_SELECTOR, "button[aria-label='Create a post']")
            ))
            start_post_btn.click()
            time.sleep(2)
            
            # Find and click on the post content area
            post_area = self.wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, "div[aria-label='Text editor for creating content']")
            ))
            post_area.click()
            
            # Enter post content
            formatted_content = f"{title}\n\n{content[:1000]}" # LinkedIn has character limits
            post_area.send_keys(formatted_content)
            time.sleep(2)
            
            # Upload images if provided
            if images and len(images) > 0:
                try:
                    # Find and click on the image upload button
                    media_button = self.wait.until(EC.element_to_be_clickable(
                        (By.CSS_SELECTOR, "button[aria-label='Add a photo']")
                    ))
                    media_button.click()
                    time.sleep(1)
                    
                    # Find the file input and upload the image
                    for image_path in images[:4]:  # LinkedIn typically allows up to 4 images
                        file_input = self.wait.until(EC.presence_of_element_located(
                            (By.CSS_SELECTOR, "input[type='file']")
                        ))
                        # Convert to absolute path
                        abs_path = str(Path(image_path).resolve())
                        file_input.send_keys(abs_path)
                        time.sleep(3)  # Wait for upload
                        
                        # If uploading multiple images, we need to click "add image" again for each subsequent image
                        if images.index(image_path) < len(images) - 1:
                            add_another_btn = self.wait.until(EC.element_to_be_clickable(
                                (By.CSS_SELECTOR, "button[aria-label='Add another media']")
                            ))
                            add_another_btn.click()
                            time.sleep(1)
                            
                except Exception as img_err:
                    logger.error(f"Error uploading images to LinkedIn: {str(img_err)}")
                    # Continue with posting even if image upload fails
            
            # Click post button
            post_button = self.wait.until(EC.element_to_be_clickable(
                (By.CSS_SELECTOR, "button[aria-label='Post']")
            ))
            post_button.click()
            
            # Wait for post to complete
            time.sleep(5)
            
            logger.info("Successfully posted to LinkedIn")
            return {"success": True, "message": "Posted to LinkedIn successfully"}
            
        except Exception as e:
            logger.error(f"Error posting to LinkedIn: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def docx_to_html(self, docx_file_path):
        """
        Convert a DOCX file to HTML for Medium posting
        
        Args:
            docx_file_path (str): Path to the DOCX file
            
        Returns:
            str: HTML content of the document
        """
        try:
            doc = docx.Document(docx_file_path)
            html_content = []
            
            # Process document paragraphs
            for para in doc.paragraphs:
                if not para.text.strip():
                    continue
                    
                # Check if this is a heading
                if para.style.name.startswith('Heading'):
                    level = int(para.style.name[-1]) if para.style.name[-1].isdigit() else 1
                    html_content.append(f"<h{level}>{para.text}</h{level}>")
                else:
                    html_content.append(f"<p>{para.text}</p>")
            
            return "\n".join(html_content)
            
        except Exception as e:
            logger.error(f"Error converting DOCX to HTML: {str(e)}")
            return ""
    
    def close(self):
        """Clean up resources"""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("Browser closed successfully")
            except Exception as e:
                logger.error(f"Error closing browser: {str(e)}")

# Test function for local testing
def test_posting():
    poster = SocialMediaPoster()
    try:
        # Test Medium post
        result = poster.post_to_medium(
            "Test Post from Python",
            "<p>This is a test post created by the Medium API through Python.</p>",
            ["test", "python", "api"],
            "draft"
        )
        print(f"Medium post result: {result}")
        
        # Test LinkedIn post
        result = poster.post_to_linkedin(
            "Test Post from Python",
            "This is a test post created by Python automation on LinkedIn."
        )
        print(f"LinkedIn post result: {result}")
        
    finally:
        poster.close()

if __name__ == "__main__":
    test_posting() 