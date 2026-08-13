import streamlit as st
import pandas as pd
import requests
import urllib.parse
import json
import re
import os
import time
import random
import math
from datetime import datetime
import numpy as np
import plotly.graph_objects as go

# ==========================================
# ⚙️ 1. 설정 및 상태 관리
# ==========================================
st.set_page_config(page_title="J-PRO Valuation System", page_icon="🏅", layout="wide")

DB_FILE = "jpro_db.csv"
LEDGER_FILE = "my_car_ledger.csv"
INVENTORY_FILE = "autoplus_inventory.csv" 
COOKIE_FILE = "encar_cookie.txt" 
WEBHOOK_URL = "https://script.google.com/macros/s/AKfycbyyPeTsI9-TK9niAcxw8c21itSzplbzCi0jXLb61fTlcanCEnJmlC9mjwWMOH8yZfbl/exec"

def load_cookie():
    if os.path.exists(COOKIE_FILE):
        with open(COOKIE_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    return ""

def save_cookie(cookie_str):
    with open(COOKIE_FILE, "w", encoding="utf-8") as f:
        f.write(cookie_str)

if 'inventory_data' not in st.session_state:
    if os.path.exists(INVENTORY_FILE):
        try: st.session_state.inventory_data = pd.read_csv(INVENTORY_FILE)
        except: st.session_state.inventory_data = pd.DataFrame()
    else: st.session_state.inventory_data = pd.DataFrame()

if 'scan_data' not in st.session_state: st.session_state.scan_data = pd.DataFrame()
if 'f_status' not in st.session_state: st.session_state.f_status = []
if 'f_brand' not in st.session_state: st.session_state.f_brand = "전체"
if 'f_name' not in st.session_state: st.session_state.f_name = "전체"
if 'f_sub' not in st.session_state: st.session_state.f_sub = "전체"
if 'my_ledger_data' not in st.session_state:
    if os.path.exists(LEDGER_FILE):
        try:
            st.session_state.my_ledger_data = pd.read_csv(LEDGER_FILE)
            st.session_state.my_ledger_data['차량번호'] = st.session_state.my_ledger_data['차량번호'].astype(str)
        except:
            st.session_state.my_ledger_data = pd.DataFrame(columns=['등록일', '차량번호', '제조사', '차량명', '세부모델', '연식', '주행거리', '매입가', '판매가', '특이사항'])
    else:
        st.session_state.my_ledger_data = pd.DataFrame(columns=['등록일', '차량번호', '제조사', '차량명', '세부모델', '연식', '주행거리', '매입가', '판매가', '특이사항'])

if 'option_catalog_cache' not in st.session_state:
    st.session_state.option_catalog_cache = {}

if 'purchase_route' not in st.session_state:
    st.session_state.purchase_route = "셀프(기본)"

# 🔥 입력값 초기화를 위한 세션 상태 세팅
if 'l_car_num' not in st.session_state: st.session_state.l_car_num = ""
if 'l_mil' not in st.session_state: st.session_state.l_mil = 0
if 'l_sell_price' not in st.session_state: st.session_state.l_sell_price = 0
if 'l_ext_repair' not in st.session_state: st.session_state.l_ext_repair = 0
if 'l_manual_fee' not in st.session_state: st.session_state.l_manual_fee = 0
if 'l_memo' not in st.session_state: st.session_state.l_memo = ""
if 'save_success' not in st.session_state: st.session_state.save_success = False
if 'saved_car_num' not in st.session_state: st.session_state.saved_car_num = ""

# ==========================================
# ⚙️ 2. 데이터 처리 엔진 (띄어쓰기 압착 및 매핑 강화)
# ==========================================
class DataProcessor:
    @staticmethod
    def infer_brand(car_name):
        name = str(car_name).strip().upper()
        if any(x in name for x in ['G70', 'G80', 'G90', 'GV70', 'GV80', 'GV60', '제네시스', 'EQ900']): return "제네시스"
        elif any(x in name for x in ['쏘나타', '그랜저', '아반떼', '싼타페', '투싼', '팰리세이드', '캐스퍼', '포터', '스타리아', '스타렉스', '코나', '아이오닉', '베뉴']): return "현대"
        elif any(x in name for x in ['K3', 'K5', 'K7', 'K8', 'K9', '쏘렌토', '스포티지', '카니발', '레이', '모닝', '봉고', '셀토스', '니로', '모하비', 'EV6', 'EV9']): return "기아"
        elif any(x in name for x in ['스파크', '말리부', '트레일블레이저', '트래버스', '콜로라도', '이쿼녹스', '볼트']): return "쉐보레"
        elif any(x in name for x in ['SM3', 'SM5', 'SM6', 'QM3', 'QM6', 'XM3']): return "르노코리아"
        elif any(x in name for x in ['티볼리', '코란도', '렉스턴', '토레스']): return "KG모빌리티"
        elif any(x in name for x in ['E클래스', 'S클래스', 'C클래스', '벤츠', 'GLC', 'GLE', 'GLA', 'GLB', 'AMG']): return "벤츠"
        elif any(x in name for x in ['3시리즈', '5시리즈', '7시리즈', 'BMW', 'X3', 'X4', 'X5', 'X6', 'X7', 'M3', 'M4', 'M5']): return "BMW"
        elif any(x in name for x in ['아우디', 'A4', 'A6', 'A7', 'A8', 'Q5', 'Q7', 'Q8']): return "아우디"
        elif any(x in name for x in ['렉서스', 'ES', 'RX', 'NX', 'LS']): return "렉서스"
        elif any(x in name for x in ['볼보', 'XC60', 'XC90', 'S90']): return "볼보"
        elif any(x in name for x in ['포르쉐', '카이엔', '파나메라', '마칸', '911']): return "포르쉐"
        elif any(x in name for x in ['미니', 'MINI', '클럽맨', '컨트리맨']): return "미니"
        elif any(x in name for x in ['포드', '익스플로러', '머스탱']): return "포드"
        elif any(x in name for x in ['테슬라', '모델3', '모델Y', '모델S', '모델X']): return "테슬라"
        return "기타"

    @staticmethod
    def standardize(df):
        if df.empty: return df
        df = df.copy()
        df = df.loc[:, ~df.columns.duplicated()]
        
        rename_dict = {}
        price_candidates = {"할인적용가": 1, "지점판매가": 2, "판매가": 3, "가격": 4, "매입가": 5}
        best_price_col = None
        best_price_rank = 99
        
        for col in df.columns:
            clean_col = str(col).replace(" ", "").lower()
            
            if "세부모델" in clean_col: rename_dict[col] = "세부모델"
            elif any(x in clean_col for x in ["제조사", "브랜드", "메이커"]): rename_dict[col] = "제조사"
            elif any(x in clean_col for x in ["차종", "차량명", "모델"]): rename_dict[col] = "차량명"
            elif "상태" in clean_col: rename_dict[col] = "상태"
            elif any(x in clean_col for x in ["등록일", "연식"]): rename_dict[col] = "연식"
            elif "주행거리" in clean_col: rename_dict[col] = "주행거리"
            elif any(x in clean_col for x in ["경과일", "재고"]): rename_dict[col] = "재고" 
            elif "성능" in clean_col: rename_dict[col] = "성능일"
            elif any(x in clean_col for x in ["url", "링크", "웹페이지", "사이트", "link"]): rename_dict[col] = "링크"
            
            for cand, rank in price_candidates.items():
                if cand in clean_col and rank < best_price_rank:
                    best_price_col = col
                    best_price_rank = rank
                    
        if best_price_col:
            rename_dict[best_price_col] = "판매가"

        df = df.rename(columns=rename_dict)
        df = df.loc[:, ~df.columns.duplicated()]
        
        if "차량명" in df.columns:
            df["차량명"] = df["차량명"].astype(str).str.replace(" ", "", regex=False)
        if "세부모델" in df.columns:
            df["세부모델"] = df["세부모델"].astype(str).str.replace(" ", "", regex=False)
            
        if "제조사" not in df.columns: df["제조사"] = ""
        if "차량명" in df.columns:
            df["제조사"] = df.apply(lambda row: DataProcessor.infer_brand(row["차량명"]) if pd.isna(row["제조사"]) or str(row["제조사"]).strip() == "" else row["제조사"], axis=1)
        
        if "_carid" not in df.columns: df["_carid"] = ""
        df["_carid"] = df["_carid"].astype(str)
        
        target_columns = ['상태', '성능일', '제조사', '차량명', '세부모델', '연식', '주행거리', '판매가', '재고', '사고유무', '추가옵션', '링크', '_carid']
        for col in target_columns:
            if col not in df.columns:
                if col in ['사고유무', '추가옵션', '성능일', '재고']: df[col] = "-"
                elif col == '상태': df[col] = "자사재고"
                else: df[col] = ""
                
        df["상태"] = df["상태"].fillna("자사재고").replace("", "자사재고")
                
        ordered_df = df[target_columns].copy()

        if "링크" in ordered_df.columns:
            def fix_url(url):
                u = str(url).strip()
                if not u or u.lower() in ["nan", "-", "none", ""] or "javascript" in u.lower(): return None
                if not u.startswith("http"): return f"https://{u}"
                return u
            ordered_df["링크"] = ordered_df["링크"].apply(fix_url)

        if "연식" in ordered_df.columns:
            def format_year(y):
                y = str(y).strip()
                if len(y) >= 7 and y[4] == '-': return y[2:7] 
                if len(y) == 6 and y.isdigit(): return f"{y[2:4]}-{y[4:6]}" 
                if len(y) == 4 and y.isdigit(): return y[2:4] 
                return y
            ordered_df["연식"] = ordered_df["연식"].apply(format_year)
            
        if "주행거리" in ordered_df.columns:
            ordered_df["주행거리"] = ordered_df["주행거리"].astype(str).str.replace(r'[^\d.]', '', regex=True)
            ordered_df["주행거리"] = pd.to_numeric(ordered_df["주행거리"], errors='coerce')
        
        if "판매가" in ordered_df.columns:
            ordered_df["판매가"] = ordered_df["판매가"].astype(str).str.replace(r'[^\d.]', '', regex=True)
            ordered_df["판매가"] = pd.to_numeric(ordered_df["판매가"], errors='coerce')
            ordered_df["판매가"] = ordered_df["판매가"].apply(lambda x: x / 10000 if pd.notna(x) and x >= 100000 else x)
            
            valid_prices = ordered_df["판매가"].dropna()
            if len(valid_prices) > 10:
                low_bound = valid_prices.quantile(0.01)
                high_bound = valid_prices.quantile(0.99)
                ordered_df = ordered_df[(ordered_df["판매가"].isna()) | ((ordered_df["판매가"] >= low_bound) & (ordered_df["판매가"] <= high_bound))]

        if "재고" in ordered_df.columns:
            def format_inv(v):
                v_str = str(v).strip()
                if v_str.lower() in ['nan', 'none', '', '-']: return "-"
                try: return str(int(float(v_str)))
                except: return v_str
            ordered_df["재고"] = ordered_df["재고"].apply(format_inv)

        ordered_df = ordered_df.fillna("")
        if "링크" in ordered_df.columns:
            ordered_df["링크"] = ordered_df["링크"].replace("", None)
            
        return ordered_df

# ==========================================
# ⚙️ 3. 초정밀 데이터 스크래퍼 엔진
# ==========================================
class Scraper:
    @staticmethod
    def calculate_inventory_days(date_str):
        try:
            full_date_str = f"20{date_str}" 
            delta = datetime.now() - datetime.strptime(full_date_str, "%Y-%m-%d")
            return str(delta.days)
        except: return "-"

    @staticmethod
    def _fetch_json(session, url, ref_id):
        headers = {"Referer": f"https://fem.encar.com/cars/detail/{ref_id}"}
        try:
            res = session.get(url, headers=headers, timeout=5)
            json_data = None
            if res.status_code == 200:
                try: json_data = res.json()
                except: pass
            return {"status": res.status_code, "json": json_data}
        except Exception:
            return {"status": "error", "json": None}

    @staticmethod
    def clean_option_name(name):
        return re.sub(r'\([^)]*\)|\[[^\]]*\]', '', str(name)).strip()

    @staticmethod
    def fetch_car_detail(session, c_id):
        perf_date = "⚠️미등록"
        inv_days = "-"
        accident_status = "⚠️정보없음"
        opt_str = "없음"
        is_rate_limited = False

        v_resp = Scraper._fetch_json(session, f"https://api.encar.com/v1/readside/vehicle/{c_id}?include=MANAGE,OPTIONS", c_id)
        if v_resp["status"] in [403, 429]: return {"성능일": "⚠️조회실패", "재고": "-", "사고유무": "⚠️조회실패", "추가옵션": "⚠️조회실패", "is_rate_limited": True}
        
        real_id = str(c_id)
        applied_codes = []
        
        if v_resp["status"] == 200 and v_resp["json"]:
            manage = v_resp["json"].get("manage") or {}
            if manage.get("dummy"):
                real_id = str(manage.get("dummyVehicleId", c_id))
            applied_codes = v_resp["json"].get("options", {}).get("choice", [])

        i_resp = Scraper._fetch_json(session, f"https://api.encar.com/v1/readside/inspection/vehicle/{real_id}", c_id)
        if i_resp["status"] in [403, 429]: return {"성능일": "⚠️조회실패", "재고": "-", "사고유무": "⚠️조회실패", "추가옵션": "⚠️조회실패", "is_rate_limited": True}
        
        if i_resp["status"] == 200 and i_resp["json"]:
            master = i_resp["json"].get("master") or {}
            detail = master.get("detail") or {}

            issue_date = detail.get("issueDate", "")
            if issue_date and len(issue_date) == 8:
                perf_date = f"{issue_date[2:4]}-{issue_date[4:6]}-{issue_date[6:8]}"
                inv_days = Scraper.calculate_inventory_days(perf_date)

            acc = master.get("accdient")
            rep = master.get("simpleRepair")

            if acc is False and rep is False:
                accident_status = "✅ 완전무사고"
            elif acc is None and rep is None:
                accident_status = "⚠️정보없음"
            else:
                flags = []
                if acc: flags.append("사고")
                if rep: flags.append("판금")
                accident_status = f"⚠️ ({'/'.join(flags)})"
        elif i_resp["status"] == 404:
            perf_date = "미검사/사진"
            accident_status = "기록부(사진)"

        exch_cnt = 0
        sheet_cnt = 0
        d_resp = Scraper._fetch_json(session, f"https://api.encar.com/v1/readside/diagnosis/vehicle/{real_id}", c_id)
        if d_resp["status"] == 200 and d_resp["json"]:
            items = d_resp["json"].get("items", [])
            for item in items:
                r_code = str(item.get("resultCode", ""))
                if r_code == "EXCHANGE": exch_cnt += 1
                elif r_code in ["SHEET_METAL", "REPAIR", "WELDING"]: sheet_cnt += 1
                    
        if exch_cnt > 0 or sheet_cnt > 0:
            if "기록부(사진)" not in accident_status:
                accident_status += f" [교환:{exch_cnt} / 판금:{sheet_cnt}]"

        if applied_codes:
            if c_id not in st.session_state.option_catalog_cache:
                o_resp = Scraper._fetch_json(session, f"https://api.encar.com/v1/readside/vehicles/car/{c_id}/options/choice", c_id)
                if o_resp["status"] == 200 and o_resp["json"]:
                    st.session_state.option_catalog_cache[c_id] = o_resp["json"]
                elif o_resp["status"] == 404:
                    opt_str = "없음(구버전점검)" 
                elif o_resp["status"] in [403, 429]:
                    opt_str = "⚠️조회실패"
                    is_rate_limited = True
                elif o_resp["status"] != 200:
                    opt_str = "코드매칭실패"

            if opt_str == "없음": 
                catalog = st.session_state.option_catalog_cache.get(c_id, [])
                if isinstance(catalog, list) and catalog:
                    applied_opts = []
                    for opt in catalog:
                        if isinstance(opt, dict) and str(opt.get("optionCd", "")) in applied_codes:
                            name = Scraper.clean_option_name(opt.get("optionName", ""))
                            price = opt.get("price", 0)
                            if name and "외장컬러" not in name:
                                if price > 0: applied_opts.append(f"{name}({price}만)")
                                else: applied_opts.append(name)
                    if applied_opts:
                        opt_str = " / ".join(applied_opts)

        return {
            "성능일": perf_date,
            "재고": inv_days,
            "사고유무": accident_status,
            "추가옵션": opt_str,
            "is_rate_limited": is_rate_limited
        }

    @staticmethod
    def dedupe_after_scan(df):
        if df.empty: return df
        df_copy = df.copy()
        
        def calculate_score(row):
            score = 0
            if str(row.get('성능일', '')) not in ['⚠️미등록', '미검사/사진', '⚠️조회실패', '-']: score += 1
            if str(row.get('사고유무', '')) not in ['⚠️정보없음', '기록부(사진)', '⚠️조회실패', '-']: score += 1
            if str(row.get('추가옵션', '')) not in ['⚠️조회실패', '코드매칭실패', '없음(구버전점검)', '-']: score += 1
            return score

        df_copy['data_score'] = df_copy.apply(calculate_score, axis=1)
        deduped = df_copy.sort_values('data_score', ascending=False).drop_duplicates(
            subset=['차량명', '세부모델', '연식', '주행거리', '판매가'], keep='first'
        )
        deduped = deduped.drop(columns=['data_score']).reset_index(drop=True)
        return deduped

    @staticmethod
    def run(target_url, custom_cookie, progress_bar, status_text):
        try:
            status_text.text("1/3: 실시간 통신 준비...")
            progress_bar.progress(10)
            
            decoded_url = urllib.parse.unquote_plus(target_url.strip())
            condition = ""
            json_match = re.search(r'#!(\{.*\})', decoded_url)
            if json_match:
                try: condition = json.loads(json_match.group(1)).get("action", "")
                except: pass
                    
            if not condition:
                match = re.search(r'"action"\s*:\s*"([^"]+)"', decoded_url)
                if match: condition = match.group(1).encode('ascii', 'backslashreplace').decode('unicode_escape') if r'\u' in match.group(1) else match.group(1)
                elif 'q=' in decoded_url: 
                    try: condition = decoded_url.split('q=')[1].split('&')[0]
                    except: pass

            if not condition: return pd.DataFrame(), "❌ URL 검색 조건 누락"
                
            safe_condition = urllib.parse.quote(condition)
            api_url = f"https://api.encar.com/search/car/list/general?count=false&q={safe_condition}&sr=%7CModifiedDate%7C0%7C100"
            
            session = requests.Session()
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
                "Origin": "https://fem.encar.com",
            }
            if custom_cookie: headers["Cookie"] = custom_cookie
            session.headers.update(headers)

            cars_res = session.get(api_url).json()
            cars = cars_res.get("SearchResults", [])
            if not cars: return pd.DataFrame(), "❌ 매물 없음"

            car_data_list = []
            for car in cars:
                if car.get("Price", 0) <= 0: continue
                
                sell_type = str(car.get("SellType", ""))
                if "렌트" in sell_type or "리스" in sell_type: continue
                if car.get("LeaseType"): continue 
                
                badge_group = car.get('BadgeGroup', '')
                badge = car.get('Badge', '')
                badge_detail = car.get('BadgeDetail', '')
                
                parts = []
                if badge_group: parts.append(badge_group)
                if badge and badge not in parts: parts.append(badge)
                if badge_detail and badge_detail not in parts: parts.append(badge_detail)
                
                sub_model_full = " ".join(parts).strip()

                car_data_list.append({
                    "상태": "실시간", "제조사": car.get('Manufacturer', '').strip(),
                    "차량명": car.get('Model', '').strip(), "세부모델": sub_model_full, 
                    "연식": str(car.get("FormYear", "")), "주행거리": car.get("Mileage", 0),
                    "판매가": car.get("Price", 0), "성능일": "-", "재고": "-",
                    "사고유무": "-", "추가옵션": "-",
                    "링크": f"http://www.encar.com/dc/dc_cardetailview.do?carid={car.get('Id', '')}",
                    "_carid": str(car.get('Id', ''))
                })
            
            total_cars = len(car_data_list)
            consecutive_failures = 0
            
            for idx, car in enumerate(car_data_list):
                status_text.text(f"2/3: 쾌속 정밀 스캔 중... ({idx+1}/{total_cars}대)")
                progress_bar.progress(10 + int(80 * (idx + 1) / total_cars))
                
                res = Scraper.fetch_car_detail(session, car["_carid"])
                
                car["성능일"] = res["성능일"]
                car["재고"] = res["재고"]
                car["사고유무"] = res["사고유무"]
                car["추가옵션"] = res["추가옵션"]

                if res.get("is_rate_limited"):
                    consecutive_failures += 1
                    if consecutive_failures >= 5:
                        status_text.text("⚠️ 엔카 방어막 감지! 15초간 보안 대기합니다...")
                        time.sleep(15.0)
                        consecutive_failures = 0
                else:
                    consecutive_failures = 0
                    
                # 🔥 울트라 터보 모드 (0.01초 ~ 0.05초)
                time.sleep(random.uniform(0.01, 0.05))

            status_text.text("3/3: 스캔 완료. 스마트 데이터 취합 중...")
            raw_df = pd.DataFrame(car_data_list)
            deduped_df = Scraper.dedupe_after_scan(raw_df)

            progress_bar.progress(100)
            status_text.text("✅ 스캔 및 최적화 완전 성공!")
            return DataProcessor.standardize(deduped_df), "success"
        except Exception as e:
            return pd.DataFrame(), f"❌ 에러: {str(e)}"

    @staticmethod
    def rescan(failed_indices, custom_cookie, progress_bar, status_text):
        session = requests.Session()
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
            "Origin": "https://fem.encar.com",
        }
        if custom_cookie: headers["Cookie"] = custom_cookie
        session.headers.update(headers)
        
        consecutive_failures = 0
        total_cars = len(failed_indices)
        
        for i, idx in enumerate(failed_indices):
            status_text.text(f"♻️ 실패 매물 원터치 재스캔... ({i+1}/{total_cars}대)")
            progress_bar.progress(int(100 * (i + 1) / total_cars))
            
            # 🔥 재스캔도 울트라 터보
            time.sleep(random.uniform(0.05, 0.1)) 
            
            c_id = st.session_state.scan_data.loc[idx, '_carid']
            res = Scraper.fetch_car_detail(session, c_id)
            
            st.session_state.scan_data.loc[idx, '성능일'] = res["성능일"]
            st.session_state.scan_data.loc[idx, '재고'] = res["재고"]
            st.session_state.scan_data.loc[idx, '사고유무'] = res["사고유무"]
            st.session_state.scan_data.loc[idx, '추가옵션'] = res["추가옵션"]
            
            if res.get("is_rate_limited"):
                consecutive_failures += 1
                if consecutive_failures >= 5:
                    status_text.text("⚠️ 보안 대기 중 (15초)...")
                    time.sleep(15.0)
                    consecutive_failures = 0
            else:
                consecutive_failures = 0
                
        status_text.text("✅ 재스캔 완료!")

