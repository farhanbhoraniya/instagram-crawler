## Install
1. Make sure you have Chrome browser installed.
2. Download [chromedriver](https://sites.google.com/a/chromium.org/chromedriver/) and put it into bin folder: `./inscrawler/bin/`
3. Install Selenium: `pip3 install -r requirements.txt`
4. Create secret.txt file into `./inscrawler/`. First line of secret.txt should be Instagram username and second line should be password.

## Crawler
### Usage
```
positional arguments:
  mode
    options: [posts_full, profile, hashtag]

optional arguments:
  -n NUMBER, --number NUMBER
                        number of returned posts or default to 10

```


### Get User Details

1. Create `user_info_pending.json` file at the root folder
2. Add the list of usernames you want to fetch details for into the user_info_pending.json file
3. Create `user_info_visited.json` file at the root folder
4. Add list of usernames for which you don't want to fetch the details or add empty list
5. Run using `python crawler.py profile`
6. User details will be added into the file `users.json`. 
7. Crawler will update the list in `user_info_pending.json` using usernames from followers and following list



### Get User Posts

1. Creste `user_posts_pending.json` file at the root folder
2. Add the list of usernames you want to fetch posts of into the user_posts_pending.json file
3. Create `user_posts_visited.json` file at the root folder
4. Add list of usernames for which you don't want to fetch posts or add empty list
5. Run using `python crawler.py posts_full -n [number of posts to fetch]`
6. User posts will be added into the file `user_posts.json`
7. After getting the posts of user, user will be added in the file `user_posts_visited.json` 



### Get Hashtag Posts

1. Creste `pending_hashtag.json` file at the root folder
2. Add the list of hashtags you want to fetch posts of into the pending_hashtag.json file
3. Create `visited_hashtag.json` file at the root folder
4. Add list of hashtags for which you don't want to fetch posts or add empty list
5. Run using `python crawler.py hashtag -n [number of posts to fetch]`
6. Hashtag posts will be added into the file `hashtag.json`
7. After getting the posts of hashtag, it will be added in the file `visited_hashtag.json`
