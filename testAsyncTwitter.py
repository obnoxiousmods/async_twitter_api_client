from asyncTwitter.asyncAccount import AsyncAccount
from trio import run


async def mainFunc():
    twitter = AsyncAccount()

    await twitter.__ainit__(
        cookies="C:/Users/a/Documents/Git/infiniteMoneyTwitterBot/cookies/obJellyfin.cookies"
    )

    # results = await twitter.asyncTweet(text="A test tweet from the asyncTwitter module!")
    scheduleTweetResults = await twitter.asyncScheduleTweet(
        text="A test tweet from the asyncTwitter module!",
        date="2021-08-01 08:21",
    )

    print(scheduleTweetResults)


run(mainFunc)
