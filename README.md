# async-twitter-api-client
Async port of twitter-api-client

```
from asyncTwitter.asyncAccount import asyncAccount
from trio import run


async def mainFunc():
    twitter = asyncAccount()

    initResults = await twitter.asyncAuthenticate(cookies="cookies/obJellyfin.cookies")
    print(initResults)

    await twitter.asyncTweet(text="Async tweet testing 123")


run(mainFunc)
```