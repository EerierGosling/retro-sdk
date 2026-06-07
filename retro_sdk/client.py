import io
import base64
import json
import time
import uuid
import urllib.parse
import requests
from PIL import Image
from google.oauth2.credentials import Credentials
from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter
from google.api_core.exceptions import PermissionDenied

class Retro:
    """
    A client for interacting with the Retro API.
    """

    def __init__(self, refresh_token=None) -> None:
        """Initializes the Retro client."""
        self.refresh_token = refresh_token
        self.auth_token = None
        self.web_api_key = "AIzaSyDVXcY0s4ZeREh43EYzsHqbEWcCJ6Ism5w"
        if refresh_token:
            self._refresh_auth_token()

    def _refresh_auth_token(self) -> None:
        """Refreshes the auth token using the refresh token."""
        url = f"https://securetoken.googleapis.com/v1/token?key={self.web_api_key}"
        payload = {"grantType": "refresh_token", "refreshToken": self.refresh_token}
        r = requests.post(url, json=payload)
        try:
            r.raise_for_status()
        except requests.HTTPError:
            print(f"Error: {r.text}")
            raise
        self.auth_token = r.json().get("access_token")

    def get_auth_token(self) -> str | None:
        """Returns the current auth token, refreshing it if necessary."""
        if not self.auth_token:
            return None
        payload = self.auth_token.split(".")[1]
        payload += "=" * (4 - len(payload) % 4)
        claims = json.loads(base64.b64decode(payload))
        if claims["exp"] < time.time():
            self._refresh_auth_token()
        return self.auth_token

    def get_auth_header(self) -> dict[str, str]:
        """Returns the authorization header for authenticated requests."""
        return {"Authorization": f"Firebase {self.get_auth_token()}"}

    def get_refresh_token(self, token, verbose=False) ->  None | dict:
        """
        Exchanges an ID token for a refresh token.
        
        Returns the refresh token string. If `verbose=True`, returns the full response from the server.
        """
        url = f"https://www.googleapis.com/identitytoolkit/v3/relyingparty/verifyCustomToken?key={self.web_api_key}"
        headers = {"content-type": "application/json"}
        payload = {"token": token, "returnSecureToken": True}
        r = requests.post(url, headers=headers, json=payload)
        try:
            r.raise_for_status()
        except requests.HTTPError:
            print(f"Error: {r.text}")
            raise
        r_json = r.json()
        self.refresh_token = r_json["refreshToken"]
        print(r_json)
        if not verbose:
            return
        return r_json
    
    def send_code(self, phone_number, custom_data=None, verbose=False) -> None | dict: # https://us-central1-retro-media.cloudfunctions.net/sendCode was removed - v2 is the only one left
        """
        Phone number must be in international format (e.g `+18556254225`).
        
        `custom_data` can be used to send additional data to the server. Requests from the app follow this format:
        
        ```
        {
            "data": {
                "deviceId": str,            
                "appVersion": str,
                "phoneNumber": str,
                "platform": str,
                "osVersion": str,
                "dispatchId": str,
                "deviceModel": str
            }
        }
        ```

        If `verbose=True`, returns the full response from the server which is in the format:
        ```
        {
            "result": {
                "authenticationUuid": str
            }
        }
        ```
        `authenticationUuid` was used in the previous `/verifyCode` endpoint and is no longer used in the new `/verifyCodeV2` endpoint - replaced by `phoneNumber`.
        
        """

        url = "https://us-central1-retro-media.cloudfunctions.net/sendCodeV2"
        headers = {"content-type": "application/json"}
        if custom_data==None:
            payload = {
                    "data": {
                        "phoneNumber": phone_number
                    }
                }
        else:
            payload = custom_data

        r = requests.post(url, headers=headers, json=payload)
        try:
            r.raise_for_status()
        except requests.HTTPError:
            print(f"Error: {r.text}")
            raise
        r_json = r.json()
        self.phone_number = phone_number
        if verbose:
            return r_json
    
    def verify_code(self, code, phone_number=None, verbose=False) -> bool | dict: # https://us-central1-retro-media.cloudfunctions.net/verifyCode was removed - v2 is the only one left
        """
        Verifies the code sent to the user's phone number. Adds the authentication token to the client if successful. Returns `True` if the code was correct, `False` otherwise.

        If `verbose=True`, returns the full response from the server which is in the format:
        ```
        {
            'kind': str,          # e.g. 'identitytoolkit#VerifyCustomTokenResponse'
            'idToken': str,
            'refreshToken': str,
            'expiresIn': str,     # e.g. '3600'
            'isNewUser': bool
        }
        ```
        """
        url = "https://us-central1-retro-media.cloudfunctions.net/verifyCodeV2"
        headers = {"content-type": "application/json"}
        payload = {"data": {"phoneNumber": phone_number if phone_number else self.phone_number, "code": code}}
        r = requests.post(url, headers=headers, json=payload)
        try:
            r.raise_for_status()
        except requests.HTTPError:
            print(f"Error: {r.text}")
            return False
        r_json = r.json()
        self.auth_token = r_json["result"]["token"]
        self.get_refresh_token(self.auth_token)
        if not verbose:
            return True
        return r_json

    def list_profile_photos(self, user_id) -> list[str]:
        url = "https://firebasestorage.googleapis.com/v0/b/retro-media-multi/o"
        r = requests.get(url, headers=self.get_auth_header(), params={"prefix": f"profilePhotos/{user_id}/", "delimiter": "/"})
        try:
            r.raise_for_status()
        except requests.HTTPError:
            print(f"Error: {r.text}")
            raise
        items = r.json().get("items", [])
        return [item["name"].split("/")[-1] for item in items]

    def download_image(self, storage_path) -> Image.Image:
        encoded = urllib.parse.quote(storage_path, safe="")
        url = f"https://firebasestorage.googleapis.com/v0/b/retro-media-multi/o/{encoded}?alt=media"
        r = requests.get(url, headers=self.get_auth_header())
        try:
            r.raise_for_status()
        except requests.HTTPError:
            print(f"Error: {r.text}")
            raise
        return Image.open(io.BytesIO(r.content))

    def download_profile_photos(self, user_id) -> list[Image.Image]:
        return [self.download_profile_photo(user_id, f) for f in self.list_profile_photos(user_id)]

    def download_profile_photo(self, user_id, filename) -> Image.Image:
        return self.download_image(f"profilePhotos/{user_id}/{filename}")

    def get_media_metadata(self, user_id, week, filename) -> dict:
        url = f"https://firebasestorage.googleapis.com/v0/b/retro-media-multi/o/media%2F{user_id}%2F{week}%2F{filename}"
        r = requests.get(url, headers=self.get_auth_header())
        try:
            r.raise_for_status()
        except requests.HTTPError:
            print(f"Error: {r.text}")
            raise
        return r.json()

    def list_files_in_folder(self, user_id, week) -> dict:
        url = "https://firebasestorage.googleapis.com/v0/b/retro-media-multi/o"
        r = requests.get(url, headers=self.get_auth_header(), params={"prefix": f"media/{user_id}/{week}/", "delimiter": "/"})
        try:
            r.raise_for_status()
        except requests.HTTPError:
            print(f"Error: {r.text}")
            raise
        return r.json()

    def get_filenames_in_folder(self, user_id, week) -> list[str]:
        data = self.list_files_in_folder(user_id, week)
        items = data.get("items", [])
        return [item["name"] for item in items] if items else []

    def download_media_file(self, user_id, week, filename) -> Image.Image:
        return self.download_image(f"media/{user_id}/{week}/{filename}")
    
    def profile_weeks(self, user_id, verbose=False) -> list | dict:
        """
        Returns a list of weeks (e.g ["2026_01", "2026_02", ...]).
        
        Only returns weeks if `user_id` is the current user or a user that `user_id` has a key for.
        """
        url = "https://us-central1-retro-media.cloudfunctions.net/profileWeeks"
        headers = {"content-type": "application/json", "Authorization": f"Bearer {self.get_auth_token()}"}
        payload = {"data": {"uid": user_id}}
        r = requests.post(url, headers=headers, json=payload)
        try:
            r.raise_for_status()
        except requests.HTTPError:
            print(f"Error: {r.text}")
            raise
        r_json = r.json()
        if verbose:
            return r_json
        return r_json["result"]
    
    def profile_weeks_v2(self, user_id, verbose=False) -> dict: # only difference between this and v1 is that this returns whether or not the user is new as well
        """
        Returns a list of weeks the user has posted (e.g `["2026_01", "2026_02", ...]`) and whether or not the user is new.
        _Only returns weeks if `user_id` is the current user or a user that `user_id` has a key for._

        Return format:
        ```
        {
            "weeks": list[str],
            "isNew": bool
        }
        ```
        """
        url = "https://us-central1-retro-media.cloudfunctions.net/profileWeeksV2"
        headers = {"content-type": "application/json", "Authorization": f"Bearer {self.get_auth_token()}"}
        payload = {"data": {"uid": user_id}}
        r = requests.post(url, headers=headers, json=payload)
        try:
            r.raise_for_status()
        except requests.HTTPError:
            print(f"Error: {r.text}")
            raise
        r_json = r.json()
        if verbose:
            return r_json
        return r_json["result"]
    
    def set_username(self, username, verbose=False) -> bool | dict:
        """
        Sets the username for the current user. Returns `True` if successful, `False` otherwise.

        If `verbose=True`, returns the full response from the server.
        """
        url = "https://us-central1-retro-media.cloudfunctions.net/setUsername"
        headers = {"content-type": "application/json", "Authorization": f"Bearer {self.get_auth_token()}"}
        payload = {"data": {"username": username}}
        r = requests.post(url, headers=headers, json=payload)
        try:
            r.raise_for_status()
        except requests.HTTPError:
            print(f"Error: {r.text}")
            return False
        if not verbose:
            return True
        return r.json()

    def send_friend_request(self, user_id, verbose=False) -> bool | dict:
        """
        Sends a friend request to the specified user. Returns `True` if successful, `False` otherwise.

        If `verbose=True`, returns the full response from the server.
        """
        url = "https://us-central1-retro-media.cloudfunctions.net/requestFriend"
        headers = {"content-type": "application/json", "Authorization": f"Bearer {self.get_auth_token()}"}
        payload = {"data": {"uid": user_id}}
        r = requests.post(url, headers=headers, json=payload)
        try:
            r.raise_for_status()
        except requests.HTTPError:
            print(f"Error: {r.text}")
            return False
        if not verbose:
            return True
        return r.json()
    
    def cancel_friend_request(self, user_id, verbose=False) -> bool | dict:
        """
        Cancels a friend request to the specified user. Returns `True` if successful, `False` otherwise.

        If `verbose=True`, returns the full response from the server.
        """
        url = "https://us-central1-retro-media.cloudfunctions.net/cancelFriendRequest"
        headers = {"content-type": "application/json", "Authorization": f"Bearer {self.get_auth_token()}"}
        payload = {"data": {"uid": user_id}}
        r = requests.post(url, headers=headers, json=payload)
        try:
            r.raise_for_status()
        except requests.HTTPError:
            print(f"Error: {r.text}")
            return False
        if not verbose:
            return True
        return r.json()
    
    def unfriend(self, user_id, verbose=False) -> bool | dict:
        """
        Removes a user from the current user's friends list. Returns `True` if successful, `False` otherwise.

        If `verbose=True`, returns the full response from the server.
        """
        url = "https://us-central1-retro-media.cloudfunctions.net/unfriend"
        headers = {"content-type": "application/json", "Authorization": f"Bearer {self.get_auth_token()}"}
        payload = {"data": {"uid": user_id}}
        r = requests.post(url, headers=headers, json=payload)
        try:
            r.raise_for_status()
        except requests.HTTPError:
            print(f"Error: {r.text}")
            return False
        if not verbose:
            return True
        return r.json()
    
    def get_people_you_may_also_know(self, user_id, verbose=False) -> list | dict:
        """
        Gets a list of people Retro thinks the user may also know. Returns `True` if successful, `False` otherwise.

        If `verbose=True`, returns the full response from the server.
        """
        url = "https://us-central1-retro-media.cloudfunctions.net/getPeopleYouMayAlsoKnow"
        headers = {"content-type": "application/json", "Authorization": f"Bearer {self.get_auth_token()}"}
        payload = {"data": {"uid": user_id}}
        r = requests.post(url, headers=headers, json=payload)
        try:
            r.raise_for_status()
        except requests.HTTPError:
            print(f"Error: {r.text}")
            raise
        r_json = r.json()
        if not verbose:
            return r_json["result"]["peopleYouMayAlsoKnow"]
        return r_json

    def search_users(self, username, page=0) -> dict:
        """
        Searches for users by username using Algolia. Does not require authentication.

        Return format:
        ```
            {
                "hits": [
                    {
                        "objectID": str,           # user ID
                        "username": str,
                        "fullName": str,
                        "path": str,               # e.g. "users/{userId}"
                        "profilePhotoURL": str,    # Firebase Storage URL (may not exist)
                        "profileThumbHash": str,   # (may not exist)
                        "hasSavedAddress": bool,   # (may not exist)
                        "lastmodified": int,       # unix ms timestamp
                    },
                    ...
                ],
                "nbHits": int,
                "page": int,
                "nbPages": int,
                "hitsPerPage": int,
                "query": str,
            }
        ```
        """
        url = "https://39g8v6v6qe-dsn.algolia.net/1/indexes/users/query"
        headers = {"X-Algolia-API-Key": "574f0e95c4fbfe204867000799037e69", "X-Algolia-Application-Id": "39G8V6V6QE"}
        r = requests.post(url, headers=headers, json={"query": username, "page": page})
        try:
            r.raise_for_status()
        except requests.HTTPError:
            print(f"Error: {r.text}")
            raise
        return r.json()

    def get_user_id(self, username) -> str | None:
        """Get a user ID from a username. Returns `None` if no user is found."""
        results = self.search_users(username)
        hits = results.get("hits", [])
        if not hits or hits[0].get("username", "").lower() != username.lower():
            return None
        return hits[0].get("objectID")

    def create_journal(self, name, members=[], cover_font="roslindale", verbose=False) -> str | dict:
        """
        Creates a new journal with the specified name, members, and cover font. Returns the journal ID if successful, `None` otherwise.
        
        If `verbose=True`, returns the full response from the server.
        """

        url = "https://us-central1-retro-media.cloudfunctions.net/createJournal"
        headers = {"content-type": "application/json", "Authorization": f"Bearer {self.get_auth_token()}"}
        payload = {"data": {"name": name, "members": members, "coverFont": cover_font}}
        r = requests.post(url, headers=headers, json=payload)
        try:
            r.raise_for_status()
        except requests.HTTPError:
            print(f"Error: {r.text}")
            raise
        r_json = r.json()
        if not verbose:
            return r_json["result"]["journalId"]
        return r_json

    def get_current_user_id(self) -> str | None:
        """Returns the current authenticated user's UID decoded from the JWT."""
        token = self.get_auth_token()
        if not token:
            return None
        payload = token.split(".")[1]
        payload += "=" * (4 - len(payload) % 4)
        claims = json.loads(base64.b64decode(payload))
        return claims.get("user_id") or claims.get("sub")

    def get_user(self, user_id=None) -> dict | None:
        """
        Gets a user's profile data from Firestore. Returns `None` if the user does not exist.

        If `user_id` is not provided, gets the current authenticated user's profile data.

        Return format:
        ```
        {
            "id": str,
            "username": str,
            "fullName": str,
            "profilePhotoURL": str,
            "profileThumbHash": str,
            "hasSavedAddress": bool,
        }
        ```
        """
        if not user_id:
            user_id = self.get_current_user_id()

        db = self._get_firestore_client()
        doc = db.collection("users").document(user_id).get()
        if not doc.exists:
            return None
        return {"id": doc.id, **doc.to_dict()}

    def get_friend_statuses(self, filter=None) -> list[dict]:
        """
        Gets all friend statuses, optionally filtered by `filter` of type `FieldFilter`.

        Filter examples:
        - `FieldFilter("status", "==", "accepted")` -> filters to accepted friends
        - `FieldFilter("status", "==", "inboundRequestPending")` -> filters to incoming friend requests
        - `FieldFilter("hasGivenKey", "==", True)` -> filters to friends that the user has given a key to
        - `FieldFilter("hasReceivedKey", "==", True)` -> filters to friends that the user has received a key from

        Return format:
        ```
        [
            {
                "id": str,                       # user ID of the other user
                "status": str,                   # "accepted", "rejected", "inboundRequestPending", or "outboundRequestPending"
                "updatedAt": datetime,
                "requestHidden": bool,           # whether the request was hidden by current user
                "requestSeen": bool,             # whether the request was seen by current user
                "mutualFriendCount": int,        # exists on pending requests
                "mutualIds": list[str],          # exists on pending requests
                "inboundExpiresAt": float,       # optional, unix timestamp
                "coefficient": float,            # optional, exists on accepted friends
                "hasGivenKey": bool,             # optional
                "hasReceivedKey": bool,          # optional
            },
            ...
        ]
        ```
        """
        uid = self.get_current_user_id()
        db = self._get_firestore_client()
        results = []
        try:
            ref = db.collection("users").document(uid).collection("friends")
            if filter:
                ref = ref.where(filter=filter)

            for doc in ref.stream():
                results.append({"id": doc.id, **doc.to_dict()})
        except PermissionDenied:
            print("PermissionDenied: friends subcollection")
        return results

    def get_notifications(self, type=None) -> list[dict]:
        """
        Gets activity notifications for the current authenticated user.

        Optionally filter by `type`. Type options are `"comment"`, `"like"`, `"request"`, and `"tag"`.

        Return format:
        ```
        [
            {
                "id": str,
                "uid": str,                  # user ID of whoever triggered the notification
                "text": str,                 # human-readable description
                "createdAt": float,          # unix timestamp (seconds)
                "customRenderType": str,     # optional, e.g. "friendRequest", "systemMessage"
                "deeplink": str,             # optional, e.g. "media?uid=...&weekId=...&mediaId=..."
                "targetMediaURL": str,       # optional
                "targetMediaAuthorId": str,  # optional
                "targetMediaId": str,        # optional
                "targetMediaWeekId": str,    # optional, e.g. "2026_23"
                "targetCommentId": str,      # optional, present on "also commented" and "mentioned" notifications
            },
            ...
        ]
        ```
        """
        uid = self.get_current_user_id()
        db = self._get_firestore_client()
        results = []
        try:
            for doc in db.collection("users").document(uid).collection("activityItems").stream():
                results.append({"id": doc.id, **doc.to_dict()})
        except PermissionDenied:
            print("PermissionDenied: activityItems")
        if type is None:
            return results
        filters = {
            "like": lambda n: n.get("text", "").startswith("❤️"),
            "comment": lambda n: n.get("text", "").startswith("Also commented") or n.get("text", "").startswith("Mentioned you"),
            "request": lambda n: n.get("customRenderType") == "friendRequest",
            "tag": lambda n: "tagged you" in n.get("text", ""),
        }
        return [n for n in results if filters.get(type, lambda _: True)(n)]

    def accept_friend_request(self, user_id, verbose=False) -> bool | dict:
        """
        Accepts an incoming friend request from `user_id`. Returns `True` if successful and `False` otherwise.
        
        If `verbose=True`, returns the full response from the server.
        """
        url = "https://us-central1-retro-media.cloudfunctions.net/acceptFriend"
        headers = {"content-type": "application/json", "Authorization": f"Bearer {self.get_auth_token()}"}
        r = requests.post(url, headers=headers, json={"data": {"uid": user_id}})
        try:
            r.raise_for_status()
        except requests.HTTPError:
            print(f"Error: {r.text}")
            return False
        return r.json() if verbose else True

    def reject_friend_request(self, user_id, verbose=False) -> bool | dict:
        """
        Rejects an incoming friend request from `user_id`. Returns `True` if successful and `False` otherwise.
        
        If `verbose=True`, returns the full response from the server.
        """
        url = "https://us-central1-retro-media.cloudfunctions.net/rejectFriendRequest"
        headers = {"content-type": "application/json", "Authorization": f"Bearer {self.get_auth_token()}"}
        r = requests.post(url, headers=headers, json={"data": {"uid": user_id}})
        try:
            r.raise_for_status()
        except requests.HTTPError:
            print(f"Error: {r.text}")
            return False
        return r.json() if verbose else True

    def post_comment(self, owner_id, media_id, week_id, text) -> str:
        """Posts a comment on a media item. Returns the new comment ID."""
        media_id = media_id.rsplit(".", 1)[0] if "." in media_id else media_id
        uid = self.get_current_user_id()
        db = self._get_firestore_client()

        media_url = None
        media_created_at = None

        if week_id and not media_url:
            try:
                probe = db.collection("users").document(owner_id).collection("media").document(week_id).collection("items").document(media_id).get()
                if probe.exists:
                    d = probe.to_dict()
                    media_url = d.get("fullSizeURL")
                    media_created_at = d.get("createdAt")
                else:
                    print(f"Warning: media doc not found at users/{owner_id}/media/{week_id}/items/{media_id}")
            except Exception as e:
                print(f"Warning: media doc probe failed: {e}")

        if not week_id:
            print("Warning: could not determine week_id — comment will not appear in app")
        if not media_url:
            print("Warning: could not determine targetMediaURL — comment may not appear in app")

        comment_id = str(uuid.uuid4()).upper()
        doc = {
            "uid": uid,
            "text": text,
            "targetMediaId": media_id,
            "targetMediaCreatorId": owner_id,
            "createdAt": time.time(),
        }
        if week_id:
            doc["targetMediaWeekId"] = week_id
        if media_url:
            doc["targetMediaURL"] = media_url
        if media_created_at:
            doc["targetMediaCreatedAt"] = media_created_at
        db.collection("users").document(owner_id).collection("receivedComments").document(comment_id).set(doc)
        return comment_id

    def delete_media(self, week_id, media_id) -> None:
        """Deletes a media item from `users/{uid}/media/{week_id}/items/{media_id}`."""
        uid = self.get_current_user_id()
        db = self._get_firestore_client()
        db.collection("users").document(uid).collection("media").document(week_id).collection("items").document(media_id).delete()

    def give_key(self, user_id) -> None:
        """Gives a key to `user_id`."""
        uid = self.get_current_user_id()
        db = self._get_firestore_client()
        db.collection("users").document(uid).collection("friends").document(user_id).update({"hasGivenKey": True})

    def revoke_key(self, user_id) -> None:
        """Revokes a key from `user_id`."""
        uid = self.get_current_user_id()
        db = self._get_firestore_client()
        db.collection("users").document(uid).collection("friends").document(user_id).update({"hasGivenKey": False})

    def get_journal(self, journal_id) -> dict | None:
        """
        Gets journal metadata from Firestore. Returns `None` if the journal does not exist.

        Return format:
        ```
        {
            "id": str,
            "name": str,
            "creatorId": str,
            "createdAt": datetime,
            "updatedAt": datetime,
            "coverFont": str,                        # e.g. "roslindale"
            "mediaSortOrder": str,                   # e.g. "newest_first"
            "editPermission": str,                   # e.g. "creator_only", "all_members"
            "sharingPermission": str,                # e.g. "all_members"
            "manageMembershipPermission": str,       # e.g. "all_members"
            "canJoinFromPublicSlug": bool,
            "profilePhotoURL": str | None,
        }
        ```
        """
        db = self._get_firestore_client()
        doc = db.collection("journals").document(journal_id).get()
        if not doc.exists:
            return None
        return {"id": doc.id, **doc.to_dict()}

    def get_journal_media(self, journal_id) -> list[dict]:
        """
        Gets all media items from `journals/{journalId}/media` ordered by `createdAt`.

        Journal media is a flat collection with no week structure — week grouping is done client-side
        from the `createdAt` timestamp, unlike user media which is nested by weekId.

        Return format:
        ```
        [
            {
                "id": str,                           # UUID (matches Firebase Storage filename)
                "creatorId": str,
                "createdAt": float,                  # unix timestamp (seconds), when photo was taken
                "uploadedAt": float,                 # unix timestamp (seconds)
                "uploadedInCurrentWeek": bool,
                "fullSizeURL": str,                  # Firebase Storage download URL
                "thumbHash": str,                    # blurhash-style thumbnail
                "imageWidth": float,
                "imageHeight": float,
                "isKeyholdersOnly": bool,
                "timeZoneOffset": float,             # optional, UTC offset in seconds (e.g. -14400 = EDT)
                "localAssetIdentifier": str,         # optional, iOS PHAsset identifier
            },
            ...
        ]
        ```
        """
        db = self._get_firestore_client()
        ref = db.collection("journals").document(journal_id).collection("media").order_by("createdAt")
        results = []
        try:
            for doc in ref.stream():
                results.append({"id": doc.id, **doc.to_dict()})
        except PermissionDenied:
            print("PermissionDenied: journals media subcollection")
        return results

    def add_journal_member(self, journal_id, user_ids) -> bool | dict:
        """Adds a member to a journal. Returns `True` if successful and `False` otherwise."""
        url = "https://us-central1-retro-media.cloudfunctions.net/addJournalMembers"
        headers = {"content-type": "application/json", "Authorization": f"Bearer {self.get_auth_token()}"}
        r = requests.post(url, headers=headers, json={"data": {"uids": user_ids, "journalId": journal_id}})
        try:
            r.raise_for_status()
        except requests.HTTPError:
            print(f"Error: {r.text}")
            return False
        return True
    
    def remove_journal_member(self, journal_id, user_id) -> bool | dict:
        """Removes a member from a journal. Returns `True` if successful and `False` otherwise."""
        url = "https://us-central1-retro-media.cloudfunctions.net/removeFromJournal"
        headers = {"content-type": "application/json", "Authorization": f"Bearer {self.get_auth_token()}"}
        r = requests.post(url, headers=headers, json={"data": {"uid": user_id, "journalId": journal_id}})
        try:
            r.raise_for_status()
        except requests.HTTPError:
            print(f"Error: {r.text}")
            return False
        return True
    
    def make_journal_admin(self, journal_id, user_id) -> bool | dict:
        """Promotes a member to admin in a journal. Returns `True` if successful and `False` otherwise."""
        url = "https://us-central1-retro-media.cloudfunctions.net/makeJournalAdmin"
        headers = {"content-type": "application/json", "Authorization": f"Bearer {self.get_auth_token()}"}
        r = requests.post(url, headers=headers, json={"data": {"uid": user_id, "journalId": journal_id}})
        try:
            r.raise_for_status()
        except requests.HTTPError:
            print(f"Error: {r.text}")
            return False
        return True

    def get_user_profile_picture(self, user_id) -> Image.Image | None:
        """Gets a user's profile picture as a PIL Image. Returns `None` if the user has no profile picture."""
        db = self._get_firestore_client()
        doc = db.collection("users").document(user_id).get()
        if not doc.exists:
            return None
        url = doc.to_dict().get("profilePhotoURL")
        if not url:
            return None
        r = requests.get(url, headers=self.get_auth_header())
        r.raise_for_status()
        return Image.open(io.BytesIO(r.content))

    def get_media_comments(self, owner_id, media_id) -> list[dict]:
        """
        Gets comments for a media item. Returns a list of comments, where each comment is a dict with the following keys:
        ```
        [
            {
                "id": str,                       # comment ID
                "uid": str,                      # user ID of the commenter
                "text": str,                     # comment text
                "createdAt": int,                # unix ms timestamp
                "targetMediaId": str,
                "targetMediaURL": str,           # Firebase Storage URL
                "targetMediaCreatorId": str,
                "targetMediaCreatedAt": float,
                "targetMediaWeekId": str,        # e.g. "2026_23"
            },
            ...
        ]
        ```
        """
        db = self._get_firestore_client()
        comments_ref = db.collection("users").document(owner_id).collection("receivedComments")
        docs = comments_ref.where(filter=FieldFilter("targetMediaId", "==", media_id)).stream()
        results = []
        for doc in docs:
            data = doc.to_dict()
            results.append({"id": doc.id, **data})
        return results

    def _get_firestore_client(self) -> firestore.Client:
        """Returns a Firestore client authenticated with the current auth token."""
        creds = Credentials(token=self.get_auth_token())
        return firestore.Client(project="retro-media", credentials=creds)

    def get_week_media(self, user_id, week_id) -> list[dict]:
        """Gets media items for a given user and week. Returns a list of media items, where each item is a dict with the following keys:
        ```
        [
            {
                "id": str,                                 # Firestore document ID (same as cloudId)
                "cloudId": str,                            # Firebase Storage filename; not on memory posts
                "fullSizeURL": str,                        # Firebase Storage download URL
                "creatorId": str,                          # user ID of the uploader
                "imageHeight": float,                      # not on memory posts
                "imageWidth": float,                       # not on memory posts
                "thumbHash": str,                          # blurhash-style thumbnail
                "uploadedAt": float,                       # unix timestamp (seconds)
                "createdAt": float,                        # unix timestamp (seconds), when taken
                "isKeyholdersOnly": bool,
                "uploadedInCurrentWeek": bool,
                "localAssetIdentifier": str,               # iOS PHAsset identifier
                "videoDurationSeconds": float,             # 0.0 for photos
                "timeZoneOffset": float,                   # optional, UTC offset in seconds (e.g. -14400 = EDT)
                "locationName": str,                       # optional
                "captionCommentId": str,                   # optional
                "taggedUsers": list[str],                  # optional, list of tagged user IDs
                "deepDeletionEdges": list[str],            # optional, Firestore paths to clean up on delete
                "repostedMediaOriginalPath": str,          # optional, exists on reposts
                "repostedMediaOriginalOwner": str,         # optional, exists on reposts
                "memoryType": str,                         # optional, exists on memory posts (e.g. "onThisWeek")
                "memoryCreatedAt": float,                  # optional, exists on memory posts
            },
            ...
        ]
        ```
        """
        db = self._get_firestore_client()
        items_ref = db.collection("users").document(user_id).collection("media").document(week_id).collection("items")
        results = []
        for doc in items_ref.stream():
            data = doc.to_dict()
            results.append({"id": doc.id, **data})
            
        return results
