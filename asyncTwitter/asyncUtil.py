import random
import re
import time
import string

from logging import Logger
from pathlib import Path
from urllib.parse import urlsplit, urlencode, urlunsplit, parse_qs, quote

import orjson
from httpx import Response, AsyncClient

from .constants import GREEN, MAGENTA, RED, RESET, ID_MAP, USER_AGENTS


def generate_random_string(length):
    characters = string.ascii_letters + string.digits
    return "".join(random.choice(characters) for i in range(length))


def randomLivePipelineSession():
    # 'LivePipeline-Session': '4cc59a77-31a2-4ed0-8246-ada14c86d528',

    return f"{generate_random_string(8)}-{generate_random_string(4)}-{generate_random_string(4)}-{generate_random_string(4)}-{generate_random_string(12)}"


def randomTransactionId():
    x_client_transaction_id = f"{generate_random_string(19)}/{generate_random_string(3)}/{generate_random_string(18)}+{generate_random_string(51)}"
    return x_client_transaction_id



async def async_init_session(proxies=None):
    client = AsyncClient(
        headers={
            "authorization": "Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs=1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA",
            "user-agent": random.choice(USER_AGENTS),
        },
        follow_redirects=True,
        proxies=proxies,
        verify=False,
    )
    r = await client.post("https://api.twitter.com/1.1/guest/activate.json")
    r = r.json()
    client.headers.update(
        {
            "content-type": "application/json",
            "x-guest-token": r["guest_token"],
            "x-twitter-active-user": "yes",
        }
    )
    return client


def batch_ids(ids: list[int], char_limit: int = 4_500) -> list[dict]:
    """To avoid 431 errors"""
    length = 0
    res, batch = [], []
    for x in map(str, ids):
        curr_length = len(x)
        if length + curr_length > char_limit:
            res.append(batch)
            batch = []
            length = 0
        batch.append(x)
        length += curr_length
    if batch:
        res.append(batch)
    return res


def build_params(params: dict) -> dict:
    return {k: orjson.dumps(v).decode() for k, v in params.items()}


def save_json(r: Response, path: Path, name: str, **kwargs):
    try:
        data = r.json()
        kwargs.pop("cursor", None)
        out = path / "_".join(map(str, kwargs.values()))
        out.mkdir(parents=True, exist_ok=True)
        (out / f"{time.time_ns()}_{name}.json").write_bytes(orjson.dumps(data))
    except Exception as e:
        print(f"Failed to save data: {e}")


def flatten(seq: list | tuple) -> list:
    flat = []
    for e in seq:
        if isinstance(e, list | tuple):
            flat.extend(flatten(e))
        else:
            flat.append(e)
    return flat


def get_json(res: list[Response], **kwargs) -> list:
    cursor = kwargs.get("cursor")
    temp = res
    if any(isinstance(r, (list, tuple)) for r in res):
        temp = flatten(res)
    results = []
    for r in temp:
        try:
            data = r.json()
            if cursor:
                results.append([data, cursor])
            else:
                results.append(data)
        except Exception as e:
            print("Cannot parse JSON response", e)
    return results


def set_qs(url: str, qs: dict, update=False, **kwargs) -> str:
    *_, q, f = urlsplit(url)
    return urlunsplit(
        (
            *_,
            urlencode(
                qs | parse_qs(q) if update else qs,
                doseq=True,
                quote_via=quote,
                safe=kwargs.get("safe", ""),
            ),
            f,
        )
    )


def get_cursor(data: list | dict) -> str:
    # inefficient, but need to deal with arbitrary schema
    entries = find_key(data, "entries")
    if entries:
        for entry in entries.pop():
            entry_id = entry.get("entryId", "")
            if ("cursor-bottom" in entry_id) or ("cursor-showmorethreads" in entry_id):
                content = entry["content"]
                if itemContent := content.get("itemContent"):
                    return itemContent["value"]  # v2 cursor
                return content["value"]  # v1 cursor


def get_headers(session, **kwargs) -> dict:
    """
    Get the headers required for authenticated requests
    """
    cookies = session.cookies
    # todo httpx cookie issues
    try:
        if session._init_with_cookies:
            cookies.delete("ct0", domain=".twitter.com")
    except Exception:
        ...
    headers = (
        kwargs
        | {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "*/*",
            "Accept-Language": "en-CA,en-US;q=0.7,en;q=0.3",
            "authorization": "Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs=1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA",
            "LivePipeline-Session": randomLivePipelineSession(),  #'4cc59a77-31a2-4ed0-8246-ada14c86d528',
            # "cookie": "; ".join(f"{k}={v}" for k, v in cookies.items()),
            "Referer": "https://twitter.com/",
            "x-csrf-token": cookies.get("ct0", ""),
            "x-guest-token": cookies.get("guest_token", ""),
            "x-twitter-auth-type": "OAuth2Session" if cookies.get("auth_token") else "",
            "x-twitter-active-user": "yes",
            "x-twitter-client-language": "en",
            "Origin": "https://twitter.com",
            "DNT": "1",
            "Sec-GPC": "1",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site",
            "Connection": "keep-alive",
            "Pragma": "no-cache",
            "Cache-Control": "no-cache",
            # oLYdXdvdHrDENpgQRhn/c2v/cj3SoIX67EyajoIa5y+ZmpxGNKiEFT1WlnSFv1BrQUVHRaFLp1c2Xx1iMaGOeqYgtygDow
            "x-client-transaction-id": randomTransactionId(),
        }
    )
    return dict(sorted({k.lower(): v for k, v in headers.items()}.items()))


