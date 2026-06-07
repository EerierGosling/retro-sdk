# retro sdk

a python sdk for the internal retro apis!

## authentication

- `send_code(phone_number, verbose=False)` — send a verification SMS (international format, e.g. `+18556254225`)
- `verify_code(code, phone_number=None, verbose=False)` — verify the SMS code and authenticate the session
- `get_refresh_token(token, verbose=False)` — exchange a custom token for a refresh token and store it

## users

- `get_current_user_id()` — returns the UID of the authenticated user
- `get_user(user_id=None)` — get a user's profile data; defaults to the current user
- `set_username(username, verbose=False)` — set the username for the authenticated user
- `get_user_profile_picture(user_id)` — get a user's profile picture as a PIL Image
- `list_profile_photos(user_id)` — list filenames of a user's profile photos in Firebase Storage
- `download_profile_photo(user_id, filename)` — download a profile photo as a PIL Image
- `download_profile_photos(user_id)` — download all profile photos for a user

## media

- `get_week_media(user_id, week_id)` — get all media items for a user and week
- `get_week_id(owner_id, media_id)` — look up the week ID for a given post (tries existing comments, then walks profile weeks)
- `delete_media(week_id, media_id)` — delete one of your own media items
- `get_media_metadata(user_id, week, filename)` — get Firebase Storage metadata for a media file
- `list_files_in_folder(user_id, week)` — list raw Storage response for a user's week folder
- `get_filenames_in_folder(user_id, week)` — get filenames in a user's week folder
- `download_media_file(user_id, week, filename)` — download a media file as a PIL Image
- `download_image(storage_path)` — download any Firebase Storage file as a PIL Image

## comments

- `get_media_comments(owner_id, media_id)` — get all comments on a media item
- `post_comment(owner_id, media_id, text, week_id=None)` — post a comment; pass `week_id` when known (required for comment to appear in app)

## friends

- `get_friend_statuses(filter=None)` — get all friend relationships; optionally pass a `FieldFilter`
- `send_friend_request(user_id, verbose=False)` — send a friend request
- `cancel_friend_request(user_id, verbose=False)` — cancel a pending outbound friend request
- `accept_friend_request(user_id, verbose=False)` — accept an incoming friend request
- `reject_friend_request(user_id, verbose=False)` — reject an incoming friend request
- `unfriend(user_id, verbose=False)` — remove a friend
- `get_people_you_may_also_know(user_id, verbose=False)` — get suggested friends

## keys

- `send_key(user_id)` — give your key to a friend
- `revoke_key(user_id)` — take back a key you gave

## albums

- `get_album(album_id)` — get album metadata
- `get_album_media(album_id)` — get all media in an album
- `create_album(name, members=[], cover_font="roslindale", verbose=False)` — create a new album
- `add_album_member(album_id, user_ids)` — add members to an album
- `remove_album_member(album_id, user_id)` — remove a member from an album
- `make_album_admin(album_id, user_id)` — promote a member to admin

## notifications

- `get_notifications(type=None)` — get activity notifications; optionally filter by `"like"`, `"comment"`, `"request"`, or `"tag"`

## search

- `search_users(username, page=0)` — search for users by username via Algolia (no auth required)
- `get_user_id(username)` — look up a user's ID from their username

## profile weeks

- `profile_weeks(user_id, verbose=False)` — get the list of weeks a user has posted (requires friendship or key)
- `profile_weeks_v2(user_id, verbose=False)` — same as above, also returns `isNew`

## utilities

- `get_auth_token()` — returns the current auth token, refreshing if expired
- `get_auth_header()` — returns the Firebase auth header dict for manual requests
