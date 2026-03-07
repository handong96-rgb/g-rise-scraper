import requests
from bs4 import BeautifulSoup
import pandas as pd
import urllib3
import time
import base64
import urllib.parse

# 공공기관 사이트 SSL 경고 숨기기
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def get_encoded_q(page):
    """페이지 번호를 G-RISE 사이트 전용 암호(Base64)로 변환합니다."""
    # 1. 원래 형태의 문자열 생성
    raw_str = f"act=List&PageNum={page}"
    # 2. URL 인코딩 (act%3DList%26PageNum%3D...)
    url_encoded = urllib.parse.quote(raw_str)
    # 3. Base64 인코딩
    b64_encoded = base64.b64encode(url_encoded.encode('utf-8')).decode('utf-8')
    return b64_encoded

def get_total_pages(url, headers):
    """1페이지에 접속하여 전체 페이지 수를 파악합니다."""
    try:
        response = requests.get(url, headers=headers, verify=False)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        page_info = soup.select_one('span.page > span')
        if page_info:
            return int(page_info.get_text(strip=True))
    except Exception as e:
        print(f"전체 페이지 수 확인 중 오류 발생: {e}")
    return 21

def scrape_g_rise_family_final():
    final_results = []
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://www.g-riseon.or.kr/181/FamilyList.do"
    }

    base_url = "https://www.g-riseon.or.kr/181/FamilyList.do"
    
    print("1. 전체 페이지 수 파악 중...")
    # 1페이지용 암호를 만들어 접속
    first_page_url = f"{base_url}?q={get_encoded_q(1)}"
    total_pages = get_total_pages(first_page_url, headers)
    print(f" -> 총 {total_pages}페이지 확인 완료!\n")
    
    for page in range(1, total_pages + 1):
        print(f"[{page}/{total_pages}] 페이지 수집 중...")
        
        # 💡 [핵심 해결] 각 페이지 번호에 맞는 암호(Base64)를 생성하여 주소에 붙입니다.
        target_url = f"{base_url}?q={get_encoded_q(page)}"
        
        try:
            # 안전한 GET 방식으로 요청
            response = requests.get(target_url, headers=headers, verify=False)
            response.raise_for_status()
            response.encoding = 'utf-8'
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            company_items = soup.select('div.familyDB > ul.list > li')
            
            if not company_items:
                print(f"  -> {page}페이지에서 데이터를 찾지 못했습니다.")
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
            
            time.sleep(1) # 서버 보호를 위한 1초 휴식

        except Exception as e:
            print(f"오류 발생 ({page}페이지): {e}")
            continue

    return final_results

if __name__ == "__main__":
    data = scrape_g_rise_family_final()
    
    df = pd.DataFrame(data)
    
    columns_order = ['기업명', '대학명', '대표자', '사업자등록번호', '산업분류', '업종업태', '주소']
    for col in columns_order:
        if col not in df.columns:
            df[col] = ""
    df = df[columns_order]

    if not df.empty:
        # 이중 방어막: 이름과 주소가 같으면 중복 제거
        initial_count = len(df)
        df = df.drop_duplicates(subset=['기업명', '주소'], keep='first')
        print(f"\n[안내] 수집된 {initial_count}건 중 중복을 제거하여 실제 {len(df)}개의 유니크한 데이터가 남았습니다.")
        
        file_name = "G_RISE_가족회사.csv"
        df.to_csv(file_name, index=False, encoding="utf-8-sig")
        print(f"===== 🎉 수집 완료! =====")
        print(f"저장된 파일: {file_name}")
    else:
        print("\n수집된 데이터가 없습니다.")
