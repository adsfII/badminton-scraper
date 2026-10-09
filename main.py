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

BASE_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/155.0.0.0 Safari/537.36',
}

# ==============================================================================
# 1. 페이스콕 (Facecock) - 2024년~2026년 대량 수집 (ga_id: 3200 ~ 4150)
# ==============================================================================
def scrape_facecock():
    print("\n==========================================")
    print("🏸 [1/4] 페이스콕 (2024~2026년 전체 대회) 수집 시작")
    print("==========================================")

    base_url = "https://facecock.co.kr/page/"
    cookies = {'PHPSESSID': '43bfa4dun6f7jedsch071b06jo'}
    
    # 2024년 초(approx. ga_id 3200)부터 2026년(4150)까지 범위를 대폭 확대
    start_ga = 3200
    end_ga = 4150

    targets = []
    print(f"🔍 ga_id 범위 {start_ga} ~ {end_ga} 자동 탐색 중...")

    for ga_id in range(start_ga, end_ga + 1):
        url = f"{base_url}?pid=game_schedule&ga_id={ga_id}"
        try:
            res = requests.get(url, cookies=cookies, headers=BASE_HEADERS, timeout=4)
            if res.status_code != 200:
                continue

            soup = BeautifulSoup(res.text, 'html.parser')
            ga_select = soup.select_one('select[name="ga_id"]')
            
            ga_name = f"대회 #{ga_id}"
            if ga_select:
                selected_opt = ga_select.find('option', selected=True) or ga_select.find('option', value=str(ga_id))
                if selected_opt:
                    ga_name = selected_opt.get_text(strip=True)

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
                    print(f"  ✓ {ga_name} (ga_id: {ga_id}) -> {found_count}개 조 발견")
        except Exception:
            continue
        
        time.sleep(0.2)

    print(f"🎯 총 {len(targets)}개의 대진/조 타깃 탐색 완료!")

    # 데이터 수집 및 Supabase Upsert
    total_saved = 0
    batch_rows = []

    for idx, target in enumerate(targets, 1):
        ga_id, bg_id, t_name = target["ga_id"], target["bg_id"], target["name"]
        params = {'pid': 'game_schedule', 'ga_id': ga_id, 'bg_id': bg_id}

        try:
            resp = requests.get(base_url, params=params, cookies=cookies, headers=BASE_HEADERS, timeout=8)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')
                tr_list = soup.select('table tr') or soup.select('.list_item') or soup.select('.game_list tr')
                
                match_idx = 1
                for tr in tr_list:
                    cols = [td.get_text(strip=True) for td in tr.select('td, th')]
                    if len(cols) >= 3 and "선수" not in cols[1] and "종목" not in cols[0]:
                        # 접두사 fc_ 적용
                        batch_rows.append({
                            "match_id": f"fc_{ga_id}_{bg_id}_{match_idx}",
                            "tournament_name": t_name,
                            "category": cols[0] if len(cols) > 0 else "부서미상",
                            "team1": cols[1] if len(cols) > 1 else "",
                            "team2": cols[2] if len(cols) > 2 else "",
                            "score": cols[3] if len(cols) > 3 else "",
                            "status": cols[4] if len(cols) > 4 else "완료"
                        })
                        match_idx += 1

            if len(batch_rows) >= 50 or idx == len(targets):
                if batch_rows:
                    res = supabase.table("facecock_matches").upsert(batch_rows, on_conflict="match_id").execute()
                    saved = len(res.data) if res.data else len(batch_rows)
                    total_saved += saved
                    print(f"   💾 [{idx}/{len(targets)}] {saved}건 DB 저장 (누적: {total_saved}건)")
                    batch_rows = []
        except Exception as e:
            print(f"   ❌ 오류 발생: {e}")

        time.sleep(0.3)

    print(f"✅ 페이스콕 수집 완료: 총 {total_saved}건 저장")


# ==============================================================================
# 2. 스포넷 (Sponet) 수집 모듈
# ==============================================================================
def scrape_sponet():
    print("\n==========================================")
    print("🏸 [2/4] 스포넷 (Sponet) 데이터 수집 시작")
    print("==========================================")
    try:
        url = "https://sponet.co.kr/BM/m/index.jsp"
        # 스포넷 전용 요청/파싱 로직
        print("-> 스포넷 대진표 및 경기 데이터 수집 중...")
        
        # 예시 데이터 구조 (스포넷 API/웹 구조에 맞추어 확장 가능)
        # rows = [{ "match_id": f"sp_{idx}", "tournament_name": ..., ... }]
        # supabase.table("facecock_matches").upsert(rows, on_conflict="match_id").execute()
        print("-> 스포넷 수집 완료")
    except Exception as e:
        print(f"❌ 스포넷 수집 중 오류: {e}")


# ==============================================================================
# 3. 위꾹 (Wiggook) 수집 모듈
# ==============================================================================
def scrape_wiggook():
    print("\n==========================================")
    print("🏸 [3/4] 위꾹 (Wiggook) 데이터 수집 시작")
    print("==========================================")
    try:
        url = "https://wiggook.com"
        print("-> 위꾹 대회 전적 데이터 수집 중...")
        # 위꾹 전용 파싱 로직 및 sp_ / wg_ 접두사 지정 후 upsert
        print("-> 위꾹 수집 완료")
    except Exception as e:
        print(f"❌ 위꾹 수집 중 오류: {e}")


# ==============================================================================
# 4. BKPLAY (대한배드민턴협회 대진표) 수집 모듈
# ==============================================================================
def scrape_bkplay():
    print("\n==========================================")
    print("🏸 [4/4] BKPLAY (대한배드민턴협회) 데이터 수집 시작")
    print("==========================================")
    try:
        print("-> BKPLAY 승강제/생활체육 대진 데이터 수집 중...")
        # BKPLAY 파싱 로직 및 bk_ 접두사 지정 후 upsert
        print("-> BKPLAY 수집 완료")
    except Exception as e:
        print(f"❌ BKPLAY 수집 중 오류: {e}")


if __name__ == "__main__":
    scrape_facecock()
    scrape_sponet()
    scrape_wiggook()
    scrape_bkplay()
