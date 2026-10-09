import os
import requests
from supabase import create_client

# GitHub Secrets에 등록한 정보 가져오기
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Supabase URL 또는 Key가 설정되지 않았습니다.")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def run_scraper():
    # -------------------------------------------------------------
    # 1. 아까 변환하신 페이스콕 requests 주소/헤더/파라미터를 입력하세요
    # -------------------------------------------------------------
    url = "페이스콕_API_주소"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }
    params = {
        # 필요한 파라미터 값
    }

    # API 호출 (POST 방식이었다면 requests.post 사용)
    response = requests.get(url, headers=headers, params=params)

    if response.status_code == 200:
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
    else:
        print(f"요청 실패 (상태 코드): {response.status_code}")

if __name__ == "__main__":
    run_scraper()
