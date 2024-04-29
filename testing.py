import requests

headers = {
    "sec-ch-ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "upgrade-insecure-requests": "1",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "sec-fetch-site": "same-origin",
    "sec-fetch-mode": "navigate",
    "sec-fetch-user": "?1",
    "sec-fetch-dest": "document",
    "referer": "https://twitter.com/i/flow/login",
    "accept-encoding": "gzip, deflate, br, zstd",
    "accept-language": "en-US,en;q=0.9",
    "priority": "u=0, i",
    #"cookie": '_ga=GA1.2.396964430.1714338740; _gid=GA1.2.792491738.1714338740; kdt=m12M1xdg7Mw0a3TbACWbIZJlu8VBUL2P6A5dpJYj; lang=en; dnt=1; guest_id=v1%3A171436913069729690; guest_id_marketing=v1%3A171436913069729690; guest_id_ads=v1%3A171436913069729690; personalization_id="v1_m3Td5kYJdlAANN2W+uUNhw=="; gt=1784819612883832954; _twitter_sess=BAh7CSIKZmxhc2hJQzonQWN0aW9uQ29udHJvbGxlcjo6Rmxhc2g6OkZsYXNo%250ASGFzaHsABjoKQHVzZWR7ADoPY3JlYXRlZF9hdGwrCGQKXSiPAToMY3NyZl9p%250AZCIlMzRkMjJmOTBjYWU0ZWNjZTgwNDAyMzFiYzMzZDY2NjA6B2lkIiUyNmU0%250AMDdlN2YzZGQzYzFkNjBkZTZmMjllMGVmMWIxNg%253D%253D--2c40ae37af3d86c0038dd6e274d5e855ca2573d8; twid="u=1061735362350014464"; auth_token=20e72527a43d3f80ff1aff5e1db0512bfc54e182; ct0=0dee2493408e84c1bc084e1ba6ebab9cfbbe1b46edfae1b2c00bcc852e780560d78782f9354cbd7cc52f5de18d3a001d2376eb4cf93b72d22196e796eace1a782bc66d02a54e4cd46336d1e844a0ad14',
}
payload = None

response0 = requests.request(
    "GET", "https://twitter.com/account/access", headers=headers, data=payload
)
