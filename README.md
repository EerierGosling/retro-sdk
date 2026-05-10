# retro sdk

this is an sdk to use the internal retro apis with python! the functions available are:

## authentication

- `get_refresh_token(token, verbose=False)` — exchange a custom token for a refresh token and store it
- ~~`send_code(phone_number, custom_data=None, verbose=False)` — send a verification SMS to a phone number (international format); returns `authenticationUuid`~~ doesn't work without a firebase app token!
- `send_code_v2(phone_number, verbose=False)` — v2 of send code
- `verify_code(code, authenticationUuid=None, verbose=False)` — verify the SMS code and authenticate the session

## profile & account

- `set_username(username, verbose=False)` — set the username for the authenticated user
- `profile_weeks(user_id, verbose=False)` — get the list of weeks for a user's profile
- `download_profile_photo(user_id, filename, output_path)` — download a user's profile photo to a local file

## media

- `get_media_metadata(user_id, week, filename)` — get metadata for a specific media file
- `list_files_in_folder(user_id, week)` — list all files in a user's week folder (raw response)
- `get_filenames_in_folder(user_id, week)` — get just the filenames in a user's week folder - only works if you're logged in as the user you're checking!
- `download_media_file(user_id, week, filename, output_path)` — download a media file to a local path

## friends

- `send_friend_request(user_id, verbose=False)` — send a friend request to a user
- `cancel_friend_request(user_id, verbose=False)` — cancel a pending friend request
- `unfriend(user_id, verbose=False)` — remove a friend
- `get_people_you_may_also_know(user_id, verbose=False)` — get suggested friends for a user

## search

- `search_users(username, page=0)` — search for users by username
- `get_user_id_from_username(username)` — look up a user's ID from their username

## utilities

- `set_last_checked_time(time)` — store a timestamp on the client instance
- `get_last_checked_time()` — retrieve the stored timestamp
- `get_auth_header()` — returns the Firebase auth header dict for manual requests
