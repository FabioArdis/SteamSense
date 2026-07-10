import requests

from src.collector.exceptions import SteamAPIError, StoreGameNotFound, AchievementsNotFound, ReviewsNotFound


class SteamClient:
    BASE_URL = "https://api.steampowered.com"
    STORE_URL = "https://store.steampowered.com"

    def __init__(self, api_key: str):
        self.api_key = api_key

    def get_owned_games(self, steam_id: str) -> list[dict]:
        endpoint = f"{self.BASE_URL}/IPlayerService/GetOwnedGames/v1/"
        params = {
            "key": self.api_key,
            "steamid": steam_id,
            "include_appinfo": True,
            "format": "json"
        }

        response = requests.get(endpoint, params)

        if response.status_code != 200:
            raise SteamAPIError(f"SteamAPI returned {response.status_code}")

        return response.json()["response"]["games"]

    def get_app_details(self, appid) -> dict:
        response = requests.get(
            f"{self.STORE_URL}/api/appdetails",
            params={
                "appids": appid,
                "l": "english"
            }
        )

        if response.status_code != 200:
            raise SteamAPIError(f"Steam Store API returned {response.status_code}")

        data = response.json()
        if data[str(appid)]["success"] is not True:
            raise StoreGameNotFound(f"Game not found for appid: {appid}")

        return data

    def get_app_reviews(self, appid) -> dict:
        response = requests.get(f"{self.STORE_URL}/appreviews/{appid}?json=1&num_per_page=0")

        if response.status_code != 200:
            raise SteamAPIError(f"Steam Store API returned {response.status_code}")

        data = response.json()
        if data["success"] != 1:
            raise ReviewsNotFound(f"Reviews not found for appid: {appid}")

        return {
            "total_positive": data["query_summary"]["total_positive"],
            "total_negative": data["query_summary"]["total_negative"],
        }


    def get_player_achievements(self, steam_id: str, appid) -> list[dict]:
        endpoint = f"{self.BASE_URL}/ISteamUserStats/GetPlayerAchievements/v1/"
        params = {
            "key": self.api_key,
            "steamid": steam_id,
            "appid": appid
        }

        response = requests.get(endpoint, params)

        if response.status_code != 200:
            raise SteamAPIError(f"SteamAPI returned {response.status_code}")

        if not response.json()["playerstats"]["success"]:
            raise AchievementsNotFound(f"SteamAPI returned no achievements for {appid}")

        return response.json()["playerstats"].get("achievements", [])
