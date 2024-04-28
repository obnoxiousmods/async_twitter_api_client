# asyncTwitterClient

Async port of twitter-api-client

~ of 2024-04-24 this is being maintained as its being used in a project im being paid to maintain ~

MASSIVE Thank you to Trevor Hobenshield @trevorhobenshield for making this!
All I have done is changed the client to asyncClient 

# Key Differences

```
supports unlocking account via account.unlockViaArkoseCaptcha()
linted by ruff
renames tweet and other functions to asyncTweet asyncReply etc
all functions must be awaited
uses httpx asyncclient instead of Client so it supports anyio, trio, curio, asyncio
natively supports proxies, http(s)+socks5
reply & quote support uploading images
save_cookies takes toFile arg instead of always making a file and rets a dict

Original search.py uses asyncio.gather(), i switched to use anyio.create_task_group() with a results list that the tasks append to, might not be a 1:1 behaviour
```

# Todo
```
Add more captchas providers to solve arkose challenge
Find a way to provide real ui_metrics for unlocker
Find a way to use original AsyncClient for unlocker
Maybe fix searching somehwat?
Add signup
```




```pip install asyncTwitterClient```

```
import anyio

from asyncTwitter.asyncAccount import AsyncAccount


async def main():
    twitter = AsyncAccount()
    await twitter.asyncAuthenticate(
        cookies={"ct0": "fuefjwegf89ewg9uiwg9", "auth_token": "je09giewg9iwg9j"}
    )

if __name__ == "__main__":
    anyio.run(main)
```