# ==========================================
# ⚙️ 4. 사이드바 UI 및 메인 리스트 출력
# ==========================================
st.sidebar.markdown("### 📥 데이터 스캔")

uploaded_files = st.sidebar.file_uploader("자사 재고 엑셀 업로드", type=['xlsx', 'xls', 'csv'], accept_multiple_files=True, label_visibility="collapsed")
if st.sidebar.button("📁 엑셀 병합 및 DB 저장", use_container_width=True):
    if uploaded_files:
        new_dfs = []
        for uf in uploaded_files:
            try: new_dfs.append(pd.read_excel(uf) if uf.name.endswith(('xls', 'xlsx')) else pd.read_csv(uf))
            except: pass
        if new_dfs:
            merged_df = DataProcessor.standardize(pd.concat(new_dfs, ignore_index=True))
            if not st.session_state.inventory_data.empty:
                st.session_state.inventory_data = pd.concat([st.session_state.inventory_data, merged_df]).drop_duplicates(subset=['제조사', '차량명', '세부모델', '연식', '주행거리', '판매가'], keep='last')
            else:
                st.session_state.inventory_data = merged_df
            st.session_state.inventory_data.to_csv(INVENTORY_FILE, index=False, encoding='utf-8-sig')
            
            st.rerun()

if st.sidebar.button("🗑️ 저장된 엑셀 DB 지우기", use_container_width=True):
    st.session_state.inventory_data = pd.DataFrame()
    if os.path.exists(INVENTORY_FILE): os.remove(INVENTORY_FILE)
    st.rerun()

