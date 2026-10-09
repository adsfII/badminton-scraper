import requests

cookies = {
    'PHPSESSID': '43bfa4dun6f7jedsch071b06jo',
    '2a0d2363701f23f8a75028924a3af643': 'MjExLjE5NC43OS40NA%3D%3D',
}

headers = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/jxl,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
    'Cache-Control': 'max-age=0',
    'Connection': 'keep-alive',
    'If-Modified-Since': 'Fri, 09 Oct 2026 07:24:28 GMT',
    'Referer': 'https://facecock.co.kr/page/?pid=search&stx=%EC%9D%B4%EC%98%81%EC%A4%80',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'same-origin',
    'Sec-Fetch-User': '?1',
    'Upgrade-Insecure-Requests': '1',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/155.0.0.0 Safari/537.36',
    'sec-ch-ua': '"Google Chrome";v="155", "Chromium";v="155", "Not(A:Brand";v="24"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    # 'Cookie': 'PHPSESSID=43bfa4dun6f7jedsch071b06jo; 2a0d2363701f23f8a75028924a3af643=MjExLjE5NC43OS40NA%3D%3D',
}

params = {
    'pid': 'game_schedule',
    'ga_id': '4148',
    'bg_id': '195859',
}

response = requests.get('https://facecock.co.kr/page/', params=params, cookies=cookies, headers=headers)
