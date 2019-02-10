import argparse
import traceback
import time
import json
import sys
import os
import logging
from datetime import datetime
from contextlib import contextmanager
from getpass import getpass

from colorama import (Fore, Style)

from . import ACCOUNT_DIR
from instascrape.__version__ import __version__
from instascrape.instascraper import InstaScraper
from instascrape.utils import (load_obj, dump_obj, remove_obj)
from instascrape.logger import set_logger
from instascrape.exceptions import InstaScrapeError


@contextmanager
def handle_errors(current_function_name: str = None, is_final: bool = False):
    """Any exceptions thrown inside this context is logged and printed out but they will not trigger program exit."""
    try:
        yield
    except KeyboardInterrupt:
        print()
        if is_final:
            err_print()
        else:
            err_print("Interrupted by user")
            ask("Contiune to next job")
    except InstaScrapeError as e:
        logger = logging.getLogger("instascrape")
        exc = sys.exc_info()
        exc = "".join(traceback.format_exception(*exc))
        logger.error(str(e))
        logger.debug(str(exc))
        info_print("(✗) Failed:", text="{0} because {1}".format(current_function_name + "()" + Fore.LIGHTRED_EX, Fore.RESET + Style.BRIGHT + str(e)), color=Fore.LIGHTRED_EX)
    except Exception as e:
        logger = logging.getLogger("instascrape")
        logger.critical(str(e), exc_info=True)
        info_print("(✗) Failed:", text="{0} because {1}".format(current_function_name + "()" + Fore.LIGHTRED_EX, Fore.RESET + Style.BRIGHT + str(e)), color=Fore.LIGHTRED_EX)
    finally:
        pass


def pretty_print(data, title: str = None):
    if title:
        print("\n ", Style.BRIGHT + "\033[4m[" + title + "]")
    if isinstance(data, dict):
        for key, value in data.items():
            print("·", key, end=": ")

            if "time" in key:
                print(Fore.LIGHTCYAN_EX + str(datetime.fromtimestamp(value)))

            # boolean
            elif isinstance(value, bool):
                if value:
                    print(Fore.LIGHTGREEN_EX + str(value))
                else:
                    print(Fore.LIGHTRED_EX + str(value))

            # integer
            elif isinstance(value, int):
                print(Fore.LIGHTCYAN_EX + str(value))

            # NoneType
            elif value is None:
                print(Fore.LIGHTBLACK_EX + str(value))

            # string or other types
            else:
                splitted = str(value).split("\n")
                print(Fore.LIGHTYELLOW_EX + splitted[0])
                for text in splitted[1:]:
                    print(" "*(len(key)+4) + Fore.LIGHTYELLOW_EX + text)
    else:
        # GeneratorType or List
        for i, item in enumerate(data, start=1):
            if isinstance(item, dict):
                print(Fore.LIGHTMAGENTA_EX + "[{0}]".format(i))
                pretty_print(item)
                print()
            else:
                print(Fore.LIGHTMAGENTA_EX + "[{0}]".format(i), Fore.LIGHTYELLOW_EX + str(item))


def ask(msg: str) -> bool:
    try:
        ans = input(Style.BRIGHT + "[?] " + Style.NORMAL + "{0} (y/n)? ".format(msg)).lower()
        if (ans != "y" and ans != "n") or not ans:
            return ask(msg)
        if ans == "n":
            err_print()
            sys.exit(255)
        return True
    except KeyboardInterrupt:
        sys.exit(255)


def err_print(msg: str = None):
    print(Fore.RED + Style.BRIGHT + "[x] " + Style.NORMAL + (msg or "Operation aborted"))


def warn_print(msg: str):
    print(Fore.YELLOW + Style.BRIGHT + "[!] " + Style.NORMAL + msg)


def info_print(msg: str, text: str = None, color: str = None):
    if not color:
        color = ""

    s = color + "* " + Style.BRIGHT + msg
    if text:
        s += " " + Fore.RESET + text
    print(s)