scan_url = st.sidebar.text_input("엔카 정밀 스캔 URL 입력:", label_visibility="collapsed", placeholder="엔카 URL 붙여넣기")

saved_cookie = load_cookie()
custom_cookie = st.sidebar.text_input("🔑 엔카 쿠키", type="password", value=saved_cookie, placeholder="로그인 Cookie 값 붙여넣기")

if st.sidebar.button("💾 쿠키 영구 저장해두기", use_container_width=True):
    save_cookie(custom_cookie)
    st.sidebar.success("✅ 쿠키가 안전하게 저장되었습니다!")

if st.sidebar.button("🚀 실시간 엔카 스캔", use_container_width=True):
    if scan_url:
        p_bar, s_text = st.sidebar.progress(0), st.sidebar.empty()
        new_scan_df, msg = Scraper.run(scan_url, custom_cookie, p_bar, s_text)
        if msg == "success":
            st.session_state.scan_data = pd.concat([st.session_state.scan_data, new_scan_df], ignore_index=True)
            st.session_state.scan_data = st.session_state.scan_data.drop_duplicates(subset=['_carid'], keep='last').reset_index(drop=True)
            
            if not new_scan_df.empty:
                st.session_state.f_brand = new_scan_df['제조사'].iloc[0] if '제조사' in new_scan_df.columns else "전체"
                st.session_state.f_name = new_scan_df['차량명'].iloc[0]
                st.session_state.f_sub = new_scan_df['세부모델'].iloc[0]
                st.session_state.f_status = [] 
            st.rerun()
        else: s_text.error(msg)
        
