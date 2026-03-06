import requests
from bs4 import BeautifulSoup
import pandas as pd
import urllib3
import time

# 공공기관 사이트 SSL 경고 숨기기
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==========================================
# 1. 가족회사(지주회사) 수집용 함수들
# ==========================================
def get_total_pages(url, headers):
    """가족회사 1페이지에 접속하여 전체 페이지 수를 파악합니다."""
    try:
        response = requests.get(url, headers=headers, verify=False)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        page_info = soup.select_one('span.page > span')
        if page_info:
            return int(page_info.get_text(strip=True))
        else:
            return 21
    except Exception as e:
        print(f"전체 페이지 수 확인 중 오류 발생: {e}")
        return 21

def scrape_g_rise_smart():
    final_results = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    base_url = "https://www.g-riseon.or.kr/181/FamilyList.do?pageIndex=1"
    
    total_pages = get_total_pages(base_url, headers)
    print(f"▶ 총 {total_pages}페이지를 수집합니다.")
    
    for page in range(1, total_pages + 1):
        print(f"  -> [{page}/{total_pages}] 페이지 수집 중...")
        url = f"https://www.g-riseon.or.kr/181/FamilyList.do?pageIndex={page}"
        
        try:
            response = requests.get(url, headers=headers, verify=False)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            company_items = soup.select('div.familyDB > ul.list > li')
            if not company_items:
                continue

            for item in company_items:
                data = {}
                name_tag = item.select_one('p.name')
                data['기업명'] = name_tag.get_text(strip=True) if name_tag else ""
                
                univ_tag = item.select_one('div.cate-wrap span.univ')
                data['대학명'] = univ_tag.get_text(strip=True) if univ_tag else ""
                
                etc_items = item.select('ul.etc > li')
                for etc in etc_items:
                    strong_text = etc.find('strong').get_text(strip=True) if etc.find('strong') else ""
                    p_text = etc.find('p').get_text(strip=True) if etc.find('p') else ""
                    if '산업분류' in strong_text: data['산업분류'] = p_text
                    elif '업종업태' in strong_text: data['업종업태'] = p_text

                detail_dls = item.select('div.family-detail-list > dl')
                for dl in detail_dls:
                    dt_text = dl.find('dt').get_text(strip=True) if dl.find('dt') else ""
                    dd_text = dl.find('dd').get_text(strip=True) if dl.find('dd') else ""
                    if '사업자등록번호' in dt_text: data['사업자등록번호'] = dd_text
                    elif '대표자' in dt_text: data['대표자'] = dd_text
                    elif '주소' in dt_text: data['주소'] = dd_text

                final_results.append(data)
            time.sleep(1)
        except Exception as e:
            print(f"오류 발생 ({page}페이지): {e}")
            continue

    return final_results


# ==========================================
# 2. 명품/PRE-명품강소기업 수집용 함수들
# ==========================================
def get_available_terms(session, url):
    """명품강소기업 웹페이지에 접속하여 현재 존재하는 탭(기수) 목록을 자동 추출합니다."""
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        response = session.get(url, headers=headers, verify=False)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        terms = []
        for li in soup.find_all('li', attrs={'data-term': True}):
            term_val = li.get('data-term')
            if term_val and term_val.isdigit():
                terms.append(int(term_val))
        return sorted(list(set(terms)))
    except Exception as e:
        return []

def scrape_all_prestige_companies():
    session = requests.Session()
    session.verify = False
    
    api_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "X-Requested-With": "XMLHttpRequest"
    }
    api_url = "https://www.g-riseon.or.kr/sub/prestigeCompanyList.do"
    all_data = []

    # [명품강소기업]
    url_normal = "https://www.g-riseon.or.kr/255/pageview.do"
    terms_normal = get_available_terms(session, url_normal)
    if not terms_normal: terms_normal = [11, 12, 13] 
    
    print(f"▶ 감지된 [명품강소기업] 기수: {terms_normal}")
    api_headers["Referer"] = url_normal
    
    for term in terms_normal:
        print(f"  -> {term}기 데이터 수집 중...")
        params = {"type": "A15001", "term": term}
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
                        "구분": "명품강소기업",
                        "기수": f"{term}기",
                        "기업명": item.get("comNm", ""),
                        "분야/업종": item.get("comBiztype", ""),
                        "대표자": item.get("comCeo", ""),
                        "주소": f"{addr1} {addr2}".strip()
                    })
        except Exception as e:
            print(f"  -> 오류 발생 ({term}기): {e}")

    # [PRE-명품강소기업]
    url_pre = "https://www.g-riseon.or.kr/256/pageview.do"
    terms_pre = get_available_terms(session, url_pre)
    if not terms_pre: terms_pre = [7, 8] 
    
    print(f"▶ 감지된 [PRE-명품강소기업] 기수: {terms_pre}")
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


# ==========================================
# 3. 메인 실행부 (한 번에 두 개 모두 돌리기)
# ==========================================
if __name__ == "__main__":
    print("==================================================")
    print(" 1. [가족회사] 데이터 수집 시작")
    print("==================================================")
    data_family = scrape_g_rise_smart()
    df_family = pd.DataFrame(data_family)
    
    # 컬럼 순서 정리
    columns_order = ['기업명', '대학명', '대표자', '사업자등록번호', '산업분류', '업종업태', '주소']
    for col in columns_order:
        if col not in df_family.columns:
            df_family[col] = ""
    df_family = df_family[columns_order]

    if not df_family.empty:
        file_family = "G_RISE_기업목록.csv"
        df_family.to_csv(file_family, index=False, encoding="utf-8-sig")
        print(f"✔ '{file_family}' 저장 완료! (총 {len(df_family)}개)")

    print("\n==================================================")
    print(" 2. [명품강소기업 통합] 데이터 수집 시작")
    print("==================================================")
    data_prestige = scrape_all_prestige_companies()
    df_prestige = pd.DataFrame(data_prestige)
    
    if not df_prestige.empty:
        file_prestige = "명품강소기업_통합_스마트.csv"
        df_prestige.to_csv(file_prestige, index=False, encoding="utf-8-sig")
        print(f"✔ '{file_prestige}' 저장 완료! (총 {len(df_prestige)}개)")

    print("\n==================================================")
    print(" 🎉 모든 데이터 수집 및 깃허브 저장이 완료되었습니다!")
    print("==================================================")