def login(args: argparse.Namespace):
    username = args.username
    cookie_file = args.cookie
    insta = load_obj()
    my_username = insta.my_username if insta else ""

    if cookie_file:
        un = pw = None
    elif username:
        # username already provided as command-line arguments
        filenames = []
        for cookie in os.listdir(ACCOUNT_DIR):
            filename, ext = os.path.splitext(cookie)
            filenames.append(filename)

        un = username.strip()
        if username in filenames:
            pw = None
        else:
            info_print("Cookie file does not exist yet. Getting credentials...")
            pw = getpass()
            if not pw.strip():
                parser.error("password should not be empty")
    else:
        # List all saved local cookies
        filenames = []  # store raw filenames without the `.cookie` extension
        cookies = os.listdir(ACCOUNT_DIR)
        print(Style.BRIGHT + "\n    \033[4m" + "Choose Account\n")
        for i, cookie in enumerate(cookies, start=1):
            filename, ext = os.path.splitext(cookie)
            filenames.append(filename)
            # get last modify (login) time
            try:
                mtime = time.ctime(os.path.getmtime(ACCOUNT_DIR + cookie))
            except OSError:
                mtime = time.ctime(os.path.getctime(ACCOUNT_DIR + cookie))
            # print
            sign = " "
            if filename == my_username:
                # current logged in account: use symbol '*'
                sign = Fore.YELLOW + "*"
            print(Fore.MAGENTA + "({0})".format(i), sign, filename)
            print(Fore.CYAN + "Last login:", Style.DIM + mtime)
            print()
        # handle cases when a account is logged in but cookie was deleted from dsik
        if insta and my_username not in filenames:
            print(Fore.RED + "(x)", Fore.YELLOW + "*", my_username)
            print(Fore.LIGHTBLACK_EX + "Cookie Not Found: deleted from disk\n")
        # Option for logging in a new account
        print(Fore.MAGENTA + "({0})".format(len(cookies) + 1), Fore.GREEN + "+", "Login New Account\n")

        # Prompt
        try:
            choice = input("choice> ")
        except KeyboardInterrupt:
            return
        if not choice.isdigit() or not 0 < int(choice) <= len(cookies) + 1:
            parser.error("invalid choice")
        choice = int(choice)

        if choice == len(cookies) + 1:
            # login to new account
            un = input("Username: ")
            pw = getpass()
            if not all((un.strip(), pw.strip())):
                parser.error("credentials must not be empty")
            if un in filenames:
                info_print("Cookie already exists. Using local saved cookie of the same username.")
        else:
            # use lcoal cookie
            un = filenames[choice-1]
            pw = None

    # Warn users if they had already logged in to an account
    if insta and not cookie_file:
        warn_print("You've already logged in as '{0}'".format(my_username))
        ask("Log out from current account and log in to '{0}'".format(un))
    # Initialize and login with `InstasSraper` object
    insta = InstaScraper(username=un, password=pw, cookie=cookie_file)  # ! no need to provide `level`, as the logger was set up in `main()`.
    insta.login()  # keep the logged in state and store it in the pickle
    dump_obj(insta)
    info_print("Logged in as '{0}'".format(insta.my_username), color=Fore.LIGHTBLUE_EX)


def logout(args: argparse.Namespace):
    if args.real:
        insta = load_obj()
        if not insta:
            err_print("You haven't logged in to any account.")
            return
        insta.logout()
    remove_obj()
    info_print("Logged out", color=Fore.LIGHTBLUE_EX)


def dump(args: argparse.Namespace):
    targets = args.user
    count = args.count
    outfile = args.outfile

    if not targets:
        parser.error("one dump type must be specified")
    if len(targets) > 1:
        parser.error("cannot dump more than one type")

    insta = load_obj()
    if not insta:
        err_print("No account logged in")
        return

    kwargs = {"count": count or 50}
    ex_kwargs = {"count": count or 50, "convert": False}
    jobs = []

    target = targets[0]
    if len(target) < 2:
        parser.error("illegal argument parsed in '{0}'".format(target))
    arg = target[1:]

    if target[0] == "@":
        if args.likes or args.comments:
            parser.error("-likes, -comments: not allowed with @user type")

        if not args.followers and not args.followings:
            if args.count:
                parser.error("--count: not allowed with argument @user")
            jobs.append((insta.get_profile, (arg,), {}, target, "User Information {0}"))
        else:
            if args.followers:
                jobs.append((insta.get_user_followers, (arg,), ex_kwargs, target, "User Followers {0}"))
            if args.followings:
                jobs.append((insta.get_user_followings, (arg,), ex_kwargs, target, "User Followings {0}"))

    elif target[0] == ":":
        if args.followers or args.followings:
            parser.error("-followers, -followings: not allowed with :post type")

        if not args.likes and not args.comments:
            if args.count:
                parser.error("--count: not allowed with argument :post")
            jobs.append((insta.get_post, (arg,), {}, target, "Post Information {0}"))
        else:
            if args.likes:
                jobs.append((insta.get_post_likes, (arg,), ex_kwargs, target, "Post Likes {0}"))
            if args.comments:
                jobs.append((insta.get_post_comments, (arg,), kwargs, target, "Post Comments {0}"))

    else:
        parser.error("illegal symbol parsed in argument: '{0}'".format(target))

    print(Fore.YELLOW + "Current User:", Style.BRIGHT + insta.my_username)
    if count:
        print(Fore.YELLOW + "Count:", Style.BRIGHT + str(count or 50))

    for i, (function, arguments, kwarguments, string, title) in enumerate(jobs, start=1):
        print()
        with handle_errors(current_function_name=function.__name__, is_final=i == len(jobs)):
            info_print("(Dump) {0}".format(function.__name__.title().replace("_", " ")), text=string if string else None, color=Fore.LIGHTBLUE_EX)
            result = function(*arguments, **kwarguments)
            data = result.as_dict() if hasattr(result, "as_dict") else result
            if not data:
                info_print("(✗) Dump Failed", color=Fore.LIGHTRED_EX)
                return
            if outfile:
                # save to file
                path = os.path.abspath(outfile)
                if isinstance(data, dict):
                    # => JSON
                    with open(path, "w+") as f:
                        json.dump(data, f, indent=4)
                else:
                    # => txt
                    with open(path, "w+") as f:
                        buffer = []
                        for item in data:
                            if isinstance(item, dict):  # comments
                                buffer.append(item)
                            else:
                                f.write("@" + str(item) + "\n")
                        if buffer:
                            json.dump(buffer, f, indent=4)
                # done
                info_print("(✓) Dump Succeeded =>", text=path, color=Fore.LIGHTGREEN_EX)
            else:
                # print to stdout
                pretty_print(data, title.format(string))


