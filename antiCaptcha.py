import anyio

from httpx import AsyncClient
from sys import exit

class antiCaptcha:
    def __init__(self, apiKey):
        if not apiKey or len(apiKey) != 32:
            exit("NEED ANTI CAPTCHA KEY")

        self.apiBase = "https://api.anti-captcha.com"
        self.apiKey = apiKey

        self.session = AsyncClient(
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            verify=False,
            timeout=120,
            #proxies='http://127.0.0.1:8866'
        )
        
    async def checkBalance(self):
        checkBalanceResponse = await self.session.post(
            url=f"{self.apiBase}/getBalance",
            json={"clientKey": self.apiKey},
        )

        jsonResponse = checkBalanceResponse.json()

        return jsonResponse

    async def test(self):
        submitResponse = await self.createImageToTextTask(
            "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"
        )

        if submitResponse["success"]:
            print(submitResponse["taskId"])
            taskResult = await self.getTaskResult(submitResponse["taskId"])
            print(taskResult)

        # taskResult = await self.getTaskResult('72515685')
        # print(taskResult)
        
    async def createArkoseTask(self, websiteUrl, websiteKey, threadCount=0):
        createTaskResponse = await self.session.post(
            url=f"{self.apiBase}/createTask",
            json={
                "clientKey": self.apiKey,
                "task": {
                    "type": "FunCaptchaTaskProxyless",
                    "websiteURL": websiteUrl,
                    "websitePublicKey": websiteKey,
                },
                "softId": 0,
            },
        )

        jsonResponse = createTaskResponse.json()

        taskId = jsonResponse.get("taskId", None)
        errorId = jsonResponse.get("errorId", None)

        if errorId:
            return {'success': False, 'json': jsonResponse}

        return {"success": True, "taskId": taskId}
        
    async def reportIncorrectRecaptcha(self, taskId):
        reportIncorrectRecaptchaResponse = await self.session.post(
            url=f"{self.apiBase}/reportIncorrectRecaptcha",
            json={
                "clientKey": self.apiKey,
                "taskId": taskId,
            },
        )

        jsonResponse = reportIncorrectRecaptchaResponse.json()

        return jsonResponse
    
    async def reportCorrectRecaptcha(self, taskId):
        reportCorrectRecaptchaResponse = await self.session.post(
            url=f"{self.apiBase}/reportCorrectRecaptcha",
            json={
                "clientKey": self.apiKey,
                "taskId": taskId,
            },
        )

        jsonResponse = reportCorrectRecaptchaResponse.json()

        return jsonResponse

    async def getTaskResult(self, taskId, sleepSecs=8, maxRetries=50, threadCount=0):
        for retryCount in range(maxRetries):
            try:
                getTaskResultResponse = await self.session.post(
                    url=f"{self.apiBase}/getTaskResult",
                    json={"clientKey": self.apiKey, "taskId": taskId},
                    timeout=60,
                )

                jsonResponse = getTaskResultResponse.json()

                errorCode = jsonResponse.get("errorCode", None)

                retDict = {
                    "success": False,
                }
                
                retDict.update(jsonResponse)

                if errorCode:
                    retDict["success"] = False
                    
                if jsonResponse["status"] == "processing":
                    print(
                        f"[T{threadCount}R{retryCount}] Captcha was processing, sleeping for {sleepSecs} seconds then continuing..."
                    )
                    await anyio.sleep(sleepSecs)
                    continue

                elif jsonResponse["status"] == "ready":
                    retDict["success"] = True
                    
                return retDict

            except Exception as e:
                print(f"[T{threadCount}R{retryCount}] Error getting task result: {e}")
                try:
                    print(jsonResponse)
                except Exception:
                    pass
                await anyio.sleep(sleepSecs)
                continue
            
        return {'success': False, 'error': 'Captcha timed out...'}

    async def createRecaptchaV2Task(self, websiteUrl, websiteKey, threadCount=0):
        createTaskResponse = await self.session.post(
            url=f"{self.apiBase}/createTask",
            json={
                "clientKey": self.apiKey,
                "task": {
                    "type": "RecaptchaV2EnterpriseTaskProxyless",
                    "websiteURL": websiteUrl,
                    "websiteKey": websiteKey,
                },
                "enterprisePayload": {
                    "s": "test",
                },
                "softId": 0,
            },
        )

        jsonResponse = createTaskResponse.json()

        taskId = jsonResponse.get("taskId", None)
        errorId = jsonResponse.get("errorId", None)
        errorCode = jsonResponse.get("errorCode", None)

        if errorId and 'BALANCE_NOT_ENOUGH' in errorCode:
            exit(f'[T{threadCount}] Anti-Captcha balance is too low, exiting...')
        
        if not taskId:
            return {'success': False, 'json': jsonResponse}

        return {"success": True, "taskId": taskId}
    
    async def createRecaptchaV3Task(self, websiteUrl, websiteKey, threadCount=0):
        createTaskResponse = await self.session.post(
            url=f"{self.apiBase}/createTask",
            json={
                "clientKey": self.apiKey,
                "task": {
                    "type": "RecaptchaV3TaskProxyless",
                    "websiteURL": websiteUrl,
                    "websiteKey": websiteKey,
                    "minScore": "0.3",
                },
                "softId": 0,
            },
        )

        jsonResponse = createTaskResponse.json()

        #print(jsonResponse)

        taskId = jsonResponse.get("taskId", None)
        errorId = jsonResponse.get("errorId", None)
        errorCode = jsonResponse.get("errorCode", None)

        if errorId and 'BALANCE_NOT_ENOUGH' in errorCode:
            exit(f'[T{threadCount}] Anti-Captcha balance is too low, exiting...')
        
        if not taskId:
            return {'success': False, 'json': jsonResponse}

        return {"success": True, "taskId": taskId}

    async def createImageToTextTask(self, base64Image):
        createTaskResponse = await self.session.post(
            url=f"{self.apiBase}/createTask",
            json={
                "clientKey": self.apiKey,
                "task": {
                    "type": "ImageToTextTask",
                    "body": base64Image,
                    "phrase": False,
                    "case": False,
                    "numeric": 0,
                    "math": False,
                    "minLength": 4,
                    "maxLength": 5,
                },
            },
        )

        jsonResponse = createTaskResponse.json()

        taskId = jsonResponse["taskId"]
        errorId = jsonResponse["errorId"]

        if errorId:
            return {"success": False, "json": jsonResponse}

        return {"success": True, "taskId": taskId}


if __name__ == "__main__":
    instance = antiCaptcha()
    anyio.run(instance.test)
