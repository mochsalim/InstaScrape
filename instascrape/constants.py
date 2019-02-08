BASE_URL = "https://instagram.com"

# Login & Logout
LOGIN_URL = BASE_URL + "/accounts/login/ajax/"
LOGOUT_URL = BASE_URL + "/accounts/logout"

# User
USER_URL = BASE_URL + "/{username}/?__a=1"
USER_ID_URL = "https://i.instagram.com/api/v1/users/{user_id}/info/"

# Post
POST_URL = BASE_URL + "/p/{shortcode}/?__a=1"

# Hashtag
HASHTAG_URL = BASE_URL + "/explore/tags/{tag}/?__a=1"

# Query Followers
QUERY_FOLLOWERS_URL = BASE_URL + "/graphql/query/?query_hash=56066f031e6239f35a904ac20c9f37d9&variables="
QUERY_FOLLOWINGS_URL = BASE_URL + "/graphql/query/?query_hash=c56ee0ae1f89cdbd1c89e2bc6b8f3d18&variables="

# Query Post Comments
QUERY_COMMENTS_URl = BASE_URL + "/graphql/query/?query_hash=f0986789a5c5d17c2400faebf16efd0d&variables="
# Query Post Likes
QUERY_LIKES_URL = BASE_URL + "/graphql/query/?query_hash=e0f59e4a1c8d78d0161873bc2ee7ec44&variables="

# Query User's Posts
QUERY_USER_MEDIA_URL = BASE_URL + "/graphql/query/?query_hash=66eb9403e44cc12e5b5ecda48b667d41&variables="
# Query User's Saved Posts
QUERY_USER_SAVED_URL = BASE_URL + "/graphql/query/?query_hash=8c86fed24fa03a8a2eea2a70a80c7b6b&variables="
# Query User's Tagged Posts
QUERY_USER_TAGGED_URL = BASE_URL + "/graphql/query/?query_hash=ff260833edf142911047af6024eb634a&variables="

# Query Hashtag Posts
QUERY_HASHTAG_URL = BASE_URL + "/graphql/query/?query_hash=f92f56d47dc7a55b606908374b43a314&variables="
# Query Discover Posts
QUERY_DISCOVER_URL = BASE_URL + "/graphql/query/?query_hash=ecd67af449fb6edab7c69a205413bfa7&variables="

# Query Search Results
QUERY_SEARCH_URL = BASE_URL + "/web/search/topsearch/?context=blended&query={query}"

# Query Stories
QUERY_STORIES_URL = BASE_URL + "/graphql/query/?query_hash=eb1918431e946dd39bf8cf8fb870e426&variables="

# User-Agent
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.113 Safari/537.36"
