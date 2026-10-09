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

BASE_URL = "https://facecock.co.kr/page/"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/155.0.0.0 Safari/537.36',
    'Referer': 'https://facecock.co.kr/'
}

COOKIES = {
    'PHPSESSID': '43bfa4dun6f7jedsch071b06jo',
}


def scan_tournaments_in_range(start_ga_id=4050, end_ga_id=4150):
    """
    ga_id 범위를 순회하며 유효한 대회 및 세부 조(bg_id) 목록을 자동 발굴합니다.
    """
    targets = []
    print(f"🔍 페이스콕 대회 탐색 시작 (ga_id 범위: {start_ga_id} ~ {end_ga_id})...")

    for ga_id in range(start_ga_id, end_ga_id + 1):
        url = f"{BASE_URL}?pid=game_schedule&ga_id={ga_id}"
        try:
            res = requests.get(url, cookies=COOKIES, headers=HEADERS, timeout=5)
            if res.status_code != 200:
                continue

            soup = BeautifulSoup(res.text, 'html.parser')

            # 1. 대회 이름 파싱 (select 또는 title 태그)
            ga_select = soup.select_one('select[name="ga_id"]')
            ga_name = f"대회 #{ga_id}"

            if ga_select:
                selected_opt = ga_select.find('option', selected=True) or ga_select.find('option', value=str(ga_id))
                if selected_opt:
                    ga_name = selected_opt.get_text(strip=True)

            # 2. 하위 부서/조 (bg_id) 옵션 전체 추출
            bg_select = soup.select_one('select[name="bg_id"]')
            if bg_select:
                bg_options = bg_select.find_all('option')
                found_count = 0
                for opt in bg_options:
                    bg_id = opt.get('value', '').strip()
                    bg_name = opt.get_text(strip=True)

                    if bg_id and bg_id != "0":
                        targets.append({
                            "ga_id": str(ga_id),
                            "bg_id": bg_id,
                            "name": f"[{ga_name}] {bg_name}"
                        })
                        found_count += 1

                if found_count > 0:
                    print(f"  ✓ 발견: {ga_name} (ga_id: {ga_id}) -> {found_count}개 조 발견")

        except Exception as e:
            continue

        time.sleep(0.3)  # 빠른 탐색 대기시간

    print(f"🎯 총 {len(targets)}개의 대진/조 타깃 탐색 완료!\n")
    return targets


def fetch_matches_for_target(ga_id, bg_id, tournament_hint):
    """특정 (ga_id, bg_id)의 경기 결과를 수집"""
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
                # 테이블 헤더 행 제외
                if "선수" in cols[1] or "팀" in cols[1] or "종목" in cols[0]:
                    continue

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

    except Exception:
        return []


def run_scraper():
    print("=== 페이스콕 광범위 대회 자동 수집 시작 ===")

    # 탐색할 ga_id 범위 설정 (최근 100개 대회 탐색)
    # 필요시 3900~4150 등으로 넓힐 수 있습니다.
    targets = scan_tournaments_in_range(start_ga_id=4050, end_ga_id=4150)

    if not targets:
        print("탐색된 대회가 없습니다. 기본 백업 타깃으로 진행합니다.")
        targets = [{"ga_id": "4148", "bg_id": "195859", "name": "2026 부안 노을배"}]

    total_saved = 0
    batch_rows = []

    # 데이터 수집 및 DB 전송
    for idx, target in enumerate(targets, 1):
        ga_id = target["ga_id"]
        bg_id = target["bg_id"]
        t_name = target["name"]

        matches = fetch_matches_for_target(ga_id, bg_id, t_name)

        if matches:
            batch_rows.extend(matches)
            print(f"[{idx}/{len(targets)}] {t_name} -> {len(matches)}건 수집")

        # 50건 이상 쌓이거나 마지막이면 Supabase 배치 전송
        if len(batch_rows) >= 50 or idx == len(targets):
            if batch_rows:
                try:
                    result = supabase.table("facecock_matches").upsert(
                        batch_rows, on_conflict="match_id"
                    ).execute()
                    saved_cnt = len(result.data) if result.data else len(batch_rows)
                    total_saved += saved_cnt
                    print(f"   💾 Supabase에 {saved_cnt}건 데이터 저장 완료 (누적: {total_saved}건)")
                    batch_rows = []
                except Exception as e:
                    print(f"   ❌ DB 저장 오류: {e}")

        time.sleep(0.5)

    print(f"\n==========================================")
    print(f"🎉 수집 완료! 총 {total_saved}건의 경기 데이터가 DB에 쌓였습니다.")
    print(f"==========================================")


if __name__ == "__main__":
    run_scraper()
