import trio
import anyio

from httpx import AsyncClient


class TwoCaptcha:
    def __init__(self, main: object, apiKey: str):
        self.main = main
        self.apiKey = apiKey

        self.baseUrl = "https://api.2captcha.com"

        self.client = AsyncClient(
            http2=False,
            verify=False,
            # proxies=self.main.general.config.get("proxy", 'http://127.0.0.1:8866'),
            #proxies="http://127.0.0.1:8866",
            headers={"Content-Type": "application/json"},
        )

    async def checkBalance(self):
        resp = await self.client.post(
            f"{self.baseUrl}/getBalance",
            json={
                "clientKey": self.apiKey,
            },
        )

        respJson = resp.json()

        balance = respJson.get("balance", None)

        if not balance:
            return {
                "success": False,
                "error": "Failed to get balance",
                "data": respJson,
            }

        return {
            "success": True,
            "balance": balance,
        }

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
        cookies: dict = None,
        **kwargs,
    ):
        taskObject = {
            "type": method,
            "websiteURL": websiteUrl,
            "websitePublicKey": websiteKey,
            **kwargs
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
