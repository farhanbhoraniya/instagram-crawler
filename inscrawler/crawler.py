from __future__ import unicode_literals

import glob
import json
import os
import re
import sys
import time
import traceback
from builtins import open
from time import sleep

from tqdm import tqdm

from . import secret
from .browser import Browser
from .exceptions import RetryException
from .fetch import fetch_caption
from .fetch import fetch_comments
from .fetch import fetch_datetime
from .fetch import fetch_imgs
from .fetch import fetch_likers
from .fetch import fetch_likes_plays
from .fetch import fetch_details
from .utils import instagram_int
from .utils import randmized_sleep
from .utils import retry


class Logging(object):
    PREFIX = "instagram-crawler"

    def __init__(self):
        try:
            timestamp = int(time.time())
            self.cleanup(timestamp)
            self.logger = open("/tmp/%s-%s.log" % (Logging.PREFIX, timestamp), "w")
            self.log_disable = False
        except Exception:
            self.log_disable = True

    def cleanup(self, timestamp):
        days = 86400 * 7
        days_ago_log = "/tmp/%s-%s.log" % (Logging.PREFIX, timestamp - days)
        for log in glob.glob("/tmp/instagram-crawler-*.log"):
            if log < days_ago_log:
                os.remove(log)

    def log(self, msg):
        if self.log_disable:
            return

        self.logger.write(msg + "\n")
        self.logger.flush()

    def __del__(self):
        if self.log_disable:
            return
        self.logger.close()


