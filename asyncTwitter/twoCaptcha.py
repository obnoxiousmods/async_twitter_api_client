import trio
import anyio

from httpx import AsyncClient


class CaptchaQueue:
    def __init__(self, main, max_available_captchas):
        self.main = main
        self.max_available_captchas = max_available_captchas
        self.queue_send, self.queue_recv = trio.open_memory_channel(
            max_available_captchas
        )
        self.capacityLimiter = trio.CapacityLimiter(max_available_captchas)

    async def fill_queue(self):
        """
        This method fills the captcha queue up to its maximum capacity by
        submitting captcha creation tasks and adding the results to the queue.
        """
        for _ in range(self.max_available_captchas):
            await self.submit_captcha_task()

    async def get_captcha(self):
        """
        Retrieves a captcha from the queue. If the queue is empty, this will
        wait until a captcha becomes available. After retrieving a captcha,
        it submits a new task to ensure the queue is always filled.
        """
        captcha_result = await self.queue_recv.receive()

        # self.main.general.logger.info(f"Retrieved captcha from queue: {captcha_result}")

        return captcha_result

    async def submit_captcha_task(self):
        """
        Submits a captcha creation task and waits for its completion before
        adding the result to the queue.
        """
        async with self.capacityLimiter:
            v2Resp = await self.main.captcha.createTask(
                websiteKey=self.main.general.config.get(
                    "onlyFansWebsiteRecaptchaV2Key", None
                ),
                websiteUrl="https://onlyfans.com/",
                method="RecaptchaV2TaskProxyless",
                isEnterprise=False,
                isInvisible=False,
            )

            if not v2Resp.get("success", False):
                self.main.general.logger.error(
                    f"Failed to create captcha task: {v2Resp.get('data', 'Unknown error')}"
                )
                return False

            v2TaskId = v2Resp.get("taskId", None)

            self.main.general.logger.info(f"Created captcha task: {v2TaskId}")

            v2CaptchaResult = await self.main.captcha.checkTaskUntilFinished(v2TaskId)

            # Send the captcha result to the queue
            # self.main.general.logger.info(f"Adding captcha to queue: {v2CaptchaResult}")
            await self.queue_send.send(
                {
                    "success": True,
                    "v2": v2CaptchaResult,
                }
            )

    async def maintain_queue(self):
        """
        Keeps the queue filled with captcha tasks. This is a background task
        that continuously checks the queue's capacity and fills it as necessary.
        """

        while True:
            async with trio.open_nursery() as self.nursery:
                if (
                    self.capacityLimiter.borrowed_tokens < self.max_available_captchas
                    and self.queue_send.statistics().current_buffer_used
                    < self.max_available_captchas
                ):
                    newCaptchasToCreate = (
                        self.max_available_captchas
                        - self.capacityLimiter.borrowed_tokens
                    )

                    self.main.general.logger.info(
                        f"Queue is low, creating {newCaptchasToCreate} new captchas | {self.capacityLimiter.borrowed_tokens} / {self.max_available_captchas} tokens used."
                    )

                    for _ in range(newCaptchasToCreate):
                        self.nursery.start_soon(self.submit_captcha_task)
                else:
                    self.main.general.logger.info(
                        f"Queue is full, {self.capacityLimiter.borrowed_tokens} / {self.max_available_captchas} tokens used. Sleeping..."
                    )
            await trio.sleep(5)


class TwoCaptcha:
    def __init__(self, main: object, apiKey: str):
        self.main = main
        self.apiKey = apiKey

        self.baseUrl = "https://api.2captcha.com"

        self.client = AsyncClient(
            http2=False,
            verify=False,
            # proxies=self.main.general.config.get("proxy", 'http://127.0.0.1:8866'),
            proxies="http://127.0.0.1:8866",
            headers={"Content-Type": "application/json"},
        )

    async def checkTaskUntilFinished(
        self, taskId: str, sleepTime: int = 9, maxRetries: int = 15
    ):
        for retryCount in range(maxRetries):
            checkResults = await self.getTaskResult(taskId)

            if checkResults.get("status", None) == "processing":
                print(
                    f"Captcha task {taskId} is still processing, retrying in {sleepTime} seconds..."
                )
                await anyio.sleep(sleepTime)
                continue

            if checkResults.get("status", None) == "ready":
                return checkResults

            return {
                "success": False,
                "error": "Failed to get captcha results",
                "data": checkResults,
            }

        return {
            "success": False,
            "error": "Failed to get captcha results",
            "data": checkResults,
        }

    async def createTask(
        self,
        websiteUrl: str,
        websiteKey: str,
        method="FunCaptchaTaskProxyless",
        isInvisible: bool = False,
        isEnterprise: bool = False,
        cookies: dict = None,
    ):
        taskObject = {
            "type": method,
            "websiteURL": websiteUrl,
            "websitePublicKey": websiteKey,
            #"isInvisible": isInvisible,
            #"isEnterprise": isEnterprise,
            #"userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/113.0",
            #"apiDomain": "recaptcha.net",
            #"proxyType": 'socks5',
            #"proxyAddress": "212.83.142.158",
            #"proxyPort": "10554",
            #"pageAction": "login"
            #"proxyLogin": "user-default_geo-ca_session-RuWtjl6c",
            #"proxyPassword": "O4A2GhpNjgOw",
        }

        def convert_cookies_to_string(cookie_dict):
            cookies = [f"{key}={value}" for key, value in cookie_dict.items()]
            return '; '.join(cookies)
        
        if cookies:
            cookiesString = convert_cookies_to_string(cookies)
            taskObject["cookies"] = cookiesString


        if "V3" in method:
            taskObject["minScore"] = 0.9

        resp = await self.client.post(
            f"{self.baseUrl}/createTask",
            json={
                "clientKey": self.apiKey,
                "task": taskObject,
                "languagePool": "en",
            },
        )

        respJson = resp.json()

        errorId = respJson.get("errorId", None)
        taskId = respJson.get("taskId", None)

        if not taskId:
            return {
                "success": False,
                "error": f"Failed to create task: {errorId}",
                "data": respJson,
            }

        return {
            "success": True,
            "taskId": taskId,
        }

    async def getTaskResult(self, taskId: str):
        resp = await self.client.post(
            f"{self.baseUrl}/getTaskResult",
            json={
                "clientKey": self.apiKey,
                "taskId": taskId,
            },
        )

        respJson = resp.json()

        status = respJson.get("status", None)

        retDict = {
            "success": False
        }
        
        retDict.update(respJson)

        if status == "ready":
            retDict["success"] = True

        if status == "processing":
            retDict["success"] = False

        return retDict

if __name__ == "__main__":
    # testing function

    captchaInstance = TwoCaptcha(
        main=None,
        apiKey="9f5eaaf194011a395fed53f579a85c57",
    )

    async def main():
        task = await captchaInstance.createTask(
            websiteUrl="https://onlyfans.com/",
            websiteKey="6LddGoYgAAAAAHD275rVBjuOYXiofr1u4pFS5lHn",
            method="RecaptchaV3TaskProxyless",
            isEnterprise=True,
        )

        taskSuccess = task.get("success", False)
        taskId = task.get("taskId", None)

        if taskId:
            print(f"Created task: {taskId}")

            taskResults = await captchaInstance.checkTaskUntilFinished(taskId)

            print(taskResults)

    trio.run(main)
