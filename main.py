import os
import time
from urllib.parse import parse_qs, urlparse
import requests
from bs4 import BeautifulSoup
from supabase import create_client

# Supabase 연결 설정
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Supabase URL 또는 Key가 설정되지 않았습니다.")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

BASE_URL = "https://facecock.co.kr/page/"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/155.0.0.0 Safari/537.36',
    'Referer': 'https://facecock.co.kr/'
}

COOKIES = {
    'PHPSESSID': '43bfa4dun6f7jedsch071b06jo',
}


def get_all_tournament_targets():
    """
    페이스콕 페이지의 <select> 요소 및 <a> 링크에서 ga_id와 bg_id 조합을 자동으로 추출합니다.
    """
    targets = []
    seen_keys = set()

    print("🔍 페이스콕 대회 및 대진(ga_id, bg_id) 자동 탐색 중...")

    # 1. 메인 대진표/대회 페이지 조회
    search_url = f"{BASE_URL}?pid=game_schedule"
    try:
        res = requests.get(search_url, cookies=COOKIES, headers=HEADERS, timeout=10)
        if res.status_code != 200:
            print(f"대회 목록 페이지 접근 실패 (상태 코드: {res.status_code})")
            return targets

        soup = BeautifulSoup(res.text, 'html.parser')

        # A. <select name="ga_id"> 드롭다운 옵션 탐색
        ga_select = soup.select_one('select[name="ga_id"]')
        ga_ids = []

        if ga_select:
            for option in ga_select.find_all('option'):
                val = option.get('value', '').strip()
                name = option.get_text(strip=True)
                if val and val != "0":
                    ga_ids.append((val, name))

        # 각 대회(ga_id)별 하위 부서/조(bg_id) 자동 수집
        if ga_ids:
            for ga_id, ga_name in ga_ids[:10]: # 최근 10개 대회 탐색
                sub_url = f"{BASE_URL}?pid=game_schedule&ga_id={ga_id}"
                sub_res = requests.get(sub_url, cookies=COOKIES, headers=HEADERS, timeout=10)
                
                if sub_res.status_code == 200:
                    sub_soup = BeautifulSoup(sub_res.text, 'html.parser')
                    bg_sel = sub_soup.select_one('select[name="bg_id"]')
                    
                    if bg_sel:
                        for opt in bg_sel.find_all('option'):
                            bg_val = opt.get('value', '').strip()
                            bg_name = opt.get_text(strip=True)
                            if bg_val and bg_val != "0":
                                key = (ga_id, bg_val)
                                if key not in seen_keys:
                                    seen_keys.add(key)
                                    targets.append({
                                        "ga_id": ga_id,
                                        "bg_id": bg_val,
                                        "name": f"{ga_name} - {bg_name}"
                                    })
                time.sleep(0.5)

        # B. HTML 내 <a> 링크 주소에서 ga_id, bg_id 파라미터 보완 추출
        links = soup.find_all('a', href=True)
        for a in links:
            href = a['href']
            parsed = urlparse(href)
            params = parse_qs(parsed.query)

            if 'ga_id' in params and 'bg_id' in params:
                ga_id = params['ga_id'][0]
                bg_id = params['bg_id'][0]
                key = (ga_id, bg_id)

                if key not in seen_keys:
                    seen_keys.add(key)
                    t_title = a.get_text(strip=True) or f"대회_{ga_id}"
                    targets.append({
                        "ga_id": ga_id,
                        "bg_id": bg_id,
                        "name": t_title
                    })

    except Exception as e:
        print(f"대회 목록 탐색 중 오류 발생: {e}")

    print(f"총 {len(targets)}개의 대진(ga_id/bg_id) 타깃을 발견했습니다.")
    return targets


def fetch_matches_for_target(ga_id, bg_id, tournament_hint="페이스콕 대회"):
    """특정 (ga_id, bg_id)의 경기 데이터 파싱"""
    params = {
        'pid': 'game_schedule',
        'ga_id': ga_id,
        'bg_id': bg_id,
    }

    try:
        response = requests.get(BASE_URL, params=params, cookies=COOKIES, headers=HEADERS, timeout=10)
        if response.status_code != 200:
            return []

        soup = BeautifulSoup(response.text, 'html.parser')
        rows_to_insert = []

        tr_list = soup.select('table tr') or soup.select('.list_item') or soup.select('.game_list tr')

        idx = 1
        for tr in tr_list:
            cols = [td.get_text(strip=True) for td in tr.select('td, th')]

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
        print(f"[{tournament_hint}] 데이터 수집 실패: {e}")
        return []


def run_scraper():
    print("=== 페이스콕 자동 탐색 및 대량 수집 시작 ===")

    # 1. 자동 탐색 수행
    targets = get_all_tournament_targets()

    # 탐색된 결과가 없을 경우 백업 타깃 실행
    if not targets:
        print("자동 탐색 결과가 없어 기본 지정 타깃을 수집합니다.")
        targets = [
            {"ga_id": "4148", "bg_id": "195859", "name": "2026 부안 노을배"},
        ]

    total_saved = 0

    # 2. 수집 대상 순회 실행
    for idx, target in enumerate(targets, 1):
        ga_id = target["ga_id"]
        bg_id = target["bg_id"]
        t_name = target.get("name", "페이스콕 대회")

        print(f"[{idx}/{len(targets)}] 수집 중: {t_name} (ga_id={ga_id}, bg_id={bg_id})")
        matches = fetch_matches_for_target(ga_id, bg_id, t_name)

        if matches:
            result = supabase.table("facecock_matches").upsert(
                matches, on_conflict="match_id"
            ).execute()
            count = len(result.data) if result.data else len(matches)
            total_saved += count
            print(f"   └ {count}건 저장/업데이트 완료")
        else:
            print("   └ 경기 데이터 없음")

        time.sleep(1)  # IP 차단 방지 대기시간

    print(f"\n=== 대량 수집 완료: 총 {total_saved}건 저장됨 ===")


if __name__ == "__main__":
    run_scraper()
