import os
import requests
from supabase import create_client

# GitHub Secrets에서 Supabase 정보 가져오기
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Supabase URL 또는 Key가 설정되지 않았습니다.")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


def run_scraper():
    # 페이스콕 요청 설정
    url = "https://facecock.co.kr/page/"

    cookies = {
        'PHPSESSID': '43bfa4dun6f7jedsch071b06jo',
        '2a0d2363701f23f8a75028924a3af643': 'MjExLjE5NC43OS40NA%3D%3D',
    }

    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
        'Cache-Control': 'max-age=0',
        'Connection': 'keep-alive',
        'Referer': 'https://facecock.co.kr/page/?pid=search&stx=%EC%9D%B4%EC%98%81%EC%A4%80',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/155.0.0.0 Safari/537.36',
    }

    params = {
        'pid': 'game_schedule',
        'ga_id': '4148',
        'bg_id': '195859',
    }

    # API 요청 보내기
    response = requests.get(url, params=params, cookies=cookies, headers=headers)

    if response.status_code == 200:
        try:
            res_data = response.json()
            rows_to_insert = []
            items = res_data if isinstance(res_data, list) else res_data.get('list', res_data.get('data', []))

            for item in items:
                match_id = str(item.get('match_id') or item.get('idx') or item.get('id', ''))
                rows_to_insert.append({
                    "match_id": match_id,
                    "tournament_name": item.get('tournament_title', '페이스콕 대회'),
                    "category": item.get('group_name') or item.get('class_name'),
                    "team1": f"{item.get('player1', '')} / {item.get('player2', '')}",
                    "team2": f"{item.get('player3', '')} / {item.get('player4', '')}",
                    "score": item.get('score'),
                    "status": item.get('status_str') or item.get('status')
                })

            if rows_to_insert:
                result = supabase.table("facecock_matches").upsert(
                    rows_to_insert, on_conflict="match_id"
                ).execute()
                print(f"총 {len(result.data)}건 저장/업데이트 완료!")
            else:
                print("저장할 데이터 항목이 없습니다.")

        except Exception as e:
            print(f"응답 처리 중 오류 발생 (JSON 파싱 등): {e}")
            print("수신된 응답 내용 일부:", response.text[:300])
    else:
        print(f"요청 실패 (상태 코드): {response.status_code}")


if __name__ == "__main__":
    run_scraper()