class InsCrawler(Logging):
    URL = "https://www.instagram.com"
    RETRY_LIMIT = 10

    def __init__(self, has_screen=False):
        super(InsCrawler, self).__init__()
        self.browser = Browser(has_screen)
        self.page_height = 0
        self.login()

    def _dismiss_login_prompt(self):
        ele_login = self.browser.find_one(".Ls00D .Szr5J")
        if ele_login:
            ele_login.click()

    def login(self):
        browser = self.browser
        url = "%s/accounts/login/" % (InsCrawler.URL)
        browser.get(url)
        u_input = browser.find_one('input[name="username"]')
        u_input.send_keys(secret.username)
        p_input = browser.find_one('input[name="password"]')
        p_input.send_keys(secret.password)

        login_btn = browser.find_one(".L3NKy")
        login_btn.click()

        @retry()
        def check_login():
            if browser.find_one('input[name="username"]'):
                raise RetryException()

        check_login()

    def get_followers(self):
        # print("GETTING FOLLOWERS")
        likers = set()
        
        try:
            time.sleep(0.5)
            likers_elems = list(self.browser.driver.find_elements_by_xpath('/html/body/div[5]/div/div/div[2]/ul/div/li'))
            # print(likers_elems)
        except Exception as e:
            print("NO LIKERS FOUND FIRST TIME", e)
            likers_elems = []
        # print(likers_elems, "")
        last_liker = None
        while likers_elems:
            # print("IN LOOP")
            # print(len(likers), len(likers_elems))
            if len(likers) >= 1000:
                break
            for ele in likers_elems:
                try:
                    name = ele.find_element_by_class_name('FPmhX').get_attribute('innerHTML')
                    likers.add(name)
                except Exception as e:
                    print("NOT ABLE TO GET THE NAME", e)
                    continue

            if last_liker == likers_elems[-1]:
                break

            last_liker = likers_elems[-1]
            # print(last_liker)
            try:
                last_liker.location_once_scrolled_into_view
                sleep(1)
            except Exception as e:
                print("EXCEPTION WHILE SCROLLING", e)
            
            try:
                likers_elems = list(self.browser.driver.find_elements_by_xpath('/html/body/div[5]/div/div/div[2]/ul/div/li'))
                likers_elems = likers_elems[-12:]
            except Exception as e:
                print("NO LIKERS FOUND AFTER FIRST TIME", e)
                likers_elems = []
        
        # close_btn = self.browser.find_one(".eiUFA .wpO6b ")
        # close_btn.click()
        return list(likers)

    def get_followed_hashtags(self, user_id, query_hash, dict_data):
        likers = set()
        browser = self.browser
        
        base_query = "graphql/query/?query_hash=" + query_hash + "&variables="
        
        base_followers_url = "%s/%s" % (InsCrawler.URL, base_query)
        
        query_vars = {
            "id":user_id
        }

        query_vars_str = json.dumps(query_vars).replace(" ", "")
        followers_url = "%s%s" % (base_followers_url, query_vars_str)

        browser.get(followers_url)
        time.sleep(1)

        try:
            followers_txt = browser.driver.find_element_by_tag_name('pre').text
            followers_json = json.loads(followers_txt)
            # print("===FollowersContent")
            # print(followers)
            
            followers_list = followers_json['data']['user'][dict_data]['edges']

            for follower in followers_list:
                likers.add(follower['node']['name'])
        
        except Exception as e:
            print("ERROR WHILE GETTING THE HASHTAGS", e)

        return list(likers)
    
    def get_followers_list(self, user_id, query_hash, dict_data):
        likers = set()
        browser = self.browser
        
        base_query = "graphql/query/?query_hash=" + query_hash + "&variables="
        
        base_followers_url = "%s/%s" % (InsCrawler.URL, base_query)
        
        page_size = 50
        
        # timeoutOccured = False

        query_vars = {
            "id":user_id,
            "first":page_size
        }

        query_vars_str = json.dumps(query_vars).replace(" ", "")
        followers_url = "%s%s" % (base_followers_url, query_vars_str)

        max_followers = 21000

        total_follower_count = 0

        while True:
            
            if(total_follower_count >= max_followers):
                break

            browser.get(followers_url)
            time.sleep(1)

            try:
                followers_txt = browser.driver.find_element_by_tag_name('pre').text
                followers_json = json.loads(followers_txt)
                # print("===FollowersContent")
                # print(followers)
                pagination_info = followers_json['data']['user'][dict_data]['page_info']
                has_next = pagination_info['has_next_page']
                
                followers_list = followers_json['data']['user'][dict_data]['edges']

                for follower in followers_list:
                    likers.add(follower['node']['username'])
                    total_follower_count += 1

                if(has_next):
                    next_page = pagination_info['end_cursor']
                    query_vars['after'] = next_page
                    query_vars_str = json.dumps(query_vars).replace(" ", "")
                    followers_url = "%s%s" % (base_followers_url, query_vars_str)
                    # print("=======next_url")
                    # print(followers_url)
                else:
                    break
            
            except Exception as e:
                print("ERROR WHILE GETTING THE FOLLOWING", e)
                print("Total Followers Found : " + str(total_follower_count))
                print("Sleeping for 5 mins...")
                time.sleep(300)

        return list(likers)


    def get_user_profile(self, username, get_followers=True):
        browser = self.browser
        url = "%s/%s/" % (InsCrawler.URL, username)
        browser.get(url)
        time.sleep(2)

        user_config_ele = browser.driver.find_element_by_xpath('/html/body/script[1]')

        user_config_txt = user_config_ele.get_attribute('innerHTML')[21:-1]
        
        user_config_json = json.loads(user_config_txt)
        user_id = user_config_json['entry_data']['ProfilePage'][0]['graphql']['user']['id']
        # print("=========user_id")
        # print(user_id)
        # count = 1
        # for script in user_config_txt:

        #     print("======= " + str(count))
        #     print(script.get_attribute('innerHTML')[:22])
        #     count += 1

        # print("========user_config_txt")
        # print(user_config_txt)

        followers = []
        following = {}
        users = []
        hashtags = []

        if get_followers:
            try:
                # Following d04b0a864b4b54837c0d870b0e77e076 | edge_follow
                # Hashtag e6306cc3dbe69d6a82ef8b5f8654c50b | edge_following_hashtag
                # Query Hash to get Followers is c76146de99bb02f6415203be841dd25a | edge_followed_by
                print("Getting Followers...")
                followers = self.get_followers_list(user_id, "c76146de99bb02f6415203be841dd25a", "edge_followed_by")
            except Exception as e:
                print("ERROR WHILE GETTING THE FOLLOWERS", e)
                pass
            # print(followers)
            # browser.get(url)
            # time.sleep(2)
            try:
                # follwing_elem = browser.driver.find_element_by_xpath('//*[@id="react-root"]/section/main/div/header/section/ul/li[3]')
                # follwing_elem.click()
                print("Getting Following...")
                users = self.get_followers_list(user_id, "d04b0a864b4b54837c0d870b0e77e076", "edge_follow")
            except Exception as e:
                print("ERROR WHILE GETTING THE FOLLOWING", e)
                pass

            # print(users)

            # browser.get(url)
            # time.sleep(2)

            try:
                # follwing_elem = browser.driver.find_element_by_xpath('//*[@id="react-root"]/section/main/div/header/section/ul/li[3]')
                # follwing_elem.click()
                # hashtag_elem = browser.driver.find_element_by_xpath('/html/body/div[4]/div/div/nav/a[2]')
                # hashtag_elem.click()

                # hashtag_lists = browser.driver.find_elements_by_class_name('hI7cq')
                print("Getting Hashtags...")
                hashtags = self.get_followed_hashtags(user_id, "e6306cc3dbe69d6a82ef8b5f8654c50b", "edge_following_hashtag")
                # for item in hashtag_lists:
                #     # First character is #. So we remove it.
                #     hashtags.append(item.text[1:])

            except Exception as e:
                print("ERROR WHILE GETTING THE HASHTAGS", e)
                pass

        following['users'] = users
        following['hashtags'] = hashtags

        # print(following)
        browser.get(url)
        time.sleep(2)
        name = browser.find_one(".rhpdm")
        if name is None:
            name = ""
        else:
            name = name.text
        desc = browser.find_one(".-vDIg span")
        photo = browser.find_one("._6q-tv")
        try:
            photo_url = photo.get_attribute("src")
        except:
            photo_url = ""

        statistics = [ele.text for ele in browser.find(".g47SY")]

        post_num, follower_num, following_num = statistics        

        return {
            "name": name,
            "desc": desc.text if desc else None,
            "photo_url": photo_url,
            "post_num": post_num,
            "follower_num": follower_num,
            "following_num": following_num,
            "followers": followers,
            "following": following,
            "username": username
        }

    def get_user_profile_from_script_shared_data(self, username):
        browser = self.browser
        url = "%s/%s/" % (InsCrawler.URL, username)
        browser.get(url)
        source = browser.driver.page_source
        p = re.compile(r"window._sharedData = (?P<json>.*?);</script>", re.DOTALL)
        json_data = re.search(p, source).group("json")
        data = json.loads(json_data)

        user_data = data["entry_data"]["ProfilePage"][0]["graphql"]["user"]

        return {
            "name": user_data["full_name"],
            "desc": user_data["biography"],
            "photo_url": user_data["profile_pic_url_hd"],
            "post_num": user_data["edge_owner_to_timeline_media"]["count"],
            "follower_num": user_data["edge_followed_by"]["count"],
            "following_num": user_data["edge_follow"]["count"],
            "website": user_data["external_url"],
        }

    def get_user_posts(self, username, number=None, detail=False):
        user_profile = self.get_user_profile(username, False)
        if not number:
            number = instagram_int(user_profile["post_num"])

        self._dismiss_login_prompt()

        if detail:
            return self._get_posts_full(number)
        else:
            return self._get_posts(number)

    def get_latest_posts_by_tag(self, tag, num):
        url = "%s/explore/tags/%s/" % (InsCrawler.URL, tag)
        self.browser.get(url)
        return self._get_posts_full(num)

    def auto_like(self, tag="", maximum=1000):
        self.login()
        browser = self.browser
        if tag:
            url = "%s/explore/tags/%s/" % (InsCrawler.URL, tag)
        else:
            url = "%s/explore/" % (InsCrawler.URL)
        self.browser.get(url)

        ele_post = browser.find_one(".v1Nh3 a")
        ele_post.click()

        for _ in range(maximum):
            heart = browser.find_one(".dCJp8 .glyphsSpriteHeart__outline__24__grey_9")
            if heart:
                heart.click()
                randmized_sleep(2)

            left_arrow = browser.find_one(".HBoOv")
            if left_arrow:
                left_arrow.click()
                randmized_sleep(2)
            else:
                break

    def _get_posts_full(self, num):
        @retry()
        def check_next_post(cur_key):
            ele_a_datetime = browser.find_one(".eo2As .c-Yi7")

            # It takes time to load the post for some users with slow network
            if ele_a_datetime is None:
                # print("RETRY EXCEPTION")
                raise RetryException()

            next_key = ele_a_datetime.get_attribute("href")
            if cur_key == next_key:
                raise RetryException()
        # print("GETTING FULL POSTS")
        browser = self.browser
        browser.implicitly_wait(1)
        browser.scroll_down()
        ele_post = browser.find_one(".v1Nh3 a")
        if ele_post is None:
            return []
        ele_post.click()
        dict_posts = []

        pbar = tqdm(total=num)
        pbar.set_description("fetching")
        cur_key = None

        all_posts = self._get_posts(num)
        # print("ALL POSTS------------------")
        # print(all_posts)
        i = 1

        # Fetching all posts
        for x in range(num):
            # print("GETTING POST NUMBER ", x)
            dict_post = {}

            # Fetching post detail
            try:
                if(i < num):
                    check_next_post(all_posts[i]['key'])
                    i = i + 1

                browser.open_new_tab(all_posts[x]['key'])
                # Fetching datetime and url as key
                ele_a_datetime = browser.find_one(".eo2As .c-Yi7")
                cur_key = ele_a_datetime.get_attribute("href")
                # print("CURR_KEY ", cur_key)
                dict_post["key"] = cur_key
                fetch_datetime(browser, dict_post)
                fetch_imgs(browser, dict_post)
                # fetch_likes_plays(browser, dict_post)
                fetch_likers(browser, dict_post)
                fetch_caption(browser, dict_post)
                fetch_comments(browser, dict_post)
                browser.close_current_tab()

            except RetryException:
                browser.close_current_tab()
                sys.stderr.write(
                    "\x1b[1;31m"
                    + "Failed to fetch the post: "
                    + cur_key or 'URL not fetched'
                    + "\x1b[0m"
                    + "\n"
                )
                break

            except Exception:
                sys.stderr.write(
                    "\x1b[1;31m"
                    + "Failed to fetch the post: "
                    + cur_key if isinstance(cur_key,str) else 'URL not fetched'
                    + "\x1b[0m"
                    + "\n"
                )
                traceback.print_exc()

            self.log(json.dumps(dict_post, ensure_ascii=False))
            # dict_posts[browser.current_url] = dict_post
            dict_posts.append(dict_post)
            pbar.update(1)

        pbar.close()
        # posts = list(dict_posts.values())
        posts = dict_posts
        if posts:
            posts.sort(key=lambda post: post["datetime"], reverse=True)
        return posts

    def _get_posts(self, num):
        """
            To get posts, we have to click on the load more
            button and make the browser call post api.
        """
        TIMEOUT = 600
        browser = self.browser
        key_set = set()
        posts = []
        pre_post_num = 0
        wait_time = 1

        pbar = tqdm(total=num)

        def start_fetching(pre_post_num, wait_time):
            ele_posts = browser.find(".v1Nh3 a")
            for ele in ele_posts:
                key = ele.get_attribute("href")
                if key not in key_set:
                    dict_post = { "key": key }
                    ele_img = browser.find_one(".KL4Bh img", ele)
                    dict_post["caption"] = ele_img.get_attribute("alt")
                    dict_post["img_url"] = ele_img.get_attribute("src")

                    fetch_details(browser, dict_post)

                    key_set.add(key)
                    posts.append(dict_post)

                    if len(posts) == num:
                        break

            if pre_post_num == len(posts):
                pbar.set_description("Wait for %s sec" % (wait_time))
                sleep(wait_time)
                pbar.set_description("fetching")

                wait_time *= 2
                browser.scroll_up(300)
            else:
                wait_time = 1

            pre_post_num = len(posts)
            browser.scroll_down()

            return pre_post_num, wait_time

        pbar.set_description("fetching")
        while len(posts) < num and wait_time < TIMEOUT:
            post_num, wait_time = start_fetching(pre_post_num, wait_time)
            pbar.update(post_num - pre_post_num)
            pre_post_num = post_num

            loading = browser.find_one(".W1Bne")
            if not loading and wait_time > TIMEOUT / 2:
                break

        pbar.close()
        print("Done. Fetched %s posts." % (min(len(posts), num)))
        return posts[:num]