def down(args: argparse.Namespace):
    targets = args.profile
    count = args.count
    only = args.only
    dest = args.dest
    preload = args.preload
    dump_metadata = args.dump_metadata

    if not targets and not args.explore and not args.saved:
        parser.error("at least one media type must be specified")

    insta = load_obj()
    if not insta:
        err_print("No account logged in")
        return

    # ========== Prepare arguments & jobs ==========

    kwargs = {"count": count or 50, "only": only, "dest": dest, "preload": preload, "dump_metadata": dump_metadata}
    ex_kwargs = {"dest": dest}  # -> kwargs for individuals

    has_individual = False  # -> has one of 'story', 'post', 'profile-pic'
    profile_jobs = []  # -> profile job queue -> tuple(target text, list[tuple(function, (args), kwargs, target text),...])
    jobs = []  # job queue -> tuple(function, (args), kwargs, target text)

    for target in targets:
        if len(target) < 2:
            parser.error("illegal argument parsed in '{0}'".format(target))

        if target[0] == "@":  # user
            if target[1] == "#":  # tagged
                jobs.append((insta.download_user_tagged_posts, (target[2:],), kwargs, target))
            else:  # timeline
                jobs.append((insta.download_user_timeline_posts, (target[1:],), kwargs, target))

        elif target[0] == "#":  # hashtag
            jobs.append((insta.download_hashtag_posts, (target[1:],), kwargs, target))

        elif target[0] == "%":  # story
            if target[1] == "@":  # user
                story_args = (target[2:], None)
            elif target[1] == "#":  # hashtag
                story_args = (None, target[2:])
            else:
                parser.error("illegal symbol parsed in argument: '{0}'".format(target))
            has_individual = True
            jobs.append((insta.download_story, story_args, ex_kwargs, target))

        elif target[0] == ":":  # post
            has_individual = True
            jobs.append((insta.download_post, (target[1:],), ex_kwargs, target))

        elif target[0] == "/":  # profile-pic
            has_individual = True
            jobs.append((insta.download_user_profile_pic, (target[1:],), ex_kwargs, target))

        elif target[0].isalpha() or target[0].isdigit():  # profile
            # specify a new path as to create a seperate directory for storing the whole profile media
            profile_path = os.path.join(dest or "./", target)
            profile_kwargs = kwargs.copy()
            profile_ex_kwargs = ex_kwargs.copy()
            profile_kwargs.update({"dest": profile_path})
            profile_ex_kwargs.update({"dest": profile_path})
            temp = [
                (insta.download_user_timeline_posts, (target,), profile_kwargs),
                (insta.download_user_tagged_posts, (target,), profile_kwargs),
                (insta.download_story, (target, None), profile_ex_kwargs),
                (insta.download_user_profile_pic, (target,), profile_ex_kwargs)
            ]
            profile_jobs.append((target, temp))

        else:
            parser.error("illegal symbol parsed in argument: '{0}'".format(target))

    if args.saved:  # saved
        jobs.append((insta.download_self_saved_posts, (), kwargs, None))
    if args.explore:  # explore
        jobs.append((insta.download_explore_posts, (), kwargs, None))

    # Handle profiles download
    if profile_jobs and jobs:
        # arguments conflict -> cannot download both profiles and other types at the same time
        parser.error("cannot specify download both 'profile' type and other types of media at the same time")

    # ========== Download jobs ==========

    print(Fore.YELLOW + "Current User:", Style.BRIGHT + insta.my_username)
    if not has_individual:
        print(Fore.YELLOW + "Count:", Style.BRIGHT + str(count or 50))
    if has_individual and any((count, only, preload, dump_metadata)):
        warn_print("--count, --only, --preload --dump-metadata: not allowed with argument profile_pic (/), post (:), story (%@) (%#)")

    # Handle profile jobs
    if profile_jobs:
        for target, profiles in profile_jobs:
            print("\n" + Style.BRIGHT + Fore.LIGHTCYAN_EX + "=> (~) " + "\033[4mDownloading User Profile:", Style.BRIGHT + "\033[4m@{0}".format(target))
            for i, (function, arguments, kwargs) in enumerate(profiles, start=1):
                print()
                with handle_errors(current_function_name=function.__name__, is_final=i == len(jobs)):
                    info_print("(↓) {0}".format(function.__name__.title().replace("_", " ")), text=target if target else None, color=Fore.LIGHTBLUE_EX)
                    # deepcopy `InstaScraper` object to ensure better safety
                    path = function(*arguments, **kwargs)
                    if path is None:
                        # no download destination path returned because the download failed
                        info_print("(✗) Download Failed", color=Fore.LIGHTRED_EX)
                    else:
                        info_print("(✓) Download Completed =>", text=path, color=Fore.LIGHTGREEN_EX)
            print("\n" + Style.BRIGHT + Fore.LIGHTCYAN_EX + "=> (*) " + "\033[4mCompleted User Profile:", Style.BRIGHT + "\033[4m@{0}".format(target))

    # Handle seperate jobs
    if jobs:
        # retrieve functions and arguments from the job queue
        for i, (function, arguments, kwargs, target) in enumerate(jobs, start=1):
            print()
            with handle_errors(current_function_name=function.__name__, is_final=i == len(jobs)):
                info_print("(↓) {0}".format(function.__name__.title().replace("_", " ")), text=target if target else None, color=Fore.LIGHTBLUE_EX)
                # deepcopy `InstaScraper` object to ensure better safety
                path = function(*arguments, **kwargs)
                if path is None:
                    # no download destination path returned because of download failed
                    info_print("(✗) Download Failed", color=Fore.LIGHTRED_EX)
                else:
                    info_print("(✓) Download Completed =>", text=path, color=Fore.LIGHTGREEN_EX)