if st.sidebar.button("🔄 스캔 초기화", use_container_width=True): 
    st.session_state.scan_data = pd.DataFrame()
    st.session_state.f_brand = "전체"
    st.session_state.f_name = "전체"
    st.session_state.f_sub = "전체"
    st.session_state.f_status = []
    st.rerun()

if not st.session_state.scan_data.empty:
    failed_mask = st.session_state.scan_data['성능일'].astype(str).str.contains("조회실패") | \
                  st.session_state.scan_data['사고유무'].astype(str).str.contains("조회실패") | \
                  st.session_state.scan_data['추가옵션'].astype(str).str.contains("조회실패")
    failed_count = failed_mask.sum()
    
    if failed_count > 0:
        st.markdown("---")
        st.warning(f"⚠️ 조회실패 차량: {failed_count}대")
        if st.sidebar.button("♻️ 실패 차량만 재스캔", use_container_width=True):
            p_bar, s_text = st.sidebar.progress(0), st.sidebar.empty()
            failed_indices = st.session_state.scan_data[failed_mask].index
            Scraper.rescan(failed_indices, custom_cookie, p_bar, s_text)
            st.rerun()

st.sidebar.markdown("---")

st.sidebar.markdown("### 🔍 상세 검색 필터")

combined_df = pd.concat([st.session_state.inventory_data, st.session_state.scan_data], ignore_index=True)
combined_df = DataProcessor.standardize(combined_df)

