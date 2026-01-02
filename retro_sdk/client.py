import requests

class Retro:
    def __init__(self, refresh_token=None):
        self.refresh_token = refresh_token
        self.access_token = None
        self.last_checked_time = None
        self.web_api_key = "AIzaSyDVXcY0s4ZeREh43EYzsHqbEWcCJ6Ism5w"
        if refresh_token:
            self._refresh_auth_token()

    def _refresh_auth_token(self):
        url = f"https://securetoken.googleapis.com/v1/token?key={self.web_api_key}"
        payload = {"grantType": "refresh_token", "refreshToken": self.refresh_token}
        r = requests.post(url, json=payload)
        try:
            r.raise_for_status()
        except requests.HTTPError as e:
            print(f"Error: {r.text}")
            raise
        self.access_token = r.json().get("access_token")

    def set_last_checked_time(self, time):
        self.last_checked_time = time

    def get_last_checked_time(self):
        return self.last_checked_time

    def get_auth_header(self):
        return {"Authorization": f"Firebase {self.access_token}"}

    def get_refresh_token(self, token, verbose=False):
        url = f"https://www.googleapis.com/identitytoolkit/v3/relyingparty/verifyCustomToken?key={self.web_api_key}"
        headers = {"content-type": "application/json"}
        payload = {"token": token, "returnSecureToken": True}
        r = requests.post(url, headers=headers, json=payload)
        try:
            r.raise_for_status()
        except requests.HTTPError as e:
            print(f"Error: {r.text}")
            raise
        r_json = r.json()
        self.refresh_token = r_json["refreshToken"]
        print(r_json)
        if not verbose:
            return
        return r_json
    
    def send_code(self, phone_number, custom_data=None, verbose=False):
        # phone number must be in international format
        # custom payload format
        # {
        #     "data": {
        #         "deviceId": device_id,            
        #         "appVersion": app_version,
        #         "phoneNumber": phone_number,
        #         "platform": platform,
        #         "osVersion": os_version,
        #         "dispatchId": dispatch_id,
        #         "deviceModel": device_model
        #     }
        # }
        url = "https://us-central1-retro-media.cloudfunctions.net/sendCode"
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
        except requests.HTTPError as e:
            print(f"Error: {r.text}")
            raise
        r_json = r.json()
        self.prev_authenticationUuid = r_json["result"]["authenticationUuid"]
        self.phone_number = phone_number
        if not verbose:
            return r_json["result"]["authenticationUuid"]
        return r_json
    
    def verify_code(self, code, authenticationUuid=None, verbose=False):
        url = "https://us-central1-retro-media.cloudfunctions.net/verifyCode"
        headers = {"content-type": "application/json"}
        payload = {"data": {"authenticationUuid": authenticationUuid if authenticationUuid else self.prev_authenticationUuid, "code": code}}
        r = requests.post(url, headers=headers, json=payload)
        try:
            r.raise_for_status()
        except requests.HTTPError as e:
            print(f"Error: {r.text}")
            raise
        r_json = r.json()
        self.access_token = r_json["result"]["token"]
        self.get_refresh_token(self.access_token)
        if not verbose:
            return
        return r_json

    def download_profile_photo(self, user_id, filename, output_path): # make it return the image in some reasonable format
        url = f"https://firebasestorage.googleapis.com/v0/b/retro-media-multi/o/profilePhotos%2F{user_id}%2F{filename}?alt=media"
        r = requests.get(url, headers=self.get_auth_header())
        try:
            r.raise_for_status()
        except requests.HTTPError as e:
            print(f"Error: {r.text}")
            raise
        with open(output_path, "wb") as f:
            f.write(r.content)
        return True

    def get_media_metadata(self, user_id, week, filename):
        url = f"https://firebasestorage.googleapis.com/v0/b/retro-media-multi/o/media%2F{user_id}%2F{week}%2F{filename}"
        r = requests.get(url, headers=self.get_auth_header())
        try:
            r.raise_for_status()
        except requests.HTTPError as e:
            print(f"Error: {r.text}")
            raise
        return r.json()

    def list_files_in_folder(self, user_id, week):
        url = "https://firebasestorage.googleapis.com/v0/b/retro-media-multi/o"
        r = requests.get(url, headers=self.get_auth_header(), params={"prefix": f"media/{user_id}/{week}/", "delimiter": "/"})
        try:
            r.raise_for_status()
        except requests.HTTPError as e:
            print(f"Error: {r.text}")
            raise
        return r.json()

    def get_filenames_in_folder(self, user_id, week):
        data = self.list_files_in_folder(user_id, week)
        items = data.get("items", [])
        return [item["name"] for item in items] if items else []

    def download_media_file(self, user_id, week, filename, output_path):
        url = f"https://firebasestorage.googleapis.com/v0/b/retro-media-multi/o/media%2F{user_id}%2F{week}%2F{filename}?alt=media"
        r = requests.get(url, headers=self.get_auth_header(), allow_redirects=True)
        try:
            r.raise_for_status()
        except requests.HTTPError as e:
            print(f"Error: {r.text}")
            raise
        with open(output_path, "wb") as f:
            f.write(r.content)
        return True
    
    def profile_weeks(self, user_id, verbose=False):
        url = "https://us-central1-retro-media.cloudfunctions.net/profileWeeks"
        headers = {"content-type": "application/json", "Authorization": f"Bearer {self.access_token}"}
        payload = {"data": {"uid": user_id}}
        r = requests.post(url, headers=headers, json=payload)
        try:
            r.raise_for_status()
        except requests.HTTPError as e:
            print(f"Error: {r.text}")
            raise
        r_json = r.json()
        if verbose:
            return r_json
        return r_json["result"]
    
    def set_username(self, username, verbose=False):
        url = "https://us-central1-retro-media.cloudfunctions.net/setUsername"
        headers = {"content-type": "application/json", "Authorization": f"Bearer {self.access_token}"}
        payload = {"data": {"username": username}}
        r = requests.post(url, headers=headers, json=payload)
        try:
            r.raise_for_status()
        except requests.HTTPError as e:
            print(f"Error: {r.text}")
            raise
        if not verbose:
            return
        return r.json()

    def send_friend_request(self, user_id, verbose=False):
        url = "https://us-central1-retro-media.cloudfunctions.net/requestFriend"
        headers = {"content-type": "application/json", "Authorization": f"Bearer {self.access_token}"}
        payload = {"data": {"uid": user_id}}
        r = requests.post(url, headers=headers, json=payload)
        try:
            r.raise_for_status()
        except requests.HTTPError as e:
            print(f"Error: {r.text}")
            raise
        if not verbose:
            return
        return r.json()
    
    def cancel_friend_request(self, user_id, verbose=False):
        url = "https://us-central1-retro-media.cloudfunctions.net/cancelFriendRequest"
        headers = {"content-type": "application/json", "Authorization": f"Bearer {self.access_token}"}
        payload = {"data": {"uid": user_id}}
        r = requests.post(url, headers=headers, json=payload)
        try:
            r.raise_for_status()
        except requests.HTTPError as e:
            print(f"Error: {r.text}")
            raise
        if not verbose:
            return
        return r.json()
    
    def unfriend(self, user_id, verbose=False):
        url = "https://us-central1-retro-media.cloudfunctions.net/unfriend"
        headers = {"content-type": "application/json", "Authorization": f"Bearer {self.access_token}"}
        payload = {"data": {"uid": user_id}}
        r = requests.post(url, headers=headers, json=payload)
        try:
            r.raise_for_status()
        except requests.HTTPError as e:
            print(f"Error: {r.text}")
            raise
        if not verbose:
            return
        return r.json()
    
    def get_people_you_may_also_know(self, user_id, verbose=False):
        url = "https://us-central1-retro-media.cloudfunctions.net/getPeopleYouMayAlsoKnow"
        headers = {"content-type": "application/json", "Authorization": f"Bearer {self.access_token}"}
        payload = {"data": {"uid": user_id}}
        r = requests.post(url, headers=headers, json=payload)
        try:
            r.raise_for_status()
        except requests.HTTPError as e:
            print(f"Error: {r.text}")
            raise
        r_json = r.json()
        if not verbose:
            return r_json["result"]["peopleYouMayAlsoKnow"]
        return r_json

    def send_code_v2(self, phone_number, verbose=False):
        url = "https://us-central1-retro-media.cloudfunctions.net/sendCodeV2"
        headers = {"content-type": "application/json"}

    def search_users(self, username, page=0): # figure out how paginating works/how to request a later page. get all pages if num > 0 (?)
        url = "https://39g8v6v6qe-dsn.algolia.net/1/indexes/users/query"
        headers = {"X-Algolia-API-Key": "574f0e95c4fbfe204867000799037e69", "X-Algolia-Application-Id": "39G8V6V6QE"}
        r = requests.post(url, headers=headers, json={"query": username})
        try:
            r.raise_for_status()
        except requests.HTTPError as e:
            print(f"Error: {r.text}")
            raise
        return r.json()

    def get_user_id_from_username(self, username):
        results = self.search_users(username)
        hits = results.get("hits", [])
        return results[0].get("objectID") if hits else None
