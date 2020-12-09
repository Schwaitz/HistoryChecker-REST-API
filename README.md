# HistoryChecker API
An API for the HistoryChecker bot


## Endpoints

| Path      | Description | Methods |
| ----------- | ----------- | ----------- |
| GET, POST | /users | data for all users |
| GET, PUT, DELETE | /users/username | data for a single user |
| GET | /subreddits | data for all subreddits |
| GET | /subreddits/name | data for a single subreddit |
| GET, POST | /whitelist/subreddit | data for all whitelisted subreddits |
| GET, DELETE | /whitelist/subreddit/name | data for a single whitelisted subreddit |
| GET, POST | /whitelist/user | data for all whitelisted users |
| GET, DELETE | /whitelist/user/username | data for a single whitelisted user |
| GET, POST | /whitelist/usersubreddit | data for all whitelisted user/subreddit pairs |
| GET, PUT, DELETE | /whitelist/usersubreddit/name | data for a single whitelisted user/subreddit pair |