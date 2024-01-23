# async-twitter-api-client
Async port of twitter-api-client

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