filtered_df = combined_df.copy()

current_f_year = ""
current_f_mil = 0

if not filtered_df.empty:
    status_options = list(filtered_df['상태'].unique()) if '상태' in filtered_df.columns else []
    if not st.session_state.f_status:
        st.session_state.f_status = status_options
        
    st.session_state.f_status = st.sidebar.multiselect(
        "데이터 출처 / 판매상태", 
        options=status_options, 
        default=st.session_state.f_status
    )
    
    if st.session_state.f_status and '상태' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['상태'].isin(st.session_state.f_status)]
    else:
        filtered_df = pd.DataFrame(columns=filtered_df.columns)
    
    if not filtered_df.empty:
        f_brand_opts = ["전체"] + list(filtered_df['제조사'].dropna().unique())
        if st.session_state.f_brand not in f_brand_opts: st.session_state.f_brand = "전체"
        st.session_state.f_brand = st.sidebar.selectbox("제조사/브랜드", f_brand_opts, index=f_brand_opts.index(st.session_state.f_brand))
        if st.session_state.f_brand != "전체": 
            filtered_df = filtered_df[filtered_df['제조사'] == st.session_state.f_brand]

        def get_smart_sort_key(name):
            name_str = str(name)
            core_models = ['그랜저', '싼타페', '아반떼', '쏘나타', '투싼', '팰리세이드', '스타리아', '스타렉스',
                           'K3', 'K5', 'K7', 'K8', 'K9', '쏘렌토', '스포티지', '카니발', '모닝', '레이',
                           '제네시스', 'G70', 'G80', 'G90', 'GV70', 'GV80', 'GV60',
                           '스파크', '말리부', '트레일블레이저', 'SM3', 'SM5', 'SM6', 'QM3', 'QM6', 'XM3',
                           '티볼리', '코란도', '렉스턴', '토레스', 'E클래스', 'S클래스', 'C클래스', '5시리즈', '3시리즈', '7시리즈']
            for core in core_models:
                if core in name_str: return f"{core}_{name_str}"
            return name_str

        raw_names = list(filtered_df['차량명'].dropna().unique())
        sorted_names = sorted(raw_names, key=get_smart_sort_key)
        f_name_opts = ["전체"] + sorted_names
        
        if st.session_state.f_name not in f_name_opts: st.session_state.f_name = "전체"
        st.session_state.f_name = st.sidebar.selectbox("차량명", f_name_opts, index=f_name_opts.index(st.session_state.f_name))
        if st.session_state.f_name != "전체": 
            filtered_df = filtered_df[filtered_df['차량명'] == st.session_state.f_name]
        
        f_sub_opts = ["전체"] + list(filtered_df['세부모델'].dropna().unique())
        if st.session_state.f_sub not in f_sub_opts: st.session_state.f_sub = "전체"
        st.session_state.f_sub = st.sidebar.selectbox("세부모델", f_sub_opts, index=f_sub_opts.index(st.session_state.f_sub))
        if st.session_state.f_sub != "전체": 
            filtered_df = filtered_df[filtered_df['세부모델'] == st.session_state.f_sub]
        
        current_f_year = st.sidebar.text_input("연식 검색 (예: 24-05)")
        if current_f_year: filtered_df = filtered_df[filtered_df['연식'].astype(str).str.contains(current_f_year)]
        
        if "주행거리" in filtered_df.columns:
            filtered_df["주행거리"] = pd.to_numeric(filtered_df["주행거리"], errors='coerce').fillna(0)
            max_mil = int(filtered_df["주행거리"].max()) if not filtered_df.empty else 0
            if max_mil > 0:
                current_f_mil = st.sidebar.slider("📈 시세분석용 주행거리 이하 (km)", 0, max_mil, max_mil, step=1000)

        if "재고" in filtered_df.columns:
            filtered_df['_sort_inv'] = pd.to_numeric(filtered_df['재고'], errors='coerce').fillna(99999)
            filtered_df = filtered_df.sort_values(by='_sort_inv', ascending=True).drop(columns=['_sort_inv']).reset_index(drop=True)