def find_key(obj: any, key: str) -> list:
    """
    Find all values of a given key within a nested dict or list of dicts

    Most data of interest is nested, and sometimes defined by different schemas.
    It is not worth our time to enumerate all absolute paths to a given key, then update
    the paths in our parsing functions every time Twitter changes their API.
    Instead, we recursively search for the key here, then run post-processing functions on the results.

    @param obj: dictionary or list of dictionaries
    @param key: key to search for
    @return: list of values
    """

    def helper(obj: any, key: str, L: list) -> list:
        if not obj:
            return L

        if isinstance(obj, list):
            for e in obj:
                L.extend(helper(e, key, []))
            return L

        if isinstance(obj, dict) and obj.get(key):
            L.append(obj[key])

        if isinstance(obj, dict) and obj:
            for k in obj:
                L.extend(helper(obj[k], key, []))
        return L

    return helper(obj, key, [])


def log(logger: Logger, level: int, r: Response):
    def stat(r, txt, data):
        if level >= 1:
            logger.debug(f"{r.url.path}")
        if level >= 2:
            logger.debug(f"{r.url}")
        if level >= 3:
            logger.debug(f"{txt}")
        if level >= 4:
            logger.debug(f"{data}")

        try:
            limits = {k: v for k, v in r.headers.items() if "x-rate-limit" in k}
            current_time = int(time.time())
            wait = int(r.headers.get("x-rate-limit-reset", current_time)) - current_time
            remaining = limits.get("x-rate-limit-remaining")
            limit = limits.get("x-rate-limit-limit")
            logger.debug(f"remaining: {MAGENTA}{remaining}/{limit}{RESET} requests")
            logger.debug(f"reset:     {MAGENTA}{(wait / 60):.2f}{RESET} minutes")
        except Exception as e:
            logger.error(f"Rate limit info unavailable: {e}")

    try:
        status = r.status_code
        (
            txt,
            data,
        ) = r.text, r.json()
        if "json" in r.headers.get("content-type", ""):
            if data.get("errors") and not find_key(data, "instructions"):
                logger.error(f"[{RED}error{RESET}] {status} {data}")
            else:
                logger.debug(fmt_status(status))
                stat(r, txt, data)
        else:
            logger.debug(fmt_status(status))
            stat(r, txt, {})
    except Exception as e:
        logger.error(f"Failed to log: {e}")


def fmt_status(status: int) -> str:
    color = None
    if 200 <= status < 300:
        color = GREEN
    elif 300 <= status < 400:
        color = MAGENTA
    elif 400 <= status < 600:
        color = RED
    return f"[{color}{status}{RESET}]"


def get_ids(data: list | dict, operation: tuple) -> set:
    expr = ID_MAP[operation[-1]]
    return {k for k in find_key(data, "entryId") if re.search(expr, k)}


def dump(path: str, **kwargs):
    fname, data = list(kwargs.items())[0]
    out = Path(path)
    out.mkdir(exist_ok=True, parents=True)
    (out / f"{fname}_{time.time_ns()}.json").write_bytes(
        orjson.dumps(data, option=orjson.OPT_INDENT_2 | orjson.OPT_SORT_KEYS)
    )


def get_code(cls, retries=5) -> str | None:
    """Get verification code from Proton Mail inbox"""

    def poll_inbox():
        inbox = cls.inbox()
        for c in inbox.get("Conversations", []):
            if c["Senders"][0]["Address"] == "info@twitter.com":
                exprs = [
                    "Your Twitter confirmation code is (.+)",
                    "(.+) is your Twitter verification code",
                ]
                if temp := list(
                    filter(None, (re.search(expr, c["Subject"]) for expr in exprs))
                ):
                    return temp[0].group(1)

    for i in range(retries + 1):
        if code := poll_inbox():
            return code
        if i == retries:
            print("Max retries exceeded")
            return
        t = 2**i + random.random()
        print(f'Retrying in {f"{t:.2f}"} seconds')
        time.sleep(t)
