import sys

from httpx import AsyncClient
from secrets import choice
from .constants import YELLOW, RED, BOLD, RESET, USER_AGENTS
from .util import find_key


async def asyncUpdateToken(
    client: AsyncClient, key: str, url: str, **kwargs
) -> AsyncClient:
    caller_name = sys._getframe(1).f_code.co_name
    try:
        headers = {
            "x-guest-token": client.cookies.get("guest_token", ""),
            "x-csrf-token": client.cookies.get("ct0", ""),
            "x-twitter-auth-type": "OAuth2Client"
            if client.cookies.get("auth_token")
            else "",
        }
        client.headers.update(headers)
        updateTokenResponse = await client.post(url, **kwargs)
        info = updateTokenResponse.json()

        for task in info.get("subtasks", []):
            if task.get("enter_text", {}).get("keyboard_type") == "email":
                print(f"[{YELLOW}warning{RESET}] {' '.join(find_key(task, 'text'))}")
                client.cookies.set(
                    "confirm_email", "true"
                )  # signal that email challenge must be solved

            if task.get("subtask_id") == "LoginAcid":
                if task["enter_text"]["hint_text"].casefold() == "confirmation code":
                    print(
                        f"[{YELLOW}warning{RESET}] email confirmation code challenge."
                    )
                    client.cookies.set("confirmation_code", "true")

        client.cookies.set(key, info[key])

    except KeyError as e:
        client.cookies.set(
            "flow_errors", "true"
        )  # signal that an error occurred somewhere in the flow
        print(
            f"[{RED}error{RESET}] failed to update token at {BOLD}{caller_name}{RESET}\n{e}"
        )
    return client


async def asyncInitGuestToken(client: AsyncClient) -> AsyncClient:
    return await asyncUpdateToken(
        client, "guest_token", "https://api.twitter.com/1.1/guest/activate.json"
    )


async def asyncFlowStart(client: AsyncClient) -> AsyncClient:
    return await asyncUpdateToken(
        client,
        "flow_token",
        "https://api.twitter.com/1.1/onboarding/task.json",
        params={"flow_name": "login"},
        json={
            "input_flow_data": {
                "flow_context": {
                    "debug_overrides": {},
                    "start_location": {"location": "splash_screen"},
                }
            },
            "subtask_versions": {},
        },
    )


async def asyncFlowInstrumentation(client: AsyncClient) -> AsyncClient:
    return await asyncUpdateToken(
        client,
        "flow_token",
        "https://api.twitter.com/1.1/onboarding/task.json",
        json={
            "flow_token": client.cookies.get("flow_token"),
            "subtask_inputs": [
                {
                    "subtask_id": "LoginJsInstrumentationSubtask",
                    "js_instrumentation": {"response": "{}", "link": "next_link"},
                }
            ],
        },
    )


async def asyncFlowUsername(client: AsyncClient) -> AsyncClient:
    return await asyncUpdateToken(
        client,
        "flow_token",
        "https://api.twitter.com/1.1/onboarding/task.json",
        json={
            "flow_token": client.cookies.get("flow_token"),
            "subtask_inputs": [
                {
                    "subtask_id": "LoginEnterUserIdentifierSSO",
                    "settings_list": {
                        "setting_responses": [
                            {
                                "key": "user_identifier",
                                "response_data": {
                                    "text_data": {
                                        "result": client.cookies.get("username")
                                    }
                                },
                            }
                        ],
                        "link": "next_link",
                    },
                }
            ],
        },
    )


async def asyncFlowPassword(client: AsyncClient) -> AsyncClient:
    return await asyncUpdateToken(
        client,
        "flow_token",
        "https://api.twitter.com/1.1/onboarding/task.json",
        json={
            "flow_token": client.cookies.get("flow_token"),
            "subtask_inputs": [
                {
                    "subtask_id": "LoginEnterPassword",
                    "enter_password": {
                        "password": client.cookies.get("password"),
                        "link": "next_link",
                    },
                }
            ],
        },
    )


async def asyncFlowDuplicationCheck(client: AsyncClient) -> AsyncClient:
    return await asyncUpdateToken(
        client,
        "flow_token",
        "https://api.twitter.com/1.1/onboarding/task.json",
        json={
            "flow_token": client.cookies.get("flow_token"),
            "subtask_inputs": [
                {
                    "subtask_id": "AccountDuplicationCheck",
                    "check_logged_in_account": {
                        "link": "AccountDuplicationCheck_false"
                    },
                }
            ],
        },
    )


async def asyncConfirmEmail(client: AsyncClient) -> AsyncClient:
    return await asyncUpdateToken(
        client,
        "flow_token",
        "https://api.twitter.com/1.1/onboarding/task.json",
        json={
            "flow_token": client.cookies.get("flow_token"),
            "subtask_inputs": [
                {
                    "subtask_id": "LoginAcid",
                    "enter_text": {
                        "text": client.cookies.get("email"),
                        "link": "next_link",
                    },
                }
            ],
        },
    )


async def asyncSolveConfirmationChallenge(client: AsyncClient, **kwargs) -> AsyncClient:
    if fn := kwargs.get("proton"):
        confirmation_code = fn()
        return await asyncUpdateToken(
            client,
            "flow_token",
            "https://api.twitter.com/1.1/onboarding/task.json",
            json={
                "flow_token": client.cookies.get("flow_token"),
                "subtask_inputs": [
                    {
                        "subtask_id": "LoginAcid",
                        "enter_text": {
                            "text": confirmation_code,
                            "link": "next_link",
                        },
                    },
                ],
            },
        )


async def asyncExecuteLoginFlow(client: AsyncClient, **kwargs) -> AsyncClient | None:
    client = await asyncInitGuestToken(client)
    for fn in [
        asyncFlowStart,
        asyncFlowInstrumentation,
        asyncFlowUsername,
        asyncFlowPassword,
        asyncFlowDuplicationCheck,
    ]:
        client = await fn(client)

    # solve email challenge
    if client.cookies.get("confirm_email") == "true":
        client = await asyncConfirmEmail(client)

    # solve confirmation challenge (Proton Mail only)
    if client.cookies.get("confirmation_code") == "true":
        if not kwargs.get("proton"):
            print(
                f"[{RED}warning{RESET}] Please check your email for a confirmation code"
                f" and log in again using the web app. If you wish to automatically solve"
                f" email confirmation challenges, add a Proton Mail account in your account settings"
            )
            return
        client = await asyncSolveConfirmationChallenge(client, **kwargs)
    return client


async def asyncLogin(email: str, username: str, password: str, **kwargs) -> AsyncClient:
    proxies = kwargs.pop("proxies", None)

    client = AsyncClient(
        cookies={
            "email": email,
            "username": username,
            "password": password,
            "guest_token": None,
            "flow_token": None,
        },
        headers={
            "authorization": "Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA",
            "content-type": "application/json",
            "user-agent": choice(USER_AGENTS),
            "x-twitter-active-user": "yes",
            "x-twitter-client-language": "en",
        },
        follow_redirects=True,
        proxies=proxies,
        http2=True,
        timeout=30,
        verify=False
    )

    client = await asyncExecuteLoginFlow(client, **kwargs)
    if not client or client.cookies.get("flow_errors") == "true":
        raise Exception(f"[error] {username} login failed")
    return client
