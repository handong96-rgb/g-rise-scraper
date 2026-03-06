import requests
from bs4 import BeautifulSoup
import pandas as pd
import urllib3
import time

# 공공기관 사이트 SSL 경고 숨기기
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def get_total_pages(url, headers):
    """1페이지에 접속하여 전체 페이지 수를 파악합니다."""
    try:
        response = requests.get(url, headers=headers, verify=False)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 'PAGE : 1 / 21' 텍스트가 있는 부분에서 '21'을 찾아냅니다.
        page_info = soup.select_one('span.page > span')
        
        if page_info:
            # 텍스트에서 공백 등을 제거하고 숫자만 추출
            total_pages = int(page_info.get_text(strip=True))
            return total_pages
        else:
            print("전체 페이지 수를 찾을 수 없어 기본값(21)으로 설정합니다.")
            return 21 # 만약 못 찾으면 안전하게 21로 설정
            
    except Exception as e:
        print(f"전체 페이지 수 확인 중 오류 발생: {e}")
        return 21

def scrape_g_rise_smart():
    final_results = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    base_url = "https://www.g-riseon.or.kr/181/FamilyList.do?pageIndex=1"
    
    # 1. 먼저 전체 페이지 수를 알아냅니다.
    print("전체 페이지 수를 확인 중입니다...")
    total_pages = get_total_pages(base_url, headers)
    print(f"확인 완료! 총 {total_pages}페이지를 수집합니다.\n")
    
    # 2. 파악한 전체 페이지 수만큼만 반복합니다.
    for page in range(1, total_pages + 1):
        print(f"[{page}/{total_pages}] 페이지 수집 중...")
        url = f"https://www.g-riseon.or.kr/181/FamilyList.do?pageIndex={page}"
        
        try:
            response = requests.get(url, headers=headers, verify=False)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 모든 기업 항목(<li> 태그)을 찾습니다.
            company_items = soup.select('div.familyDB > ul.list > li')
            
            if not company_items:
                print(f"  -> {page}페이지에서 데이터를 찾지 못했습니다.")
                continue

            for item in company_items:
                data = {}
                
                # 기업명 추출
                name_tag = item.select_one('p.name')
                data['기업명'] = name_tag.get_text(strip=True) if name_tag else ""
                
                # 대학명 추출
                univ_tag = item.select_one('div.cate-wrap span.univ')
                data['대학명'] = univ_tag.get_text(strip=True) if univ_tag else ""
                
                # 외부 노출 정보 (산업분류, 업종업태) 추출
                etc_items = item.select('ul.etc > li')
                for etc in etc_items:
                    strong_text = etc.find('strong').get_text(strip=True) if etc.find('strong') else ""
                    p_text = etc.find('p').get_text(strip=True) if etc.find('p') else ""
                    
                    if '산업분류' in strong_text: data['산업분류'] = p_text
                    elif '업종업태' in strong_text: data['업종업태'] = p_text

                # 모바일용 숨김 박스 내 상세 정보 추출
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

# 실행부
if __name__ == "__main__":
    data = scrape_g_rise_smart()
    
    df = pd.DataFrame(data)
    
    columns_order = ['기업명', '대학명', '대표자', '사업자등록번호', '산업분류', '업종업태', '주소']
    for col in columns_order:
        if col not in df.columns:
            df[col] = ""
    df = df[columns_order]

    if not df.empty:
        # 깃허브 자동화를 위해 엑셀이 아닌 CSV로 저장! 한글 깨짐 방지 인코딩 적용
        file_name = "G_RISE_기업목록.csv"
        df.to_csv(file_name, index=False, encoding="utf-8-sig")
        print(f"\n===== 🎉 수집 완료! =====")
        print(f"총 {len(df)}개의 기업 정보를 깃허브에 저장했습니다.")
        print(f"저장된 파일: {file_name}")
    else:
        print("\n수집된 데이터가 없습니다.")
