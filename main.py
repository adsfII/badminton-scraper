import os
import time
import requests
from bs4 import BeautifulSoup
from supabase import create_client

# Supabase 연결 설정
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Supabase URL 또는 Key가 설정되지 않았습니다.")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/155.0.0.0 Safari/537.36',
    'Referer': 'https://facecock.co.kr/'
}

COOKIES = {
    'PHPSESSID': '43bfa4dun6f7jedsch071b06jo',
}

# 1. 수집 대상 대회 목록 (필요한 ga_id 및 bg_id 목록을 확장)
# ※ 특정 대회 목록을 직접 지정하거나, 검색 페이지에서 크롤링할 수 있습니다.
TOURNAMENT_TARGETS = [
    {"ga_id": "4148", "bg_id": "195859", "name": "2026 부안 노을배"},
    {"ga_id": "4148", "bg_id": "195860", "name": "2026 부안 노을배"},
    # 수집하고 싶은 대회 ga_id 및 bg_id를 계속 추가할 수 있습니다.
]


def fetch_matches_for_target(ga_id, bg_id, tournament_hint="페이스콕 대회"):
    """특정 대회/조(ga_id, bg_id)의 경기 결과를 수집하는 함수"""
    url = "https://facecock.co.kr/page/"
    params = {
        'pid': 'game_schedule',
        'ga_id': ga_id,
        'bg_id': bg_id,
    }

    try:
        response = requests.get(url, params=params, cookies=COOKIES, headers=HEADERS, timeout=10)
        if response.status_code != 200:
            print(f"[{tournament_hint}] (ga_id: {ga_id}) 요청 실패 (코드: {response.status_code})")
            return []

        soup = BeautifulSoup(response.text, 'html.parser')
        rows_to_insert = []

        # 테이블 행 추출
        tr_list = soup.select('table tr') or soup.select('.list_item') or soup.select('.game_list tr')

        idx = 1
        for tr in tr_list:
            cols = [td.get_text(strip=True) for td in tr.select('td, th')]

            # 데이터 컬럼이 유효한 경우만 추출
            if len(cols) >= 3:
                match_id = f"fc_{ga_id}_{bg_id}_{idx}"
                rows_to_insert.append({
                    "match_id": match_id,
                    "tournament_name": tournament_hint,
                    "category": cols[0] if len(cols) > 0 else "부서미상",
                    "team1": cols[1] if len(cols) > 1 else "",
                    "team2": cols[2] if len(cols) > 2 else "",
                    "score": cols[3] if len(cols) > 3 else "",
                    "status": cols[4] if len(cols) > 4 else "완료"
                })
                idx += 1

        return rows_to_insert

    except Exception as e:
        print(f"[{tournament_hint}] 수집 중 오류: {e}")
        return []


def run_scraper():
    print("=== 페이스콕 전체 대회 수집 시작 ===")
    total_saved = 0

    for target in TOURNAMENT_TARGETS:
        ga_id = target["ga_id"]
        bg_id = target["bg_id"]
        t_name = target.get("name", "페이스콕 대회")

        print(f"-> 수집 중: {t_name} (ga_id={ga_id}, bg_id={bg_id})")
        matches = fetch_matches_for_target(ga_id, bg_id, t_name)

        if matches:
            # Supabase에 Upsert 전송
            result = supabase.table("facecock_matches").upsert(
                matches, on_conflict="match_id"
            ).execute()
            count = len(result.data) if result.data else len(matches)
            total_saved += count
            print(f"   └ {count}건 저장 완료")
        else:
            print("   └ 수집할 데이터가 없거나 페이지 형식이 다릅니다.")

        # 페이스콕 서버 부하 및 IP 차단 방지를 위한 1초 대기
        time.sleep(1)

    print(f"\n=== 전체 완료: 총 {total_saved}건 저장됨 ===")


if __name__ == "__main__":
    run_scraper()