st.sidebar.markdown("---")

# ==========================================
# 📝 실시간 장부 자동 계산기 (리얼타임 반응형)
# ==========================================
st.sidebar.markdown("### 📝 장부 간편 저장 (자동 계산)")

if st.session_state.save_success:
    st.sidebar.success(f"✅ {st.session_state.saved_car_num} 장부 및 구글시트 저장 완료!")
    st.session_state.save_success = False

l_car_num = st.sidebar.text_input("차량번호 (필수)", key="l_car_num")
l_mil = st.sidebar.number_input("주행거리 (km)", min_value=0, step=1000, key="l_mil")

st.sidebar.markdown("---")

l_sell_price = st.sidebar.number_input("판매가 (예상, 만원)", min_value=0, step=10, key="l_sell_price")
l_ext_repair = st.sidebar.number_input("외판 수리 갯수", min_value=0, step=1, format="%d", key="l_ext_repair")

route_options = ["셀프(기본)", "제로", "개인"]
def update_route():
    st.session_state.purchase_route = st.session_state._route_selector

l_route = st.sidebar.radio("매입 경로", route_options, index=route_options.index(st.session_state.purchase_route), key="_route_selector", on_change=update_route)

l_manual_fee = 0
if l_route == "개인":
    l_manual_fee = st.sidebar.number_input("매입 수수료 (직접입력, 만원)", min_value=0, step=1, key="l_manual_fee")

l_margin = st.sidebar.number_input("목표 마진 (만원)", min_value=0, step=10, value=120)

name_val = st.session_state.f_name if st.session_state.f_name != "전체" else ""
is_light_car = any(x in name_val for x in ["모닝", "레이", "스파크", "마티즈", "캐스퍼", "티코"])

selling_fee = l_sell_price * 0.007
misc_cost = 15
ext_cost = l_ext_repair * 13

first_target = l_sell_price - selling_fee - misc_cost - ext_cost - l_margin
purchase_fee = 0

if l_route == "셀프(기본)":
    if first_target <= 100: purchase_fee = 7.5
    elif first_target <= 500: purchase_fee = 18.5
    elif first_target <= 1000: purchase_fee = 19.0 if is_light_car else 24.5
    elif first_target <= 3000: purchase_fee = 25.0
    else: purchase_fee = 36.0
elif l_route == "제로":
    if first_target <= 100: purchase_fee = 14.0
    elif first_target <= 500: purchase_fee = 30.0
    elif first_target <= 1000: purchase_fee = 30.5 if is_light_car else 36.5
    elif first_target <= 1500: purchase_fee = 36.5
    elif first_target <= 3000: purchase_fee = 39.5
    elif first_target <= 4000: purchase_fee = 47.5
    else: purchase_fee = 50.5
elif l_route == "개인":
    purchase_fee = l_manual_fee

final_target_raw = first_target - purchase_fee
final_target = int(math.floor(final_target_raw))

