import anyio
import json
import os
import pymongo
import json5

from colorama import Fore
from asyncTwitter.asyncAccount import AsyncAccount
from asyncTwitter.asyncScraper import AsyncScraper
from asyncTwitter.asyncSearch import AsyncSearch
from asyncTwitter.asyncUtil import find_key


async def logAllNewFollowers():
    config = json5.load(open("config.json5"))

    mongoClient = pymongo.MongoClient("mongodb://localhost:27017/")
    twitterFollowers = mongoClient["twitterFollowers"]
    followers = twitterFollowers["followers"]

    scraper = AsyncScraper(debug=True)
    account = AsyncAccount(debug=True)


    await scraper.asyncAuthenticate(
        cookies="cookies/testing.cookies.cookies", httpxSocks=False
    )
    await account.asyncAuthenticate(
        cookies="cookies/testing.cookies.cookies", httpxSocks=False
    )

    while True:
        screenNameToJSON = await scraper.asyncUsers(
            screen_names=[config.get("usernameToWatch", "obJellyfin")]
        )

        restId = (
            screenNameToJSON[0]
            .get("data", {})
            .get("user", {})
            .get("result", {})
            .get("rest_id")
        )

        if not restId:
            print("Failed to get restId.")
            exit()

        results = await scraper.asyncFollowers(user_ids=[restId], limit=50)

        print(json.dumps(results, indent=4), file=open("followers.json", "w"))

        followerRestIds = find_key(results, "rest_id")

        for followerRestId in followerRestIds:
            if not followers.count_documents({"rest_id": followerRestId}):
                print(
                    f"{Fore.CYAN}Found new follower: {followerRestId} | Adding {followerRestId} to the database.{Fore.RESET}"
                )

                followers.update_one(
                    {"rest_id": followerRestId},
                    {"$set": {"rest_id": followerRestId}},
                    upsert=True,
                )
                
                dmResults = await account.asyncDM(
                    receivers=[followerRestId],
                    text=config.get("welcomeMessage", "Welcome to the club!"),
                )
                await anyio.sleep(10)
                
                dm_id = find_key(dmResults, "dm_id")
                
                
                if dm_id:
                    dm_id = dm_id[0]
                    print(f"{Fore.GREEN}Sent DM to {followerRestId} with DM id {dm_id}.{Fore.RESET}")
                    followers.update_one(
                        {"rest_id": followerRestId},
                        {"$set": {"dm_id": dm_id}},
                        upsert=True,
                    )
                else:
                    print(f"{Fore.RED}Failed to send DM to {followerRestId}.{Fore.RESET}")
                
            else:
                print(f"{Fore.YELLOW}Found existing follower: {followerRestId}{Fore.RESET}")
                
        await anyio.sleep(config.get("interval", 180))


if __name__ == "__main__":
    init = anyio.run(logAllNewFollowers)
