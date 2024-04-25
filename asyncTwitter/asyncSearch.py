import asyncio
import logging.config
import math
import random
import re
import time
import orjson
import anyio

from logging import Logger
from pathlib import Path
from httpx import AsyncClient
from .constants import Operation, LOG_CONFIG, GREEN, YELLOW, RESET
from .asyncLogin import asyncLogin
from .util import get_headers, find_key, build_params
from functools import partial

reset = "\x1b[0m"
colors = [f"\x1b[{i}m" for i in range(31, 37)]


class AsyncSearch:
    def __init__(
        self,
        email: str = None,
        username: str = None,
        password: str = None,
        session: AsyncClient = None,
        **kwargs,
    ):
        self.save = kwargs.get("save", True)
        self.debug = kwargs.get("debug", 0)
        self.logger = self._init_logger(**kwargs)
        self.rate_limits = {}

    async def asyncAuthenticate(
        self,
        email: str = None,
        username: str = None,
        password: str = None,
        session: AsyncClient = None,
        **kwargs,
    ):
        """
        This is used to authenticate the account.

        This used to be in __init__ but we can't await in __init__ so we have to do it here.
        """

        self.email = email
        self.username = username
        self.password = password
        self.twitterId = False
        self.twitterRestId = False
        self.cookies = kwargs.get("cookies")
        self.proxies = kwargs.get("proxies")

        self.session = await self._async_validate_session(
            self.email, self.username, self.password, session, **kwargs
        )

        return self.session

    async def asyncRun(
        self,
        queries: list[dict],
        limit: int = math.inf,
        out: str = "data/search_results",
        **kwargs,
    ):
        out = Path(out)
        out.mkdir(parents=True, exist_ok=True)
        processResults = await self.process(queries, limit, out, **kwargs)
        return processResults

    async def process(
        self, queries: list[dict], limit: int, out: Path, **kwargs
    ) -> list:
        results = []
        
        async with anyio.create_task_group() as tg:
            for count, query in enumerate(queries):
                partialPaginate = partial(
                    self.paginate, query=query, limit=limit, out=out, results=results, **kwargs
                )
                tg.start_soon(partialPaginate)
                if self.debug:
                    self.logger.info(f"Ran {count} search query")
                continue
            
        return results

    async def paginate(
        self, query: dict, limit: int, out: Path, results:list, **kwargs
    ) -> list[dict]:
        params = {
            "variables": {
                "count": 20,
                "querySource": "typed_query",
                "rawQuery": query["query"],
                "product": query["category"],
            },
            "features": Operation.default_features,
            "fieldToggles": {"withArticleRichContentState": False},
        }

        res = []
        cursor = ""
        total = set()

        while True:
            if cursor:
                params["variables"]["cursor"] = cursor
            
            backoffResults = await self.backoff(
                lambda: self.get(self.session, params), **kwargs
            )
            
            if not backoffResults:
                if self.debug:
                    self.logger.debug("Failed to backoff")
                continue
            data, entries, cursor = backoffResults
            res.extend(entries)
            if len(entries) <= 2 or len(total) >= limit:  # just cursors
                self.debug and self.logger.debug(
                    f'[{GREEN}success{RESET}] Returned {len(total)} search results for {query["query"]}'
                )
                results.append(res)
                return res
            total |= set(find_key(entries, "entryId"))
            self.debug and self.logger.debug(f'{query["query"]}')
            self.save and (out / f"{time.time_ns()}.json").write_bytes(
                orjson.dumps(entries)
            )

    async def get(self, client: AsyncClient, params: dict) -> tuple:
        _, operationQueryID, operationName = Operation.SearchTimeline
        response = await client.get(
            f"https://twitter.com/i/api/graphql/{operationQueryID}/{operationName}",
            params=build_params(params),
        )
        self.rate_limits[operationName] = {k: int(v) for k, v in response.headers.items() if 'rate-limit' in k}
        data = response.json()
        if self.debug:
            self.logger.info(f"Rate limits: {self.rate_limits[operationName]}")
        cursor = self.get_cursor(data)
        entries = [
            field
            for key in find_key(data, "entries")
            for field in key
            if re.search(r"^(tweet|user)-", field["entryId"])
        ]
        # add on query info
        for entry in entries:
            entry["query"] = params["variables"]["rawQuery"]
        return data, entries, cursor

    def get_cursor(self, data: list[dict]):
        for e in find_key(data, "content"):
            if e.get("cursorType") == "Bottom":
                return e["value"]

    async def backoff(self, fn, **kwargs):
        retries = kwargs.get("retries", 3)
        for i in range(retries + 1):
            try:
                data, entries, cursor = await fn()
                if errors := data.get("errors"):
                    for e in errors:
                        self.logger.warning(f'{YELLOW}{e.get("message")}{RESET}')
                        return [], [], ""
                ids = set(find_key(data, "entryId"))
                if len(ids) >= 2:
                    return data, entries, cursor
            except Exception as e:
                if i == retries:
                    if self.debug:
                        self.logger.debug(f"Max retries exceeded\n{e}")
                    return
                t = 2**i + random.random()
                if self.debug:
                    self.logger.debug(f'Retrying in {f"{t:.2f}"} seconds\t\t{e}')
                await asyncio.sleep(t)

    def _init_logger(self, **kwargs) -> Logger:
        if self.debug:
            cfg = kwargs.get("log_config")
            logging.config.dictConfig(cfg or LOG_CONFIG)

            # only support one logger
            logger_name = list(LOG_CONFIG["loggers"].keys())[0]

            # set level of all other loggers to ERROR
            for name in logging.root.manager.loggerDict:
                if name != logger_name:
                    logging.getLogger(name).setLevel(logging.ERROR)

            return logging.getLogger(logger_name)

    @staticmethod
    async def _async_validate_session(*args, **kwargs):
        email, username, password, session = args

        # validate credentials
        if all((email, username, password)):
            return await asyncLogin(email, username, password, **kwargs)

        # invalid credentials, try validating session
        if session and all(session.cookies.get(c) for c in {"ct0", "auth_token"}):
            return session

        # invalid credentials and session
        cookies = kwargs.get("cookies")

        # try validating cookies dict
        if isinstance(cookies, dict) and all(
            cookies.get(c) for c in {"ct0", "auth_token"}
        ):
            _session = AsyncClient(cookies=cookies, follow_redirects=True)
            _session.headers.update(get_headers(_session))
            return _session

        # try validating cookies from file
        if isinstance(cookies, str):
            _session = AsyncClient(
                cookies=orjson.loads(Path(cookies).read_bytes()), follow_redirects=True
            )
            _session.headers.update(get_headers(_session))
            return _session

        raise Exception(
            "Session not authenticated. "
            "Please use an authenticated session or remove the `session` argument and try again."
        )

    def id(self) -> int:
        """ Get User ID """
        if not self.twid:
            potentialTwid = self.session.cookies.get("twid")
            
            if not potentialTwid:
                raise Exception("Session is missing twid cookie")
            
            self.twid = int(potentialTwid.split("=")[-1].strip().rstrip())
            
        return self.twid

    def save_cookies(self, fname: str = None, toFile=True):
        """ Save cookies to file """
        cookies = self.session.cookies
        if toFile:
            Path(f'{fname or cookies.get("username")}.cookies').write_bytes(orjson.dumps(dict(cookies)))
        return dict(cookies)