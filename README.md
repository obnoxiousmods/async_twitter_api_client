# async-twitter-api-client
Async port of twitter-api-client

MASSIVE Thank you to Trevor Hobenshield @trevorhobenshield for making this!
All I have done is changed the client to asyncClient 

Key Differences:

linted by ruff
renames tweet and other functions to asyncTweet asyncReply etc
all functions must be awaited
uses httpx asyncclient instead of Client so it supports anyio, trio, curio, asyncio
natively supports proxies:

Todo: Port search.py (add awaits + async def + rename functions)

```
from asyncTwitter.asyncAccount import asyncAccount
from trio import run


async def mainFunc():
    twitter = asyncAccount()

    initResults = await twitter.asyncAuthenticate(
        cookies="cookies/obJellyfin.cookies",
        #email="lol@gmail.com"
        #password="eweigjwhj32!"
        #proxies="socks5://127.0.0.1:9150"
    )
    print(initResults)

    await twitter.asyncTweet(text="Async tweet testing 123")


run(mainFunc)
```