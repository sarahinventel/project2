import os
import time
from datetime import datetime
import csv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
from dotenv import load_dotenv
import json
import logging
from random import uniform
from retrying import retry

# Load environment variables
load_dotenv()

class InfluencerScraper:
    def __init__(self, max_retries=3, retry_delay=2):
        self.platforms = {
            'instagram': {
                'base_url': 'https://www.instagram.com',
                'selectors': {
                    'username': 'username',
                    'password': 'password',
                    'profile': 'profile',
                    'username': 'username',
                    'followers': 'followers',
                    'engagement': 'engagement',
                    'name': 'name',
                    'bio': 'bio',
                    'location': 'location',
                    'profile_link': 'profile-link'
                }
            },
            'tiktok': {
                'base_url': 'https://www.tiktok.com',
                'selectors': {
                    'profile': 'profile',
                    'username': 'username',
                    'followers': 'followers',
                    'engagement': 'engagement',
                    'name': 'name',
                    'bio': 'bio',
                    'location': 'location',
                    'profile_link': 'profile-link'
                }
            },
            'twitter': {
                'base_url': 'https://twitter.com',
                'selectors': {
                    'username': 'username',
                    'password': 'password',
                    'profile': 'profile',
                    'username': 'username',
                    'followers': 'followers',
                    'engagement': 'engagement',
                    'name': 'name',
                    'bio': 'bio',
                    'location': 'location',
                    'profile_link': 'profile-link'
                }
            }
        }
        self.driver = None
        self.data = []
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.setup_driver()
        self.setup_logging()
        
    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
    def setup_driver(self):
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        self.driver = webdriver.Chrome(options=options)
        
    def wait_for_element(self, by, value, timeout=10, retry_count=0):
        try:
            return WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
        except (TimeoutException, StaleElementReferenceException) as e:
            if retry_count < self.max_retries:
                time.sleep(self.retry_delay)
                return self.wait_for_element(by, value, timeout, retry_count + 1)
            raise e
        
    @retry(stop_max_attempt_number=3, wait_fixed=2000)
    def login_to_platform(self, platform):
        try:
            self.driver.get(self.platforms[platform]['base_url'])
            time.sleep(uniform(2, 4))
            
            if platform == 'instagram':
                username = os.getenv('INSTAGRAM_USERNAME')
                password = os.getenv('INSTAGRAM_PASSWORD')
                
                username_field = self.wait_for_element(By.NAME, self.platforms[platform]['selectors']['username'])
                password_field = self.wait_for_element(By.NAME, self.platforms[platform]['selectors']['password'])
                
                username_field.send_keys(username)
                password_field.send_keys(password)
                password_field.send_keys(Keys.RETURN)
                
                # Wait for login to complete
                time.sleep(uniform(3, 5))
                
            elif platform == 'tiktok':
                self.driver.get('https://www.tiktok.com/login')
                time.sleep(uniform(2, 4))
            
            elif platform == 'twitter':
                self.driver.get('https://twitter.com/login')
                time.sleep(uniform(2, 4))
                
            self.logger.info(f'Successfully logged into {platform}')
            
        except Exception as e:
            self.logger.error(f'Login failed for {platform}: {str(e)}')
            raise
            
    def scroll_page(self, num_scrolls=5):
        for _ in range(num_scrolls):
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(uniform(1.5, 2.5))
            
    def extract_influencer_data(self, platform, influencer):
        try:
            selectors = self.platforms[platform]['selectors']
            
            data = {
                'platform': platform,
                'username': self.safe_get_text(influencer, selectors['username']),
                'followers': self.safe_get_text(influencer, selectors['followers']),
                'engagement': self.safe_get_text(influencer, selectors['engagement']),
                'name': self.safe_get_text(influencer, selectors['name']),
                'bio': self.safe_get_text(influencer, selectors['bio']),
                'location': self.safe_get_text(influencer, selectors['location']),
                'profile_link': self.safe_get_attribute(influencer, selectors['profile_link'], 'href'),
                'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            # Add categories if bio exists
            if data['bio']:
                data['categories'] = self.categorize_influencer(data['bio'])
            
            return data
            
        except Exception as e:
            self.logger.error(f'Error extracting data: {str(e)}')
            return None
            
    def safe_get_text(self, element, selector, default=''):
        try:
            return element.find_element(By.CLASS_NAME, selector).text
        except:
            return default
            
    def safe_get_attribute(self, element, selector, attr, default=''):
        try:
            return element.find_element(By.CLASS_NAME, selector).get_attribute(attr)
        except:
            return default
            
    def scrape_influencer_data(self, platform, keywords):
        try:
            self.login_to_platform(platform)
            
            for keyword in keywords:
                search_url = f'{self.platforms[platform]['base_url']}/search?q={keyword}'
                self.logger.info(f'Searching {platform} for keyword: {keyword}')
                
                self.driver.get(search_url)
                time.sleep(uniform(2, 4))
                
                self.scroll_page()
                
                # Wait for content to load
                time.sleep(uniform(2, 4))
                
                try:
                    influencers = self.wait_for_element(By.CLASS_NAME, self.platforms[platform]['selectors']['profile'])
                    influencers = influencers.find_elements(By.CLASS_NAME, self.platforms[platform]['selectors']['profile'])
                    
                    for influencer in influencers:
                        influencer_data = self.extract_influencer_data(platform, influencer)
                        if influencer_data:
                            self.data.append(influencer_data)
                            self.logger.info(f'Found influencer: {influencer_data['username']}')
                            
                except Exception as e:
                    self.logger.error(f'Error extracting influencers: {str(e)}')
                    continue
                    
        except Exception as e:
            self.logger.error(f'Error scraping {platform}: {str(e)}')
            raise
    
    def save_to_csv(self, filename='influencers.csv'):
        """Save results to CSV with proper error handling"""
        try:
            fieldnames = ['platform', 'username', 'name', 'bio', 'location', 'followers', 'profile_link', 'categories', 'last_updated']
            
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(self.data)
                
            self.logger.info(f'Successfully saved data to {filename}')
            return True
            
        except Exception as e:
            self.logger.error(f'Error saving to CSV: {str(e)}')
            return False




    

        
    def categorize_influencer(self, bio):
        # Simple keyword-based categorization
        categories = []
        keywords = {
            'fashion': ['fashion', 'style', 'clothing', 'outfit'],
            'tech': ['tech', 'technology', 'software', 'coding'],
            'beauty': ['beauty', 'makeup', 'skincare', 'cosmetics'],
            'food': ['food', 'recipe', 'cooking', 'baking'],
            'travel': ['travel', 'adventure', 'exploring', 'vacation'],
            'fitness': ['fitness', 'workout', 'exercise', 'training'],
            'entertainment': ['entertainment', 'music', 'movies', 'shows'],
            'education': ['education', 'learning', 'teaching', 'knowledge'],
            'business': ['business', 'entrepreneur', 'startup', 'company'],
            'lifestyle': ['lifestyle', 'daily', 'routine', 'living']
        }
        
        bio_lower = bio.lower()
        for category, kw_list in keywords.items():
            if any(kw in bio_lower for kw in kw_list):
                categories.append(category)
        
        return categories[:3] if categories else None

    def run(self, keywords):
        """Run the scraper with proper error handling and logging"""
        results = []
        
        for platform in self.platforms:
            try:
                self.logger.info(f'Starting scrape for {platform}')
                self.scrape_influencer_data(platform, keywords)
                results.extend(self.data)
                self.logger.info(f'Completed scrape for {platform}. Found {len(self.data)} influencers.')
                
            except Exception as e:
                self.logger.error(f'Error scraping {platform}: {str(e)}')
                continue
        
        self.driver.quit()
        return results


