<h1 align="center">InstaScrape</h1>

<p align="center"><em>A fast and lightweight Instagram media downloader (without the need of API)</em></p>

<p align="center"><img src="./demo.gif?raw=true" width=70%></p>

<p align="center">
  <a href="https://pypi.python.org/pypi/instascrape-ax"><img src="https://img.shields.io/pypi/v/instascrape-ax.svg"></a>
  <a href="https://pypi.python.org/pypi/instascrape-ax"><img src="https://img.shields.io/pypi/dm/instascrape-ax.svg"></a>
  <a href="./LICENSE.txt"><img src="https://img.shields.io/github/license/a1phat0ny/InstaScrape.svg"></a>
  <a href="https://github.com/a1phat0ny"><img src="https://img.shields.io/badge/dev-a1phat0ny-orange.svg?style=flat-square&logo=github"></a>
</p>

**InstaScrape** is a lightweight command-line utility (and API) for downloading photos and videos ([see the list](#what-you-can-download)) from Instagram.

## Table of Contents
- [Features](#features)
- [Why](#why)
- [Installation](#installation)
  - [Source](#source)
  - [PyPI](#pypi)
  - [Dependencies](#dependencies)
- [Usage](#usage)
  - [Login](#login)
  - [Logout](#logout)
  - [Dump](#dump)
    - [Dump Types and Flags](#dump-types-and-flags)
    - [Flag Option](#flag-option)
    - [Dump Options](#dump-options)
  - [Down](#down)
    - [Media Types](#media-types)
    - [Options](#options)
- [API](#api)
  - [Methods of InstaScraper](#methods-of-instascraper)
    - [Account Interactions](#account-interactions)
    - [Get Independent Structure](#get-independent-structure)
    - [Get Loads of Structures](#get-loads-of-structures)
    - [Download Structures](#download-structures)
  - [Properties of Structures](#properties-of-structures)
    - [Profile](#profilesession-requestssession-name-str)
    - [Post](#postsession-requestssession-shortcode-str)
    - [IGTV](#igtvsession-requestssession-title-str-shortcode-str)
    - [Story](#storysession-requestssession-user_id-str--tag-str--reel_id-str)
    - [Highlight](#highlightsession-requestssession-title-str-reel_id-str)
  - [Fields of Container](#fields-of-container)
- [Terminology](#terminology)
- [Typenames](#typenames)
- [Contributing](#contributing)
- [Disclaimer](#disclaimer)

## Features

* Fancy output with colors ✨
* Fast as lightning,️ with multithreaded scraping support ⚡
* Efficient, use generators (yield) 💪🏻
* Yield data to prevent getting rate limited by Instagram
* Manage cookies and multiple accounts easily 🍪
* Download posts along with their metadata
* Job queue to handle multiple download tasks 🏃🏻‍
* Good exceptions handling ⚠️
* Download posts created in a particular time period 🕓
* Detect and Skip existing files automatically to avoid re-downloading
* Simple to use API
* Simple to use CLI (use symbols)

## What You Can Download

* Timeline media of User
* Tagged media of User
* Profile-picture of User
* Media of Post
* Story of User
* Story of Hashtag
* Story highlights of User
* IGTV videos of User
* Media of Posts in Hashtag
* Media of Posts in Explore
* Saved media of User

## Why

Have you ever seen some beautiful and attractive photos on Instagram that you wanted to download ?

> Of course ! 🤩

Have you ever came across someone on Instagram that you would really like to make a collection of all her media ?

> Hell yeah ! 😍

Then, **InstaScrape** really helps you solve the problems !

## Installation

Make sure you have Python 3.6 (or higher) installed in your machine.

### Source

```bash
$ git clone https://github.com/a1phat0ny/InstaScrape.git  # clone this github repo
$ cd InstaScrape  # cd into the cloned repo
$ python3 setup.py install  # run setup.py and install it
```

### PyPI

```bash
$ pip3 install instascrape-ax  # use 'instascrape-ax' as pypi package name to prevent naming conflicts
```

### Dependencies

1. [requests](https://github.com/requests/requests)
2. [tqdm](https://github.com/tqdm/tqdm)
3. [colorama](https://github.com/tartley/colorama)

## Usage

**There are 4 main actions:** [Login](#login), [Logout](#logout), [Dump](#dump) and [Down](#down).

```
Actions:
  Reminder: You may need to login first.

  {login,logout,dump,down}
    login               Login to Instagram and choose account (cookie)
    logout              Logout from current account
    dump                Dump target data to file or print to stdout
    down                Download media from target(s)

Options:
  -h, --help            show this help message and exit
  -d, --debug           show detailed logging messages (level: DEBUG)
  -q, --quiet           suppress logging messages output (level: ERROR)
```

Once you've logged into an account, `InstaScrape` will store its object `InstaScraper` to a pickle file for next time use. 
This means you will not need to log in again the next time you use `$ instascrape ...`, unless you log out.

***NOTE**: The `InstaScraper` object is stored in a pickle file in `~/.instascrape/insta.pkl`.*

---

### Login

`$ instascrape login [-u/--username <username> | -c/--cookie <path/to/file>]`

* `-u/--username` : try loading a local cookie with this username, prompt for password if no cookie of this username is found
* `-c/--cookie` : provide a cookie file for the login process

**InstaScrape** will store the auth cookie to avoid logging in every time you use `instascrape`. Excessive logins using different cookies everytime is a surefire way to get your account flagged for removal.

The saved auth cookie can be reused for up to 90 days. When the cookie is expired, you need to choose '(3) + Login New Account'. The expired cookie will be overwritten by the new valid cookie since then.

```
▶ instascrape login

    Choose Account

(1)   user1
Last login: Thu Feb  7 20:03:51 2019

(2)   user2
Last login: Thu Feb  7 17:38:36 2019

(x) * user3
Cookie Not Found: deleted from disk

(3) + Login New Account

choice>
```
* `*` asterisk annotated the current logged in user

In this situation, `user3` is logged in. The `InstaScraper` object is saved and being used by `user3`, but the cookie file has already gone (deleted).
That means once `user3` logged out, he will need to provide his credentials again to get a new cookie in order to log into Instagram.

***NOTE**: All cookies are stored in the `~/.instascrape/accounts/` directory.*

---

### Logout

`$ instascrape logout [-r/--real]`

* `-r/--real` : send a POST request and delete the local cookie (if found), you will need to provide your credentials again th next time use
* a `fake logout` just removes the `InstaScraper` object (`insta.pkl`) and does not delete the cookie 

---

### Dump

`$ instascrape dump [type] [[flag]...[-c/--count <integer>]] [-o/--outfile <path/to/file>]`

#### Dump Types and Flags

* **User `@username`** : user information in JSON format
  * followers `-followers` : followers of the user in plain text, one username per line in the pattern of `@{username}`
  * followings `-followings` : followings of the user in plain text, one username per line in the pattern of `@{username}`
* **Post `:shortcode`** post information in JSON format
  * likes `-likes` : users who liked the post in plain text, one username per line in the pattern of `@{username}` 
  * comments `-comments` : comments of the post in JSON format

#### Flag Option

* `--count <integer>` : set maximum count of items you want to get

#### Dump Options

* `-o/--outfile <path/to/file>` : dump data to file in a proper format

```
▶ instascrape dump :BtlyjD2lWvL

Current User: XXXXX

* (Dump) Get Post :BtlyjD2lWvL
- Getting :BtlyjD2lWvL post data...

  [Post Information :BtlyjD2lWvL]
· typename: GraphImage
· url: https://instagram.com/p/BtlyjD2lWvL
· shortcode: BtlyjD2lWvL
· post_id: 1974206323316059083
· location_name: None
· location_id: None
· owner_username: earthpix
· owner_user_id: 303273692
· created_time: 2019-02-08 02:22:34
· caption: Moonrise dreams 🌚 Photo by @abdullah_evindar
· media_count: 1
· likes_count: 287535
· comments_count: 1339
```

```
▶ instascrape dump @9gag -followings

Current User: XXXXX

* (Dump) Get User Followings @9gag
- Fetching @9gag's followings...
- Getting @9gag's profile data...
- Total: 28 Items
- WARNING: Only 28 items can be fetched.

  [User Followings @9gag]
[1] funoff
[2] watchx
[3] 9gagshop
[4] voyaged
[5] 9gaggirly
[6] 9gagnomnom
[7] classicalaf
[8] 9gaggroove
[9] takemymoney
[10] meowed
[11] 6wordsmith
[12] horrorphiles
[13] thinkinanime
[14] familygoals
[15] fitbeast
[16] 9gagscience
[17] bestads
[18] getfamous
[19] nevertooweird
[20] askingforafrd
[21] couple
[22] barked
[23] hipdict
[24] 8fact
[25] 9gagceo
[26] nsfwclothing
[27] 9gagmobile
[28] doodles
```

---

### Down

`$ instascrape down [[type]...] [[option]...]`

#### Media Types

* `PROFILE` : download all types of media of the user
* `@username` : download timeline posts of the user
* `@#username` : download tagged posts of the user
* `/username` : download the profile picture of the user
* `:shortcode` : download a single post
* `%`: download story of
  * `%@username` : a user
  * `%#hashtag` : a hashtag
* `%-username` : download story highlights of the user
* `+username` : download IGTV videos of the user
* `#hashtag` : download posts of the hashtag
* `-explore` : download posts of explore feed
* `-saved` : download self saved posts

#### Options

* `--count <integer>` : set maximum count of items you want to get

* `--only {image, video, sidecar}` : filter out other types of posts, only download this type of posts (by typename)

* `--dest <path/to/directory>` : set path to the download destination

* `--preload` : collect the initial data of all items (using thread workers) before downloading them, might help increase the speed.

* `--before-date <datetime>` : download posts created before this datetime, can be combined with `after-date` (`{YY-mm-dd-h:m:s}`)

* `--after-date <datetime>` : download posts created after this datetime, can be combined with `before-date` (`{YY-mm-dd-h:m:s}`)

* `--dump-metadata` : download posts along with their metadata dumped in JSON files

***WARN:** `--preload` option is unstable and should only be used when downloading small amount of posts, otherwise you may get rate limited quickly*.

***NOTE:** Posts downloaded will be named in the pattern `{YY-mm-dd-h:m:s}_{shortcode}` e.g. `2019-02-06-15:57:39_BtiGPG_AhXA`.*

---

## API

**InstaScrape** also provides an easy to use API with context manager implemented.

```python
InstaScraper(username: str = None, password: str = None, user_agent: str = None, cookie: dict = None, save_cookie: bool = True, logout: bool = True, level: int = None)
```

```python
from instascrape import InstaScraper

# InstaScraper will log in when entering
with InstaScraper("username", "password", user_agent=None, cookie=None, save_cookie=True, logout=True) as insta:
    insta.do_something()
# InstaScraper will automatically log out when closing
```

***NOTE:** You should always access `InstaScraper` with its context manager to ensure better security and prevent breaking the code.* 

### Methods of `InstaScraper`

High-level API methods.

#### Account Interactions
* login()
* logout()

#### Get Independent Structure
* get_profile(name) -> structures.Profile
* get_post(shortcode) -> structures.Post
* get_user_story(name) -> structures.Story
* get_hashtag_story(tag) -> structures.Story

#### Get Loads of Structures
For the methods in this section (unless specified), they returns a list if `preload=True`, a generator is returned otherwise.

* get_user_highlights(...) -> iterator[structures.Highlight]
* get_user_timeline_posts(...) -> iterator[structures.Post]
* get_self_saved_posts(...) -> iterator[structures.Post]
* get_user_tagged_posts(...) -> iterator[structures.Post]
* get_user_followers(...) -> iterator[structures.Profile] if `convert=True`, iterator[username] otherwise
* get_user_followings(...) -> iterator[structures.Profile] if `convert=True`, iterator[username] otherwise
* get_hashtag_posts(...) -> iterator[structures.Post]
* get_explore_posts(...) -> iterator[structures.Post]
* get_post_likes(...) -> iterator[structures.Profile] if `convert=True`, iterator[username] otherwise
* get_post_comments(...) -> iterator[dict{username, text, time}]
* get_profiles_from_file(...) -> iterator[structures.Profile]
* get_posts_from_file(...) -> iterator[structures.Post]

#### Download Structures

All of the above methods (except `get_user_followers`, `get_user_followings`, `get_post_likes`, `get_post_comments`, `get_profiles_from_file` and `get_posts_from_file`) each has a download method.

For more details, see the API docstring of each method in `instascraper.py`.

### Properties of Structures

You should only access the following specified fields and methods of the structures.

Calling other methods of the structures is deprecated as they are lower-level methods.

#### `Profile(session: requests.Session, name: str)`

1. as_dict() -> *dict*

* url -> *str*
* user_id -> *str*
* username -> *str*
* fullname -> *str*
* biography -> *str*
* website -> *str* or *None*
* followers_count -> *int*
* followings_count -> *int*
* mutual_followers_count -> *int*
* is_verified -> *bool*
* is_private -> *bool*
* profile_pic -> *str*
* story_highlights_count -> *int*
* timeline_posts_count -> *int*

#### `Post(session: requests.Session, shortcode: str)`

0. len()
1. obtain_media() -> *list[container.Container]*
2. as_dict() -> *dict*

* typename -> *str*
* url -> *str*
* shortcode -> *str*
* post_id -> *str*
* location_name -> *str* or *None*
* location_id -> *str* or *None*
* owner_username -> *str*
* owner_user_id -> *str*
* created_time -> *float*
* caption -> *str*
* media_count -> *int*
* likes_count -> *int*
* comments_count -> *int*

#### `IGTV(session: requests.Session, title: str, shortcode: str)`

0. len()
1. obtain_media() -> *list[container.Container]*
2. as_dict() -> *dict*

* typename -> *str*
* url -> *str*
* shortcode -> *str*
* post_id -> *str*
* location_name -> *str* or *None*
* location_id -> *str* or *None*
* owner_username -> *str*
* owner_user_id -> *str*
* created_time -> *float*
* caption -> *str*
* media_count -> *int*
* likes_count -> *int*
* comments_count -> *int*
* title -> *str*

#### `Story(session: requests.Session, user_id: str | tag: str | reel_id: str)`

0. len()
1. obtain_media() -> *list[container.Container]*

* typename -> *str*
* owner_name -> *str*
* id -> *str*
* created_time_list -> *list[float]*

#### `Highlight(session: requests.Session, title: str, reel_id: str)`

0. len()
1. obtain_media() -> *list[container.Container]*

* typename -> *str*
* owner_name -> *str*
* id -> *str*
* created_time_list -> *list[float]*
* title -> *str*

### Fields of `Container`

This class is used to storing media source data for downloading. You do not need to deal with this object in normal situation.

* typename -> *str*
* thumbnail -> *str*
* size -> *dict*
* video_duration -> *float* or *None*
* resources -> *str*
* src -> *str*

## Terminology

URL of a post from @9gag : `https://www.instagram.com/p/BtiGPG_AhXA/`

=> *BtiGPG_AhXA* is the shortcode of this post.

## Typenames

* GraphUser

* GraphSidecar (combination of videos or/and images)
  * GraphImage
  * GraphVideo

* GraphReel (user's story)
* GraphHighlightReel (user's story highlight)
* GraphMASReel (hashtag story)
  * GraphStoryImage
  * GraphStoryVideo

## Contributing

Feel free to open issues for bug reports and feature requests, or even better, make pull requests!
If you are reporting bugs, please include the log file in `~/.instascrape/instascrape.log`.

## Disclaimer

This project is in no way authorized, maintained or sponsored by Instagram. Use `InstaScrape` responsibly, do not use it for spamming or illegal activities.

We are not responsible for any kinds of negative actions that results from the use of `InstaScrape`. This is an independent and unofficial project. Use at your own risk.

<br>
<p align="center">Made with ❤️︎ by <a href="https://github.com/a1phat0ny">a1phat0ny</a><br>under <a href="./LICENSE.txt">MIT license</a></p>
