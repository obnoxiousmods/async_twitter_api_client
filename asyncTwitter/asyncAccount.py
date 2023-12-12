import orjson
import mimetypes
import random
import hashlib
import time
import logging

from logging import Logger
from tqdm import tqdm
from datetime import datetime
from httpx import AsyncClient
from .constants import (
    Operation,
    MAX_IMAGE_SIZE,
    MAX_GIF_SIZE,
    MAX_VIDEO_SIZE,
    UPLOAD_CHUNK_SIZE,
    MEDIA_UPLOAD_SUCCEED,
    MEDIA_UPLOAD_FAIL,
    LOG_CONFIG,
)
from .util import get_headers, log, urlencode, find_key, RED, RESET, Path
from uuid import uuid1, getnode
from string import ascii_letters

from .asyncLogin import asyncLogin


class asyncAccount:
    def __init__(
        self,
        **kwargs,
    ):
        self.save = kwargs.get("save", True)
        self.debug = kwargs.get("debug", 0)
        self.gql_api = "https://twitter.com/i/api/graphql"
        self.v1_api = "https://api.twitter.com/1.1"
        self.v2_api = "https://twitter.com/i/api/2"
        self.logger = self._init_logger(**kwargs)

    async def __ainit__(
        self, email=None, username=None, password=None, session=None, **kwargs
    ):
        self.session = await self._validate_session(
            email, username, password, session, **kwargs
        )

        return self.session

    async def asyncGQL(
        self,
        method: str,
        operation: tuple,
        variables: dict,
        features: dict = Operation.default_features,
    ) -> dict:
        qid, op = operation
        params = {
            "queryId": qid,
            "features": features,
            "variables": Operation.default_variables | variables,
        }
        if method == "POST":
            data = {"json": params}
        else:
            data = {"params": {k: orjson.dumps(v).decode() for k, v in params.items()}}
        r = await self.session.request(
            method=method,
            url=f"{self.gql_api}/{qid}/{op}",
            headers=get_headers(self.session),
            **data,
        )
        if self.debug:
            log(self.logger, self.debug, r)
        return r.json()

    async def asyncV1(self, path: str, params: dict) -> dict:
        headers = get_headers(self.session)
        headers["content-type"] = "application/x-www-form-urlencoded"
        v1Response = await self.session.post(
            f"{self.v1_api}/{path}", headers=headers, data=urlencode(params)
        )
        if self.debug:
            log(self.logger, self.debug, v1Response)
        return v1Response.json()

    async def asyncCreatePoll(
        self, text: str, choices: list[str], poll_duration: int
    ) -> dict:
        options = {
            "twitter:card": "poll4choice_text_only",
            "twitter:api:api:endpoint": "1",
            "twitter:long:duration_minutes": poll_duration,  # max: 10080
        }
        for i, c in enumerate(choices):
            options[f"twitter:string:choice{i + 1}_label"] = c

        headers = get_headers(self.session)
        headers["content-type"] = "application/x-www-form-urlencoded"
        url = "https://caps.twitter.com/v2/cards/create.json"
        createPollResponse = await self.session.post(
            url, headers=headers, params={"card_data": orjson.dumps(options).decode()}
        )
        card_uri = createPollResponse.json()["card_uri"]
        createPollResponse = await self.asyncTweet(
            text, poll_params={"card_uri": card_uri}
        )
        return createPollResponse

    async def asyncDM(self, text: str, receivers: list[int], media: str = "") -> dict:
        variables = {
            "message": {},
            "requestId": str(uuid1(getnode())),
            "target": {"participant_ids": receivers},
        }
        if media:
            media_id = self._upload_media(media, is_dm=True)
            variables["message"]["media"] = {"id": media_id, "text": text}
        else:
            variables["message"]["text"] = {"text": text}
        dmResponse = await self.asyncGQL(
            "POST", Operation.useSendMessageMutation, variables
        )
        if find_key(dmResponse, "dm_validation_failure_type"):
            self.logger.debug(f"{RED}Failed to send DM(s) to {receivers}{RESET}")
        return dmResponse

    async def asyncTweet(self, text: str, *, media: any = None, **kwargs) -> dict:
        variables = {
            "tweet_text": text,
            "dark_request": False,
            "media": {
                "media_entities": [],
                "possibly_sensitive": False,
            },
            "semantic_annotation_ids": [],
        }

        if reply_params := kwargs.get("reply_params", {}):
            variables |= reply_params
        if quote_params := kwargs.get("quote_params", {}):
            variables |= quote_params
        if poll_params := kwargs.get("poll_params", {}):
            variables |= poll_params

        draft = kwargs.get("draft")
        schedule = kwargs.get("schedule")

        if draft or schedule:
            variables = {
                "post_tweet_request": {
                    "auto_populate_reply_metadata": False,
                    "status": text,
                    "exclude_reply_user_ids": [],
                    "media_ids": [],
                },
            }
            if media:
                for m in media:
                    media_id = self._upload_media(m["media"])
                    variables["post_tweet_request"]["media_ids"].append(media_id)
                    if alt := m.get("alt"):
                        self._add_alt_text(media_id, alt)

            if schedule:
                variables["execute_at"] = (
                    datetime.strptime(schedule, "%Y-%m-%d %H:%M").timestamp()
                    if isinstance(schedule, str)
                    else schedule
                )
                return await self.asyncGQL(
                    "POST", Operation.CreateScheduledTweet, variables
                )

            return await self.asyncGQL("POST", Operation.CreateDraftTweet, variables)

        # regular tweet
        if media:
            for m in media:
                media_id = self._upload_media(m["media"])
                variables["media"]["media_entities"].append(
                    {"media_id": media_id, "tagged_users": m.get("tagged_users", [])}
                )
                if alt := m.get("alt"):
                    self._add_alt_text(media_id, alt)

        return await self.asyncGQL("POST", Operation.CreateTweet, variables)

    async def _upload_media(
        self, filename: str, is_dm: bool = False, is_profile=False
    ) -> int | None:
        """
        https://developer.twitter.com/en/docs/twitter-api/v1/media/upload-media/uploading-media/media-best-practices
        """

        def format_size(size: int) -> str:
            return f"{(size / 1e6):.2f} MB"

        def create_error_message(category: str, size: int, max_size: int) -> str:
            return f"cannot upload {format_size(size)} {category}, max size is {format_size(max_size)}"

        def check_media(category: str, size: int) -> None:
            if category == "image" and size > MAX_IMAGE_SIZE:
                raise Exception(create_error_message(category, size, MAX_IMAGE_SIZE))
            if category == "gif" and size > MAX_GIF_SIZE:
                raise Exception(create_error_message(category, size, MAX_GIF_SIZE))
            if category == "video" and size > MAX_VIDEO_SIZE:
                raise Exception(create_error_message(category, size, MAX_VIDEO_SIZE))

        # if is_profile:
        #     url = 'https://upload.twitter.com/i/media/upload.json'
        # else:
        #     url = 'https://upload.twitter.com/1.1/media/upload.json'

        url = "https://upload.twitter.com/i/media/upload.json"

        file = Path(filename)
        total_bytes = file.stat().st_size
        headers = get_headers(self.session)

        upload_type = "dm" if is_dm else "tweet"
        media_type = mimetypes.guess_type(file)[0]
        media_category = (
            f"{upload_type}_gif"
            if "gif" in media_type
            else f'{upload_type}_{media_type.split("/")[0]}'
        )

        check_media(media_category, total_bytes)

        params = {
            "command": "INIT",
            "media_type": media_type,
            "total_bytes": total_bytes,
            "media_category": media_category,
        }
        uploadMediaResponse = await self.session.post(
            url=url, headers=headers, params=params
        )

        if uploadMediaResponse.status_code >= 400:
            raise Exception(f"{uploadMediaResponse.text}")

        media_id = uploadMediaResponse.json()["media_id"]

        desc = f"uploading: {file.name}"
        with tqdm(
            total=total_bytes, desc=desc, unit="B", unit_scale=True, unit_divisor=1024
        ) as pbar:
            with open(file, "rb") as fp:
                i = 0
                while chunk := fp.read(UPLOAD_CHUNK_SIZE):
                    params = {
                        "command": "APPEND",
                        "media_id": media_id,
                        "segment_index": i,
                    }
                    try:
                        pad = bytes(
                            "".join(random.choices(ascii_letters, k=16)),
                            encoding="utf-8",
                        )
                        data = b"".join(
                            [
                                b"------WebKitFormBoundary",
                                pad,
                                b'\r\nContent-Disposition: form-data; name="media"; filename="blob"',
                                b"\r\nContent-Type: application/octet-stream",
                                b"\r\n\r\n",
                                chunk,
                                b"\r\n------WebKitFormBoundary",
                                pad,
                                b"--\r\n",
                            ]
                        )
                        _headers = {
                            b"content-type": b"multipart/form-data; boundary=----WebKitFormBoundary"
                            + pad
                        }
                        uploadMediaResponse = await self.session.post(
                            url=url,
                            headers=headers | _headers,
                            params=params,
                            content=data,
                        )
                    except Exception as e:
                        self.logger.error(
                            f"Failed to upload chunk, trying alternative method\n{e}"
                        )
                        try:
                            files = {"media": chunk}
                            uploadMediaResponse = await self.session.post(
                                url=url, headers=headers, params=params, files=files
                            )
                        except Exception as e:
                            self.logger.error(f"Failed to upload chunk\n{e}")
                            return

                    if (
                        uploadMediaResponse.status_code < 200
                        or uploadMediaResponse.status_code > 299
                    ):
                        self.logger.debug(
                            f"{RED}{uploadMediaResponse.status_code} {uploadMediaResponse.text}{RESET}"
                        )

                    i += 1
                    pbar.update(fp.tell() - pbar.n)

        params = {"command": "FINALIZE", "media_id": media_id, "allow_async": "true"}
        if is_dm:
            params |= {"original_md5": hashlib.md5(file.read_bytes()).hexdigest()}
        uploadMediaResponse = await self.session.post(
            url=url, headers=headers, params=params
        )
        if uploadMediaResponse.status_code == 400:
            self.logger.debug(
                f"{RED}{uploadMediaResponse.status_code} {uploadMediaResponse.text}{RESET}"
            )
            return

        # self.logger.debug(f'processing, please wait...')
        processing_info = uploadMediaResponse.json().get("processing_info")
        while processing_info:
            state = processing_info["state"]
            if error := processing_info.get("error"):
                self.logger.debug(f"{RED}{error}{RESET}")
                return
            if state == MEDIA_UPLOAD_SUCCEED:
                break
            if state == MEDIA_UPLOAD_FAIL:
                self.logger.debug(
                    f"{RED}{uploadMediaResponse.status_code} {uploadMediaResponse.text} {RESET}"
                )
                return
            check_after_secs = processing_info.get(
                "check_after_secs", random.randint(1, 5)
            )
            time.sleep(check_after_secs)
            params = {"command": "STATUS", "media_id": media_id}
            uploadMediaResponse = await self.session.get(
                url=url, headers=headers, params=params
            )
            processing_info = uploadMediaResponse.json().get("processing_info")
        # self.logger.debug

    @staticmethod
    async def _validate_session(*args, **kwargs):
        email, username, password, session = args

        # validate credentials
        if all((email, username, password)):
            session = await asyncLogin(email, username, password, **kwargs)
            session._init_with_cookies = False
            return session

        # invalid credentials, try validating session
        if session and all(session.cookies.get(c) for c in {"ct0", "auth_token"}):
            session._init_with_cookies = True
            return session

        # invalid credentials and session
        cookies = kwargs.get("cookies")

        # try validating cookies dict
        if isinstance(cookies, dict) and all(
            cookies.get(c) for c in {"ct0", "auth_token"}
        ):
            _session = AsyncClient(
                cookies=cookies,
                follow_redirects=True,
                proxies=kwargs.pop("proxies", None),
            )
            _session._init_with_cookies = True
            _session.headers.update(get_headers(_session))
            return _session

        # try validating cookies from file
        if isinstance(cookies, str):
            _session = AsyncClient(
                cookies=orjson.loads(Path(cookies).read_bytes()),
                follow_redirects=True,
                proxies=kwargs.pop("proxies", None),
            )
            _session._init_with_cookies = True
            _session.headers.update(get_headers(_session))
            return _session

        raise Exception(
            "Session not authenticated. "
            "Please use an authenticated session or remove the `session` argument and try again."
        )

    def _init_logger(self, **kwargs) -> Logger:
        if kwargs.get("debug"):
            cfg = kwargs.get("log_config")
            logging.config.dictConfig(cfg or LOG_CONFIG)

            # only support one logger
            logger_name = list(LOG_CONFIG["loggers"].keys())[0]

            # set level of all other loggers to ERROR
            for name in logging.root.manager.loggerDict:
                if name != logger_name:
                    logging.getLogger(name).setLevel(logging.ERROR)

            return logging.getLogger(logger_name)
