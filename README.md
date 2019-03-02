<h1 align="center">InstaScrape</h1>

<p align="center"><em>A fast and lightweight Instagram media downloader (without the need of API)</em></p>

<p align="center"><img src="./demo.gif?raw=true" width=70%></p>

<p align="center">
  <a href="https://pypi.python.org/pypi/InstaScrape"><img src="https://img.shields.io/pypi/v/instascrape-ax.svg"></a>
  <a href="https://pypi.python.org/pypi/InstaScrape"><img src="https://img.shields.io/pypi/dm/instascrape-ax.svg"></a>
  <a href="./LICENSE.txt"><img src="https://img.shields.io/github/license/a1phat0ny/InstaScrape.svg"></a>
</p>

**InstaScrape** is a lightweight command-line utility (and API) for downloading large amount of photos and videos ([see the list](#media-types)) from Instagram.

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
  - [InstaScraper Methods](#instascraper-methods)
  - [Structure Fields](#structure-fields)
  - [Container Fields](#container-fields)
- [Typenames](#typenames)
- [Todos](#todos)
- [Contributing](#contributing)
- [Disclaimer](#disclaimer)

## Features

* Fancy interface with colors ✨
* Fast as lightning,️ with multithreading scrape support ⚡
* Efficient, use generators (yield) 💪🏻
* Yield data to prevent getting rate limited by Instagram
* Manage cookies and multiple accounts easily 🍪
* Download posts along with their metadata
* Job queue to handle multiple download tasks 🏃🏻‍
* Good exceptions handling ⚠️
* Download posts created in a particular time period 🕓

## Why

Have you ever seen some beautiful and attractive photos on Instagram that you wanted to download ?

> Of course ! 🤩

Have you ever came across someone on Instagram that you would really like to make a collection of all her media ?

> Hell yeah ! 😍

Then, **InstaScrape** really helps you solve the problem !

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

Example output, if `-u/--username` and `-c/--cookie` are not specified:
```
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

In this situation, `user3` is logged in. The `InstaScraper` object is saved and being used by `user3`, but the cookie file is already gone.
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
  * followers `-followers` : followers of the user in plain text, one username per line in the pattern of `@username`
  * followings `-followings` : followings of the user in plain text, one username per line in the pattern of `@username`
* **Post `:shortcode`** post information in JSON format
  * likes `-likes` : users who liked the post in plain text, one username per line in the pattern of `@username` 
  * comments `-comments` : comments of the post in JSON format

#### Flag Option

* `--count <integer>` : set maximum count of items you want to get

#### Dump Options

* `-o/--outfile <path/to/file>` : dump data to file in a proper format

Example output of `$ instascrape dump :BtlyjD2lWvL`:
```
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
* `#hashtag` : download posts of the hashtag
* `-explore` : download posts of explore feed
* `-saved` : download self saved posts

#### Options

* `--count <integer>` : set maximum count of items you want to get

* `--only {image, video, sidecar}` : filter out other types of posts, only download this type of posts (by typename)

* `--dest <path/to/directory>` : set path to the download destination

* `--preload` : collect the initial data of all items (using thread workers) before downloading them, might help increase the speed.
*WARN: use at your own risk, this option is unstable and should only be used when downloading small amount of posts, otherwise you may get rate limited*.

* `--before-date <datetime>` : download posts created before this datetime, can be used with `after-date` (`{YY-mm-dd-h:m:s}`)

* `--after-date <datetime>` : download posts created after this datetime, can be used with `before-date` (`{YY-mm-dd-h:m:s}`)

* `--dump-metadata` : download posts along with their metadata dumped in JSON files

***NOTE:** Posts downloaded will be named in the pattern `{YY-mm-dd-h:m:s}_{shortcode}` e.g. `2019-02-06-15:57:39_BtiGPG_AhXA`.*

---

## API

**InstaScrape** also provides an easy to use API with context manager implemented.

```python
from instascrape import InstaScraper

# InstaScraper will login when entered
with InstaScraper(username, password, user_agent=None, cookie=None, save_cookie=True, logout=True) as insta:
    insta.do_something()
# InstaScraper will automatically log out when closed
```

***NOTE:** You should always access `InstaScraper` with its context manager to ensure better security and prevent breaking.* 

### InstaScraper Methods

Top-level API methods.

#### Account Interactions
* login()
* logout()

#### Get Independent Structure
* get_profile(name) -> structures.Profile
* get_post(shortcode) -> structures.Post
* get_story(name | tag) -> structures.Story

#### Get loads of Structures
For the methods in this section (unless specified), they returns a list if `preload=True`, a generator otherwise.

* get_user_timeline_posts(...) -> [structures.Post]
* get_self_saved_posts(...) -> [structures.Post]
* get_user_tagged_posts(...) -> [structures.Post]
* get_user_followers(...) -> [structures.Profile] if `convert=True`, list[str] otherwise
* get_user_followings(...) -> [structures.Profile] if `convert=True`, list[str] otherwise
* get_hashtag_posts(...) -> [structures.Post]
* get_explore_posts(...) -> [structures.Post]
* get_post_likes(...) -> [structures.Profile] if `convert=True`, list[str] otherwise
* get_post_comments(...) -> list[dict{<username>, <text>, <time>}]

#### Download Individuals

All of the above methods (except `get_user_followers`, `get_user_followings`, `get_post_likes` and `get_post_comments`) each has a download method.

For more details, see the docstring of each method.

### Structure Fields

The following properties are lower level.

#### Profile

1. as_dict() -> *dict*

* url -> *str*
* user_id -> *str*
* username -> *str*
* fullname -> *str*
* biography -> *str*
* website -> *str* or *None*
* followers_count -> *int*
* followings_count -> *int*
* is_verified -> *bool*
* is_private -> *bool*
* profile_pic -> *str*
* story_highlights_count -> *int*
* timeline_posts_count -> *int*

#### Post

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

#### Story

0. len()
1. obtain_media() -> *list[container.Container]*

* typename -> *str*
* name -> *str*
* id -> *str*
* created_time_list -> *list[float]*

### Container Fields

This object is used to storing media source data for downloading. You do not need to deal with this object normally.

* typename -> *str*
* thumbnail -> *str*
* size -> *dict*
* video_duration -> *float* or *None*
* resources -> *str*

## Terminology

[1] URL of a post from @9gag : `https://www.instagram.com/p/BtiGPG_AhXA/`

=> *BtiGPG_AhXA* is the shortcode of this post.

[2] In the world of `InstaScrape`, `@` and `:` are symbols to classify a User and a Post respectively.

## Typenames

Just for your reference.

### User
* GraphUser

### Hashtag
* GraphHashtag

### Post
* GraphSidecar (combination of videos or/and images)
  * GraphImage
  * GraphVideo

### Story
* GraphReel (user story)
* GraphHighlightReel (user's story highlights)
* GraphMASReel (hashtag story)
  * GraphStoryImage
  * GraphStoryVideo

## Todos

1. [x] Download posts created between two particular timestamps
2. [ ] Read shortcodes and usernames from file
3. [ ] Download story highlights
4. [ ] Guest login

## Contributing

Feel free to open issues for bug reports and feature requests, or even better, make pull requests!
If you are reporting bugs, please include the log file in `~/.instascrape/instascrape.log`.

## Disclaimer

This project is in no way authorized, maintained or sponsored by Instagram. Use `InstaScrape` responsibly, do not use it for spamming or illegal activities.

We are not responsible for any kinds of negative actions that results from the use of `InstaScrape`. This is an independent and unofficial project. Use at your own risk.

<br>
<p align="center">Made with ❤️︎ by <a href="https://github.com/a1phat0ny">a1phat0ny</a><br>under <a href="./LICENSE.txt">MIT license</a></p>