st.sidebar.markdown("---")
if st.session_state.l_sell_price > 0:
    html_content = f"""
    <div style="background-color: #d1e7dd; border: 1px solid #badbcc; padding: 15px; border-radius: 8px; color: #0f5132; margin-bottom: 15px;">
        <div style="font-size: 1.1em; font-weight: bold; margin-bottom: 5px;">✅ 권장 입찰가(매입가)</div>
        <div style="font-size: 2.3em; font-weight: 900; text-align: right; margin-bottom: 15px; color: #0a3622;">
            {final_target:,} <span style="font-size: 0.6em; font-weight: normal;">만원</span>
        </div>
        <div style="font-size: 0.9em; text-align: right; color: #146c43;">
            (수수료: {purchase_fee:g}만 / 수리비: {ext_cost:g}만)
        </div>
    </div>
    """
    st.sidebar.markdown(html_content, unsafe_allow_html=True)
else:
    st.sidebar.info("💡 판매가를 입력하시면 매입가가 자동 계산됩니다.")

l_memo = st.sidebar.text_area("특이사항 / 메모", height=80, key="l_memo")

if st.sidebar.button("💾 내 장부 및 구글시트에 저장", use_container_width=True):
    if not st.session_state.l_car_num:
        st.sidebar.error("⚠️ 차량번호 필수")
    else:
        brand_val = st.session_state.f_brand if st.session_state.f_brand != "전체" else ""
        sub_val = st.session_state.f_sub if st.session_state.f_sub != "전체" else ""
        year_val = current_f_year if current_f_year else ""

        new_record = {
            '등록일': datetime.now().strftime("%y-%m-%d"), 
            '차량번호': st.session_state.l_car_num, 
            '제조사': brand_val,
            '차량명': name_val,
            '세부모델': sub_val,
            '연식': year_val,
            '주행거리': f"{st.session_state.l_mil} km" if st.session_state.l_mil > 0 else "", 
            '매입가': final_target, 
            '판매가': st.session_state.l_sell_price, 
            '특이사항': f"[{st.session_state.purchase_route}] " + st.session_state.l_memo
        }
        st.session_state.my_ledger_data = pd.concat([st.session_state.my_ledger_data, pd.DataFrame([new_record])], ignore_index=True)
        st.session_state.my_ledger_data.to_csv(LEDGER_FILE, index=False, encoding='utf-8-sig')
        
        try:
            requests.post(WEBHOOK_URL, json=new_record, timeout=5)
        except: pass

        st.session_state.save_success = True
        st.session_state.saved_car_num = st.session_state.l_car_num
        
        st.session_state.l_car_num = ""
        st.session_state.l_mil = 0
        st.session_state.l_sell_price = 0
        st.session_state.l_ext_repair = 0
        if 'l_manual_fee' in st.session_state:
            st.session_state.l_manual_fee = 0
        st.session_state.l_memo = ""
        
        st.rerun()

st.markdown("##### 🏅 J-PRO : Advanced Auto Valuation System")

tab_scan, tab_ledger = st.tabs(["📊 시세 스캔 리스트", "📋 내 실전 장부 리스트"])

