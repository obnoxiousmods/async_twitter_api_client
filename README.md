# async-twitter-api-client
Async port of twitter-api-client

~ of 2024-04-24 this is being maintained as its being used in a project im being paid to maintain ~

MASSIVE Thank you to Trevor Hobenshield @trevorhobenshield for making this!
All I have done is changed the client to asyncClient 

Key Differences:

linted by ruff
renames tweet and other functions to asyncTweet asyncReply etc
all functions must be awaited
uses httpx asyncclient instead of Client so it supports anyio, trio, curio, asyncio
natively supports proxies, http(s)+socks5
reply & quote support uploading images

Todo: Solve & Submit captcha to unlock account using various captcha solving providers
Maybe fix searching somehwat?
Add signup

Original search.py uses asyncio.gather(), i switched to use anyio.create_task_group() with a results list that the tasks append to, might not be a 1:1 behaviour

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