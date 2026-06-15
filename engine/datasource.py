import json, urllib.request, urllib.error, sqlite3, os, csv, re, time
from datetime import datetime, timezone, timedelta

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
BJT = timezone(timedelta(hours=8))
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
INDEX_PATH = os.path.join(ROOT, "stock_index.csv")
DB_PATH = os.path.join(ROOT, "stock_history.db")

PROXY_PORT = os.environ.get("CLASH_PORT", "7897")


def _safe_div(v, n):
    if v is None or v == 0:
        return 0
    return v / n


def _sina_code(code):
    if code.startswith("6"):
        return f"sh{code}"
    return f"sz{code}"


def _sina_fetch(url, timeout=8):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Referer": "https://finance.sina.com.cn/"})
    return urllib.request.urlopen(req, timeout=timeout).read().decode("gbk", errors="replace")


def _get_json(url, timeout=10, retries=1):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Referer": "https://www.eastmoney.com/"})
    methods = [
        ("proxy", lambda: urllib.request.build_opener(
            urllib.request.ProxyHandler({"http": f"127.0.0.1:{PROXY_PORT}", "https": f"127.0.0.1:{PROXY_PORT}"})
        ).open(req, timeout=timeout)),
        ("direct", lambda: urllib.request.urlopen(req, timeout=min(timeout, 5))),
    ]
    last_err = ""
    for attempt in range(retries + 1):
        for name, fn in methods:
            try:
                return json.loads(fn().read())
            except Exception as e:
                last_err = f"{name}: {type(e).__name__}"
                if attempt < retries:
                    time.sleep(0.5)
    raise RuntimeError(last_err)


def _now():
    return datetime.now(BJT).strftime("%Y-%m-%d %H:%M:%S")


def today_str():
    return datetime.now(BJT).strftime("%Y-%m-%d")