with tab_scan:
    if not filtered_df.empty:
        col_table, col_detail = st.columns([7, 3])

        with col_table:
            display_df = filtered_df.copy()

            def summarize_options(opt_str):
                if not opt_str or opt_str in ("없음", "-", "없음(구버전점검)", "⚠️조회실패", "코드매칭실패"):
                    return opt_str
                items = [o.strip() for o in str(opt_str).split(" / ") if o.strip()]
                return f"{len(items)}개 옵션"

            display_df["추가옵션_요약"] = display_df["추가옵션"].apply(summarize_options)

            try:
                styled_df = display_df.style.set_properties(
                    subset=[c for c in ['주행거리', '판매가'] if c in display_df.columns],
                    **{'font-size': '1.1em', 'font-weight': 'bold'}
                ).format(precision=0)

                event = st.dataframe(
                    styled_df,
                    column_config={
                        "상태": st.column_config.TextColumn("상태", width=70),
                        "성능일": st.column_config.TextColumn("성능일", width=70),
                        "제조사": st.column_config.TextColumn("제조사", width=50),
                        "차량명": st.column_config.TextColumn("차량명", width=110),
                        "세부모델": st.column_config.TextColumn("세부모델", width=140),
                        "연식": st.column_config.TextColumn("연식", width=50),
                        "주행거리": st.column_config.NumberColumn("주행거리", format="%d km"), 
                        "판매가": st.column_config.NumberColumn("판매가", format="%d 만", width=60),
                        "재고": st.column_config.TextColumn("재고", width=50),
                        "사고유무": st.column_config.TextColumn("사고유무", width=180),
                        "추가옵션": None,
                        "추가옵션_요약": st.column_config.TextColumn("옵션", width=80),
                        "링크": st.column_config.LinkColumn("링크", display_text="보기", width=40),
                        "_carid": None
                    },
                    use_container_width=True,
                    height=750,  
                    hide_index=True,
                    on_select="rerun",
                    selection_mode="single-row",
                )
            except Exception as e:
                event = st.dataframe(display_df, use_container_width=True, height=750, hide_index=True)

        with col_detail:
            st.markdown("### 🚘 상세 스펙 및 옵션")
            selected_rows = event.selection.rows if hasattr(event, "selection") else []
            
            if selected_rows:
                sel_idx = selected_rows[0]
                row = filtered_df.iloc[sel_idx]

                st.info(f"**{row['차량명']} {row['세부모델']} ({row['연식']})**")
                
                def format_num(val):
                    try: 
                        if pd.isna(val) or str(val).strip() == "": return "-"
                        return f"{int(float(val)):,}"
                    except: return val
                
                col1, col2 = st.columns(2)
                col1.metric("판매가", f"{format_num(row['판매가'])} 만원")
                col2.metric("주행거리", f"{format_num(row['주행거리'])} km")
                
                st.metric("성능점검일", row['성능일'])

                st.markdown("---")
                st.markdown(f"**🛡️ 사고유무:**\n{row['사고유무']}")
                
                st.markdown("---")
                st.markdown("**✨ 추가옵션 전체 목록**")
                opt_items = [o.strip() for o in str(row['추가옵션']).split(" / ") if o.strip()]
                if opt_items and opt_items != [row['추가옵션']]:
                    for item in opt_items:
                        st.markdown(f"- {item}")
                else:
                    st.markdown(row['추가옵션'])
            else:
                st.success("👈 좌측 표에서 차량을 클릭하시면\n상세 정보가 여기에 표시됩니다.")

        st.markdown("---")
        st.markdown("### 📊 현재 조건 시세 분석")
        
        chart_base = filtered_df.copy()
        if current_f_mil > 0:
            chart_base = chart_base[chart_base['주행거리'] <= current_f_mil]
        
        valid_prices = pd.to_numeric(chart_base['판매가'], errors='coerce').dropna()
        
        if not valid_prices.empty:
            min_price = valid_prices.min()
            max_price = valid_prices.max()
            avg_price = valid_prices.mean()
            
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("분석 대상 매물 수", f"{len(chart_base)} 대")
            c2.metric("최저가", f"{int(min_price):,} 만원")
            c3.metric("최고가", f"{int(max_price):,} 만원")
            c4.metric("평균가", f"{int(avg_price):,} 만원")
            
            chart_base['주행거리_num'] = pd.to_numeric(chart_base['주행거리'], errors='coerce')
            chart_base['판매가_num'] = pd.to_numeric(chart_base['판매가'], errors='coerce')
            chart_df = chart_base.dropna(subset=['주행거리_num', '판매가_num'])
            
            if not chart_df.empty:
                fig = go.Figure()

                def get_color(acc):
                    acc_str = str(acc)
                    if "완전무사고" in acc_str: return '#2CA02C' 
                    elif "사고" in acc_str and "완전무사고" not in acc_str: return '#D62728' 
                    elif "판금" in acc_str or "교환" in acc_str: return '#FF7F0E' 
                    else: return '#7F7F7F'

                def get_symbol(stat):
                    stat_str = str(stat)
                    if stat_str == "실시간": return 'circle'
                    else: return 'diamond'

                colors = chart_df['사고유무'].apply(get_color).tolist()
                symbols = chart_df['상태'].apply(get_symbol).tolist()

                hover_text = [
                    f"출처: {row['상태']}<br>{row['연식']}년식 · 성능일 {row['성능일']}<br>{row['사고유무']}"
                    for _, row in chart_df.iterrows()
                ]

                fig.add_trace(go.Scatter(
                    x=chart_df['주행거리_num'],
                    y=chart_df['판매가_num'],
                    mode='markers',
                    marker=dict(size=10, color=colors, symbol=symbols, opacity=0.8, line=dict(width=1, color='white')),
                    text=hover_text,
                    hovertemplate="주행거리: %{x:,.0f}km<br>판매가: %{y:,.0f}만원<br>%{text}<extra></extra>",
                    name="매물"
                ))

                if len(chart_df) >= 2:
                    try:
                        z = np.polyfit(chart_df['주행거리_num'], chart_df['판매가_num'], 1)
                        x_trend = np.linspace(chart_df['주행거리_num'].min(), chart_df['주행거리_num'].max(), 50)
                        y_trend = np.polyval(z, x_trend)
                        fig.add_trace(go.Scatter(
                            x=x_trend, y=y_trend,
                            mode='lines',
                            line=dict(color='gray', dash='dash', width=1.5),
                            name='추세선',
                            hoverinfo='skip'
                        ))
                    except: pass

                selected_rows_for_chart = event.selection.rows if hasattr(event, "selection") else []
                if selected_rows_for_chart:
                    sel_row = filtered_df.iloc[selected_rows_for_chart[0]]
                    sel_km = pd.to_numeric(sel_row['주행거리'], errors='coerce')
                    sel_price = pd.to_numeric(sel_row['판매가'], errors='coerce')
                    if pd.notna(sel_km) and pd.notna(sel_price) and (current_f_mil == 0 or sel_km <= current_f_mil):
                        fig.add_trace(go.Scatter(
                            x=[sel_km], y=[sel_price],
                            mode='markers',
                            marker=dict(size=22, color='red', symbol='star', line=dict(width=2, color='darkred')),
                            name='⭐ 선택한 차량',
                            hovertemplate=f"⭐ 선택한 차량<br>주행거리: {sel_km:,.0f}km<br>판매가: {sel_price:,.0f}만원<extra></extra>"
                        ))

                x_min, x_max = chart_df['주행거리_num'].min(), chart_df['주행거리_num'].max()
                y_min, y_max = chart_df['판매가_num'].min(), chart_df['판매가_num'].max()
                x_pad = max((x_max - x_min) * 0.08, 500)
                y_pad = max((y_max - y_min) * 0.08, 20)

                fig.update_layout(
                    xaxis_title='주행거리 (km)',
                    yaxis_title='판매가 (만원)',
                    xaxis=dict(range=[x_min - x_pad, x_max + x_pad]),
                    yaxis=dict(range=[y_min - y_pad, y_max + y_pad]),
                    height=450,
                    margin=dict(l=10, r=10, t=40, b=10),
                    legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
                    hovermode='closest',
                )

                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("유효한 주행거리/판매가 데이터가 없어 차트를 그릴 수 없습니다.")
        else:
            st.info("현재 설정된 주행거리 기준에 맞는 매물이 없습니다.")

    else:
        st.info("👈 좌측 메뉴에서 엑셀을 업로드하거나 엔카 URL을 스캔하여 데이터를 불러와 주세요.")

with tab_ledger:
    if not st.session_state.my_ledger_data.empty:
        st.dataframe(
            st.session_state.my_ledger_data,
            use_container_width=True, 
            height=1600, 
            hide_index=True
        )
    else:
        st.info("아직 저장된 장부 내역이 없습니다. 좌측 장부 입력폼을 통해 타점을 기록해 보세요!")