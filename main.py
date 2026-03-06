import requests
from bs4 import BeautifulSoup
import pandas as pd
import urllib3
import time
import os

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def scrape_g_rise_all():
    final_results = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    page = 1
    while True:
        url = f"https://www.g-riseon.or.kr/181/FamilyList.do?pageIndex={page}"
        try:
            response = requests.get(url, headers=headers, verify=False)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            company_items = soup.select('div.familyDB > ul.list > li')
            if not company_items:
                break

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
                
            page += 1
            time.sleep(1)

        except Exception as e:
            print(f"Error: {e}")
            break

    return final_results

if __name__ == "__main__":
    data = scrape_g_rise_all()
    df = pd.DataFrame(data)
    
    columns_order = ['기업명', '대학명', '대표자', '사업자등록번호', '산업분류', '업종업태', '주소']
    for col in columns_order:
        if col not in df.columns:
            df[col] = ""
    df = df[columns_order]

    if not df.empty:
        # 깃허브 저장소에 CSV 형식으로 덮어쓰기 저장 (한글 깨짐 방지 utf-8-sig)
        df.to_csv("G_RISE_기업목록.csv", index=False, encoding="utf-8-sig")