def main(argv=None):
    global parser
    description = Style.BRIGHT + "    \033[4mInstaScrape" + Style.RESET_ALL + " -- A {f.LIGHTBLUE_EX}fast{f.RESET} and {f.LIGHTGREEN_EX}lightweight{f.RESET} Instagram media downloader".format(f=Fore)
    epilog = Style.BRIGHT + "Made with {f.LIGHTRED_EX}❤{f.RESET} by AlphaXenon".format(f=Fore) + Style.RESET_ALL + " (https://github.com/AlphaXenon/InstaScrape)"
    parser = argparse.ArgumentParser(prog="instascrape", description=description, epilog=epilog, allow_abbrev=False, formatter_class=argparse.RawTextHelpFormatter)
    parser._positionals.title = "Actions"
    parser._positionals.description = "Reminder: You may need to login first."
    parser._optionals.title = "Options"
    parser.add_argument("--version", action="version", version="instascrape-ax {0}".format(__version__))
    group = parser.add_mutually_exclusive_group()
    group.add_argument("-d", "--debug", help="show detailed logging messages (level: DEBUG)", default=False, action="store_true")
    group.add_argument("-q", "--quiet", help="suppress logging messages output (level: ERROR)", default=False, action="store_true")
    subparsers = parser.add_subparsers()

    login_parser = subparsers.add_parser("login", help="Login to Instagram and choose account (cookie)")
    login_parser.set_defaults(func=login)

    l_group = login_parser.add_mutually_exclusive_group()
    l_group.add_argument("-u", "--username", type=str, metavar="<username>",
                         help="skip interactive login process, try loging in to this user")
    l_group.add_argument("-c", "--cookie", type=str, metavar="<path/to/file>", dest="cookie",
                         help="provide path to the cookie file")  # FIXME: implement

    logout_parser = subparsers.add_parser("logout", help="Logout from current account")
    logout_parser.set_defaults(func=logout)
    logout_parser.add_argument("-r", "--real", help="send POST request to really logout from Instagram & delete the local saved cookie", default=False, action="store_true")

    dump_parser = subparsers.add_parser("dump", help="Dump target data to file or print to stdout", usage="instascrape dump [type] [[flag][option]...]")
    dump_parser.set_defaults(func=dump)
    dump_types = dump_parser.add_argument_group("Dump Types")
    dump_types.add_argument("user", type=str, metavar="@username", nargs="*",
                            help="Dump information of a user by username [JSON] (@)")
    dump_types.add_argument("post", type=str, metavar=":shortcode", nargs="*",
                            help="Dump information of a post by shortcode [JSON] (:)")
    user_flags = dump_parser.add_argument_group("User Type Flags")
    user_flags.add_argument("-followers", action="store_true",
                            help="Dump a list of followers of a user [txt] (@username)")
    user_flags.add_argument("-followings", action="store_true",
                            help="Dump a list of followings of a user [txt] (@username)")
    post_flags = dump_parser.add_argument_group("Post Type Flags")
    post_flags.add_argument("-likes", action="store_true",
                            help="Dump a list of users who liked the post [txt] (:shortcode)")
    post_flags.add_argument("-comments", action="store_true",
                            help="Dump comments of a post [JSON] (:shortcode)")
    flag_options = dump_parser.add_argument_group("Flag Options")
    flag_options.add_argument("--count", type=int, metavar="<integer>",
                              help="Set maximum count of items to dump (default: 50)")
    dump_options = dump_parser.add_argument_group("Dump Options")
    dump_options.add_argument("-o", "--outfile", type=str, metavar="<path/to/file>",
                              help="Dump data output to the file in a proper format i.e. JSON / txt")

    down_parser = subparsers.add_parser("down", help="Download media from target(s)", usage="instascrape down [[type]...] [[option]...]")
    down_parser.set_defaults(func=down)
    media_types = down_parser.add_argument_group("Media Types")
    media_types.add_argument("profile", metavar="PROFILE", nargs="*",
                             help="Download all types of media of a user by username")
    media_types.add_argument("user", type=str, metavar="@username", nargs="*",
                             help="Download timeline posts media of a user by username (@)")
    media_types.add_argument("tagged", type=str, metavar="@#username", nargs="*",
                             help="Download tagged posts media of a user by username (@#)")
    media_types.add_argument("profile_pic", type=str, metavar="/username", nargs="*",
                             help="Download the profile picture of a user by username (/)")
    media_types.add_argument("post", type=str, metavar=":shortcode", nargs="*",
                             help="Download media of a post by shortcode (:)")
    media_types.add_argument("story", type=str, metavar="%@username/%#hashtag", nargs="*",
                             help="Download stories media of a user by username or by hashtag name (%%@) (%%#)")
    media_types.add_argument("hashtag", type=str, metavar="#hashtag", nargs="*",
                             help="Download posts media by hashtag name (#)")
    media_types.add_argument("-explore", action="store_true",
                             help="Download media of posts in the explore feed section (-flag)")
    media_types.add_argument("-saved", action="store_true",
                             help="Download saved posts media of yourself (-flag)")
    down_options = down_parser.add_argument_group("Options")
    down_options.add_argument("--count", type=int, metavar="<integer>",
                              help="Set maximum count of items to download (default: 50)")
    down_options.add_argument("--only", choices=["image", "video", "sidecar"], type=str,
                              help="Filter out others, only download this type of media")
    down_options.add_argument("--dest", type=str, metavar="<path/to/directory>",
                              help="Set path to the destination of download (default: .)")
    down_options.add_argument("--preload", action="store_true",
                              help="Might help increase the speed of download by collecting the initial data of all items before downloading "
                                   "(WARN: this option is unstable and should only be used when downloading a small amount of posts, might get rate limited by Instagram)")
    down_options.add_argument("--dump-metadata", action="store_true",
                              help="Dump metadata of each post to JSON files")

    args = parser.parse_args(argv[1:] if argv else None)

    # setup logger everytime the program starts, before executing anything
    level = 20  # INFO
    if args.quiet:
        level = 40  # ERROR
    elif args.debug:
        level = 10  # DEBUG
    set_logger(level)

    try:
        args.func
    except AttributeError:
        parser.print_help()
    else:
        args.func(args)