# ═══════════════════════════════════════════
#  SQLite 缓存
# ═══════════════════════════════════════════
def _init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS data_cache (
            cache_key TEXT PRIMARY KEY,
            data_json TEXT,
            updated_at TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS watch_stock_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT, code TEXT, price REAL, change_pct REAL,
            turnover_rate REAL, pe REAL, volume_ratio REAL,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS daily_briefing (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT, stock_code TEXT, stock_name TEXT,
            price REAL, change_pct REAL, turnover_rate REAL,
            volume_ratio REAL, main_inflow REAL, ma_aligned INTEGER DEFAULT 0,
            match_type TEXT DEFAULT 'exact',
            created_at TEXT DEFAULT (datetime('now','localtime'))
        )
    """)
    conn.commit()
    conn.close()


def cache_put(key, data, db=None):
    own = db is None
    if own:
        db = sqlite3.connect(DB_PATH)
    db.execute("INSERT OR REPLACE INTO data_cache (cache_key, data_json, updated_at) VALUES (?,?,?)",
               (key, json.dumps(data, ensure_ascii=False), _now()))
    if own:
        db.commit(); db.close()


def cache_get(key, max_age_sec=300, db=None):
    own = db is None
    if own:
        db = sqlite3.connect(DB_PATH)
    row = db.execute("SELECT data_json, updated_at FROM data_cache WHERE cache_key=?",
                     (key,)).fetchone()
    if own:
        db.close()
    if not row:
        return None, False
    data = json.loads(row[0])
    fresh = (datetime.now(BJT) - datetime.strptime(row[1], "%Y-%m-%d %H:%M:%S").replace(tzinfo=BJT)).total_seconds() < max_age_sec
    return data, fresh


# ═══════════════════════════════════════════
#  股票名称索引 (CSV)
# ═══════════════════════════════════════════
def search_stock(keyword):
    results = _search_csv(keyword)
    if not results:
        results = _search_online(keyword)
        if results:
            _append_to_index(results)
    return results


def _search_csv(keyword):
    if not os.path.exists(INDEX_PATH):
        return []
    results = []
    kw = keyword.strip().lower()
    try:
        with open(INDEX_PATH, "r", encoding="utf-8") as f:
            for row in csv.reader(f):
                if len(row) < 2:
                    continue
                code, name = row[0], row[1]
                if kw in code or kw in name.lower():
                    results.append({"code": code, "name": name})
                if len(results) >= 12:
                    break
    except Exception:
        pass
    return results


def _search_online(keyword):
    try:
        kw = urllib.parse.quote(keyword)
        url = (f"https://searchadapter.eastmoney.com/api/suggest/get"
               f"?input={kw}&type=14")
        req = urllib.request.Request(url, headers={
            "User-Agent": UA,
            "Referer": "https://www.eastmoney.com/",
        })
        proxy = urllib.request.ProxyHandler({"http": "127.0.0.1:7897", "https": "127.0.0.1:7897"})
        data = json.loads(urllib.request.build_opener(proxy).open(req, timeout=8).read())
        results = []
        for item in data.get("QuotationCodeTable", {}).get("Data", []):
            code = item.get("Code", "")
            name = item.get("Name", "")
            if code and name:
                results.append({"code": code, "name": name})
        return results
    except Exception:
        return []


def _append_to_index(results):
    try:
        existing = set()
        if os.path.exists(INDEX_PATH):
            with open(INDEX_PATH, "r", encoding="utf-8") as f:
                for row in csv.reader(f):
                    if row:
                        existing.add(row[0])
        with open(INDEX_PATH, "a", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            for r in results:
                if r["code"] not in existing:
                    w.writerow([r["code"], r["name"]])
                    existing.add(r["code"])
    except Exception:
        pass


def _build_index():
    try:
        all_stocks = {}
        for page in range(1, 20):
            url = ("http://push2.eastmoney.com/api/qt/clist/get"
                   f"?pn={page}&pz=500&np=1&fltt=2"
                   "&fs=m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23"
                   "&fields=f12,f14")
            data = _get_json(url)
            diff = data.get("data", {}).get("diff", [])
            if not diff:
                break
            for d in diff:
                code = d.get("f12", "")
                if code and code not in all_stocks:
                    all_stocks[code] = d.get("f14", "")
        stocks = sorted(all_stocks.items(), key=lambda x: x[0])
        with open(INDEX_PATH, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerows(stocks)
    except Exception:
        if not os.path.exists(INDEX_PATH):
            with open(INDEX_PATH, "w", encoding="utf-8", newline="") as f:
                f.write("")


def refresh_index():
    if os.path.exists(INDEX_PATH):
        os.remove(INDEX_PATH)
    _build_index()
    return os.path.exists(INDEX_PATH)


# ═══════════════════════════════════════════
#  大盘指数
# ═══════════════════════════════════════════
def get_indices():
    result, fresh = _get_indices_eastmoney()
    if not result:
        result, fresh = _get_indices_sina()
    if not result:
        result, fresh = cache_get("indices", max_age_sec=3600)
        result = result or {}
    return result, fresh


def _get_indices_eastmoney():
    try:
        url = ("http://push2.eastmoney.com/api/qt/ulist.np/get"
               "?fields=f2,f3,f4,f12,f14"
               "&secids=1.000001,0.399001,0.399006,1.000300&fltt=2")
        data = _get_json(url)
        result = {}
        for d in data.get("data", {}).get("diff", []):
            result[d["f14"]] = {
                "price": d["f2"], "change_pct": d["f3"],
                "change_amt": d["f4"], "code": d["f12"]
            }
        cache_put("indices", result)
        return result, True
    except Exception:
        return {}, False


def _get_indices_sina():
    try:
        url = "http://hq.sinajs.cn/list=s_sh000001,s_sz399001,s_sz399006,s_sh000300"
        raw = _sina_fetch(url)
        result = {}
        names = {"上证指数": "000001", "深证成指": "399001", "创业板指": "399006", "沪深300": "000300"}
        for line in raw.strip().split("\n"):
            if "=" not in line:
                continue
            data = line.split('"')[1].split(",") if '"' in line else []
            if len(data) < 4:
                continue
            for n, c in names.items():
                if c in line:
                    result[n] = {
                        "price": float(data[1]),
                        "change_pct": round((float(data[1]) - float(data[2])) / float(data[2]) * 100, 2),
                        "change_amt": round(float(data[1]) - float(data[2]), 2),
                        "code": c,
                    }
        if result:
            cache_put("indices", result)
            return result, True
    except Exception:
        pass
    return {}, False


# ═══════════════════════════════════════════
#  单只股票行情
# ═══════════════════════════════════════════
def get_stock(code):
    result, fresh = _get_stock_eastmoney(code)
    if not result:
        result, fresh = _get_stock_sina(code)
    if not result:
        result, fresh = cache_get(f"stock_{code}", max_age_sec=600)
    return result, fresh


def _get_stock_eastmoney(code):
    try:
        url = (f"http://push2.eastmoney.com/api/qt/stock/get?secid=1.{code}"
               f"&fields=f43,f44,f45,f46,f47,f48,f50,f57,f58,f60,f162,f167,f170,f20,f8,f62,f9,f23")
        d = _get_json(url).get("data", {})
        if not d:
            return None, False
        result = {
            "name": d.get("f58", ""), "code": d.get("f57", ""),
            "price": _safe_div(d.get("f43"), 100),
            "open": _safe_div(d.get("f46"), 100),
            "high": _safe_div(d.get("f44"), 100),
            "low": _safe_div(d.get("f45"), 100),
            "prev_close": _safe_div(d.get("f60"), 100),
            "change_pct": _safe_div(d.get("f170"), 100),
            "volume_hands": d.get("f47", 0) or 0,
            "turnover_amt": d.get("f48", 0) or 0,
            "turnover_rate": _safe_div(d.get("f8"), 100),
            "pe": _safe_div(d.get("f162"), 100),
            "pe_dynamic": _safe_div(d.get("f9"), 100),
            "pb": _safe_div(d.get("f167"), 100),
            "market_cap": _safe_div(d.get("f20"), 1e8),
            "volume_ratio": _safe_div(d.get("f50"), 10),
            "main_inflow": _safe_div(d.get("f62"), 10000),
        }
        cache_put(f"stock_{code}", result)
        return result, True
    except Exception:
        return None, False


def _get_stock_sina(code):
    try:
        sc = _sina_code(code)
        raw = _sina_fetch(f"http://hq.sinajs.cn/list={sc}")
        data = raw.split('"')[1].split(",") if '"' in raw else []
        if len(data) < 30:
            return None, False
        price = float(data[3])
        prev = float(data[2])
        result = {
            "name": data[0], "code": code,
            "price": price,
            "open": float(data[1]),
            "high": float(data[4]),
            "low": float(data[5]),
            "prev_close": prev,
            "change_pct": round((price - prev) / prev * 100, 2),
            "volume_hands": int(float(data[8])),
            "turnover_amt": float(data[9]),
            "turnover_rate": 0,
            "pe": 0, "pe_dynamic": 0, "pb": 0,
            "market_cap": 0,
            "volume_ratio": 0,
            "main_inflow": 0,
        }
        cache_put(f"stock_{code}", result)
        return result, True
    except Exception:
        return None, False


# ═══════════════════════════════════════════
#  市场扫描
# ═══════════════════════════════════════════
def scan_market():
    stocks, fresh = _scan_eastmoney()
    if not stocks:
        stocks, fresh = _scan_sina()
    if not stocks:
        stocks, fresh = cache_get("scan_market", max_age_sec=600)
        stocks = stocks or []
    return stocks, fresh


def _scan_eastmoney():
    try:
        all_stocks = {}
        for page in range(1, 12):
            url = ("http://push2.eastmoney.com/api/qt/clist/get"
                   f"?fid=f8&po=1&pz=500&pn={page}&np=1&fltt=2"
                   "&fs=m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23"
                   "&fields=f2,f3,f4,f8,f10,f12,f14,f20,f62,f15,f16,f17,f9,f23,f37,f48")
            data = _get_json(url, timeout=10)
            diff = data.get("data", {}).get("diff", [])
            if not diff:
                break
            for d in diff:
                code = d.get("f12", "")
                if code and code not in all_stocks:
                    prev_close = _safe_div(d.get("f18"), 100)
                    high = _safe_div(d.get("f15"), 100)
                    low = _safe_div(d.get("f16"), 100)
                    all_stocks[code] = {
                        "code": code,
                        "name": d.get("f14", ""),
                        "price": d.get("f2", 0) or 0,
                        "change_pct": d.get("f3", 0) or 0,
                        "turnover_rate": _safe_div(d.get("f8"), 100),
                        "volume_ratio": _safe_div(d.get("f10"), 10),
                        "market_cap": _safe_div(d.get("f20"), 1e8),
                        "main_inflow": _safe_div(d.get("f62"), 10000),
                        "high": high,
                        "low": low,
                        "pe": _safe_div(d.get("f9"), 100),
                        "pb": _safe_div(d.get("f23"), 100),
                        "roe": _safe_div(d.get("f37"), 100),
                        "turnover_amt": _safe_div(d.get("f48"), 1e8),
                        "amplitude": round((high - low) / prev_close * 100, 2) if prev_close > 0 else 0,
                    }
        stocks = list(all_stocks.values())
        if stocks:
            cache_put("scan_market", stocks)
        return stocks, True
    except Exception:
        return [], False


def _scan_sina():
    try:
        all_stocks = {}
        for page in range(1, 15):
            url = (f"http://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/"
                   f"Market_Center.getHQNodeData?page={page}&num=500&sort=symbol&asc=1"
                   f"&node=hs_a&symbol=&_s_r_a=auto")
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Referer": "https://finance.sina.com.cn/"})
            raw = urllib.request.urlopen(req, timeout=10).read().decode("gbk", errors="replace")
            data = json.loads(raw)
            if not data:
                break
            for d in data:
                code = d.get("symbol", "")
                if code and code not in all_stocks:
                    price = float(d.get("trade", 0) or 0)
                    prev = float(d.get("settlement", 0) or 0)
                    all_stocks[code] = {
                        "code": code,
                        "name": d.get("name", ""),
                        "price": price,
                        "change_pct": float(d.get("changepercent", 0) or 0),
                        "turnover_rate": float(d.get("turnoverratio", 0) or 0),
                        "volume_ratio": float(d.get("amount", 0) or 0) / 1e8,
                        "market_cap": 0,
                        "main_inflow": 0,
                        "high": float(d.get("high", 0) or 0),
                        "low": float(d.get("low", 0) or 0),
                        "pe": float(d.get("per", 0) or 0),
                        "pb": float(d.get("pb", 0) or 0),
                        "roe": 0,
                        "turnover_amt": float(d.get("amount", 0) or 0) / 1e8,
                        "amplitude": 0,
                    }
        stocks = list(all_stocks.values())
        if stocks:
            cache_put("scan_market", stocks)
        return stocks, True
    except Exception:
        return [], False


# ═══════════════════════════════════════════
#  K线 (均线 / MACD / KDJ 共用)
# ═══════════════════════════════════════════
def get_kline(code, days=70):
    result, fresh = _get_kline_eastmoney(code, days)
    if not result:
        result, fresh = _get_kline_sina(code, days)
    if not result:
        data, fresh = cache_get(f"kline_{code}", max_age_sec=3600)
        result = data.get("klines", []) if data else []
    return result, fresh


def _get_kline_eastmoney(code, days=70):
    try:
        secid = f"1.{code}" if code.startswith("6") else f"0.{code}"
        url = (f"http://push2.eastmoney.com/api/qt/stock/kline/get"
               f"?secid={secid}&fields1=f1,f2,f3,f4,f5,f6"
               f"&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61"
               f"&klt=101&fqt=1&end=20500101&lmt={days}")
        data = _get_json(url)
        klines = data.get("data", {}).get("klines", [])
        result = []
        for k in klines:
            parts = k.split(",")
            result.append({
                "date": parts[0],
                "open": float(parts[1]),
                "close": float(parts[2]),
                "high": float(parts[3]),
                "low": float(parts[4]),
                "volume": float(parts[5]),
                "amount": float(parts[6]),
            })
        cache_put(f"kline_{code}", {"klines": result, "count": len(result)})
        return result, True
    except Exception:
        return [], False


def _get_kline_sina(code, days=70):
    try:
        sc = _sina_code(code)
        url = (f"http://money.finance.sina.com.cn/quotes_service/api/json_v2.php/"
               f"CN_MarketData.getKLineData?symbol={sc}&scale=240&ma=no&datalen={days}")
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Referer": "https://finance.sina.com.cn/"})
        raw = urllib.request.urlopen(req, timeout=10).read().decode("gbk", errors="replace")
        data = json.loads(raw)
        result = []
        for d in data:
            result.append({
                "date": d.get("day", ""),
                "open": float(d.get("open", 0)),
                "close": float(d.get("close", 0)),
                "high": float(d.get("high", 0)),
                "low": float(d.get("low", 0)),
                "volume": float(d.get("volume", 0)),
                "amount": 0,
            })
        if result:
            cache_put(f"kline_{code}", {"klines": result, "count": len(result)})
            return result, True
    except Exception:
        pass
    return [], False


# ═══════════════════════════════════════════
#  技术指标计算 (纯本地)
# ═══════════════════════════════════════════
def compute_ma(klines):
    if len(klines) < 60:
        return {"status": "no", "mas": {}}
    closes = [k["close"] for k in klines]
    mas = {
        "ma5": round(sum(closes[-5:]) / 5, 2),
        "ma10": round(sum(closes[-10:]) / 10, 2),
        "ma20": round(sum(closes[-20:]) / 20, 2),
        "ma60": round(sum(closes[-60:]) / 60, 2),
        "_price": closes[-1],
    }
    if mas["ma5"] > mas["ma10"] > mas["ma20"] > mas["ma60"]:
        return {"status": "aligned", "mas": mas}
    if mas["ma5"] > mas["ma10"] > mas["ma20"] and mas["ma20"] < mas["ma60"]:
        gap = abs(mas["ma20"] - mas["ma60"]) / mas["ma60"] * 100
        if gap < 5:
            return {"status": "near", "mas": mas}
    return {"status": "no", "mas": mas}


def compute_macd(klines):
    if len(klines) < 35:
        return {"status": "no"}
    closes = [k["close"] for k in klines]

    def ema(data, n):
        k = 2 / (n + 1)
        result = [data[0]]
        for v in data[1:]:
            result.append(v * k + result[-1] * (1 - k))
        return result

    dif = [a - b for a, b in zip(ema(closes, 12), ema(closes, 26))]
    dea = ema(dif, 9)
    macd_hist = [(dif[i] - dea[i]) * 2 for i in range(len(dif))]

    prev_dif, prev_dea = dif[-2], dea[-2]
    cur_dif, cur_dea = dif[-1], dea[-1]

    if prev_dif <= prev_dea and cur_dif > cur_dea:
        status = "golden_cross"
    elif prev_dif >= prev_dea and cur_dif < cur_dea:
        status = "death_cross"
    elif cur_dif > cur_dea:
        status = "above"
    elif cur_dif < cur_dea:
        status = "below"
    else:
        status = "flat"

    return {"status": status, "dif": round(cur_dif, 3), "dea": round(cur_dea, 3),
            "macd": round(macd_hist[-1], 3)}


def compute_kdj(klines, n=9):
    if len(klines) < n + 5:
        return {"status": "no"}
    highs = [k["high"] for k in klines]
    lows = [k["low"] for k in klines]
    closes = [k["close"] for k in klines]

    k_vals, d_vals = [], []
    k_prev, d_prev = 50, 50

    for i in range(n - 1, len(closes)):
        hh = max(highs[i - n + 1:i + 1])
        ll = min(lows[i - n + 1:i + 1])
        rsv = (closes[i] - ll) / (hh - ll) * 100 if hh != ll else 50
        k_prev = 2 / 3 * k_prev + 1 / 3 * rsv
        d_prev = 2 / 3 * d_prev + 1 / 3 * k_prev
        k_vals.append(round(k_prev, 2))
        d_vals.append(round(d_prev, 2))

    prev_k, prev_d = k_vals[-2], d_vals[-2]
    cur_k, cur_d = k_vals[-1], d_vals[-1]

    if prev_k <= prev_d and cur_k > cur_d:
        status = "golden_cross"
    elif prev_k >= prev_d and cur_k < cur_d:
        status = "death_cross"
    elif cur_k > cur_d:
        status = "above"
    elif cur_k < cur_d:
        status = "below"
    else:
        status = "flat"

    return {"status": status, "k": cur_k, "d": cur_d, "j": round(3 * cur_k - 2 * cur_d, 2)}


def compute_consecutive(klines):
    if len(klines) < 5:
        return {"up": 0, "down": 0, "volume_up": 0}
    up = down = vol_up = 0
    for k in reversed(klines):
        if k["close"] > k["open"]:
            if down == 0 and vol_up == 0:
                up += 1
            else:
                break
        elif k["close"] < k["open"]:
            if up == 0 and vol_up == 0:
                down += 1
            else:
                break
        else:
            break
    prev_vol = None
    for k in reversed(klines):
        if prev_vol is None:
            prev_vol = k["volume"]
            continue
        if k["volume"] > prev_vol * 1.1 and k["close"] > k["open"]:
            vol_up += 1
            prev_vol = k["volume"]
        else:
            break
    return {"up": up, "down": down, "volume_up": vol_up}


def compute_all_technicals(code):
    klines, fresh = get_kline(code, days=70)
    if not klines or len(klines) < 30:
        return {"ma": {"status": "no"}, "macd": {"status": "no"},
                "kdj": {"status": "no"}, "consecutive": {"up": 0, "down": 0, "volume_up": 0}}
    return {
        "ma": compute_ma(klines),
        "macd": compute_macd(klines),
        "kdj": compute_kdj(klines),
        "consecutive": compute_consecutive(klines),
    }


# ═══════════════════════════════════════════
#  新闻
# ═══════════════════════════════════════════
def get_news():
    try:
        req = urllib.request.Request("https://finance.eastmoney.com/a/czqyw.html", headers={"User-Agent": UA})
        raw = urllib.request.urlopen(req, timeout=10).read()
        html = raw.decode("utf-8", errors="replace")
        titles = re.findall(
            r'<a[^>]+href="https://finance\.eastmoney\.com/a/\d+\.html"[^>]*>([^<]{15,})</a>', html
        )
        clean = []
        for t in titles:
            t = re.sub(r"<[^>]+>", "", t).replace("　", " ").strip()
            if len(t) >= 15 and "免责" not in t and "广告" not in t:
                clean.append(t)
        return clean[:5]
    except Exception:
        return ["（新闻拉取失败）"]


def ensure_ready():
    _init_db()
    if not os.path.exists(INDEX_PATH) or os.path.getsize(INDEX_PATH) < 100:
        try:
            _build_index()
        except Exception:
            if not os.path.exists(INDEX_PATH):
                with open(INDEX_PATH, "w", encoding="utf-8", newline="") as f:
                    f.write("")
