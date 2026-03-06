import requests
import pandas as pd
import urllib3
from bs4 import BeautifulSoup

# 공공기관 사이트 SSL 경고 숨기기
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def get_available_terms(session, url):
    """웹페이지에 접속하여 현재 존재하는 기수(term) 목록을 자동으로 추출합니다."""
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    try:
        response = session.get(url, headers=headers, verify=False)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        terms = []
        # 'data-term' 속성을 가진 모든 태그를 찾아서 숫자를 빼냅니다.
        for li in soup.find_all('li', attrs={'data-term': True}):
            term_val = li.get('data-term')
            if term_val and term_val.isdigit():
                terms.append(int(term_val))
        
        # 중복을 제거하고 오름차순으로 정렬해서 반환합니다.
        return sorted(list(set(terms)))
    except Exception as e:
        print(f"기수 정보 추출 실패 ({url}): {e}")
        return []

def scrape_all_prestige_companies():
    print("===== 데이터 수집 시작 (미래 기수 자동 감지 모드) =====")
    
    session = requests.Session()
    session.verify = False
    
    # 서버 위장용 기본 헤더
    api_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "X-Requested-With": "XMLHttpRequest"
    }
    
    api_url = "https://www.g-riseon.or.kr/sub/prestigeCompanyList.do"
    all_data = []

    # -------------------------------------------------------------
    # 1. 명품강소기업 수집
    # -------------------------------------------------------------
    url_normal = "https://www.g-riseon.or.kr/255/pageview.do"
    terms_normal = get_available_terms(session, url_normal)
    
    # 추출된 기수가 없으면 예비용 기본값 사용
    if not terms_normal: terms_normal = [11, 12, 13] 
    
    print(f"\n▶ 감지된 [명품강소기업] 기수: {terms_normal}")
    api_headers["Referer"] = url_normal
    
    for term in terms_normal:
        print(f"  -> {term}기 데이터 수집 중...")
        params = {"type": "A15001", "term": term}
        try:
            response = session.get(api_url, params=params, headers=api_headers)
            response.raise_for_status()
            response.encoding = 'utf-8' # 한글 깨짐 방지
            data_list = response.json()
            
            if data_list:
                for item in data_list:
                    addr1 = item.get("comAddr1", "")
                    addr2 = item.get("comAddr2", "")
                    all_data.append({
                        "구분": "명품강소기업",
                        "기수": f"{term}기",
                        "기업명": item.get("comNm", ""),
                        "분야/업종": item.get("comBiztype", ""),
                        "대표자": item.get("comCeo", ""),
                        "주소": f"{addr1} {addr2}".strip()
                    })
        except Exception as e:
            print(f"  -> 오류 발생 ({term}기): {e}")

    # -------------------------------------------------------------
    # 2. PRE-명품강소기업 수집
    # -------------------------------------------------------------
    url_pre = "https://www.g-riseon.or.kr/256/pageview.do"
    terms_pre = get_available_terms(session, url_pre)
    
    # 추출된 기수가 없으면 예비용 기본값 사용
    if not terms_pre: terms_pre = [7, 8] 
    
    print(f"\n▶ 감지된 [PRE-명품강소기업] 기수: {terms_pre}")
    api_headers["Referer"] = url_pre
    
    for term in terms_pre:
        print(f"  -> {term}기 데이터 수집 중...")
        params = {"type": "A15002", "term": term}
        try:
            response = session.get(api_url, params=params, headers=api_headers)
            response.raise_for_status()
            response.encoding = 'utf-8'
            data_list = response.json()
            
            if data_list:
                for item in data_list:
                    addr1 = item.get("comAddr1", "")
                    addr2 = item.get("comAddr2", "")
                    all_data.append({
                        "구분": "PRE-명품강소기업",
                        "기수": f"{term}기",
                        "기업명": item.get("comNm", ""),
                        "분야/업종": item.get("comBiztype", ""),
                        "대표자": item.get("comCeo", ""),
                        "주소": f"{addr1} {addr2}".strip()
                    })
        except Exception as e:
            print(f"  -> 오류 발생 ({term}기): {e}")

    return all_data

# 실행부
if __name__ == "__main__":
    results = scrape_all_prestige_companies()
    
    df = pd.DataFrame(results)
    
    if not df.empty:
        file_name = "명품강소기업_통합_스마트.csv"
        df.to_csv(file_name, index=False, encoding="utf-8-sig")
        print(f"\n===== 🎉 수집 완료! =====")
        print(f"총 {len(df)}개의 기업 정보를 '{file_name}'로 저장했습니다.")
    else:
        print("\n수집된 데이터가 없습니다.")
