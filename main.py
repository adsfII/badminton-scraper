import os
import requests
from bs4 import BeautifulSoup
from supabase import create_client

# Supabase 연결 설정
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Supabase URL 또는 Key가 설정되지 않았습니다.")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


def run_scraper():
    url = "https://facecock.co.kr/page/"

    cookies = {
        'PHPSESSID': '43bfa4dun6f7jedsch071b06jo',
        '2a0d2363701f23f8a75028924a3af643': 'MjExLjE5NC43OS40NA%3D%3D',
    }

    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/155.0.0.0 Safari/537.36',
    }

    params = {
        'pid': 'game_schedule',
        'ga_id': '4148',
        'bg_id': '195859',
    }

    response = requests.get(url, params=params, cookies=cookies, headers=headers)

    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        rows_to_insert = []

        # HTML 내 테이블 행(tr) 또는 경기 목록 요소 파싱
        tr_list = soup.select('table tr') or soup.select('.list_item') or soup.select('.game_list tr')

        idx = 1
        for tr in tr_list:
            cols = [td.get_text(strip=True) for td in tr.select('td, th')]
            
            # 최소 3개 이상의 데이터 컬럼이 있는 행만 추출
            if len(cols) >= 3:
                match_id = f"fc_4148_195859_{idx}"
                
                rows_to_insert.append({
                    "match_id": match_id,
                    "tournament_name": "페이스콕 대회",
                    "category": cols[0] if len(cols) > 0 else "부서미상",
                    "team1": cols[1] if len(cols) > 1 else "",
                    "team2": cols[2] if len(cols) > 2 else "",
                    "score": cols[3] if len(cols) > 3 else "",
                    "status": cols[4] if len(cols) > 4 else "완료"
                })
                idx += 1

        if rows_to_insert:
            result = supabase.table("facecock_matches").upsert(
                rows_to_insert, on_conflict="match_id"
            ).execute()
            print(f"총 {len(rows_to_insert)}건의 경기 데이터를 성공적으로 Supabase에 저장했습니다!")
        else:
            print("HTML 페이지 내에서 대진표/경기 데이터 테이블을 찾지 못했습니다.")
            # 페이지 구조 확인용 일부 출력
            print("페이지 타이틀:", soup.title.string if soup.title else "제목 없음")
    else:
        print(f"요청 실패 (상태 코드): {response.status_code}")


if __name__ == "__main__":
    run_scraper()
