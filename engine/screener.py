import json, os
from . import datasource

HERE = os.path.dirname(os.path.abspath(__file__))
STRATEGIES_DIR = os.path.join(os.path.dirname(HERE), "strategies")

SIMPLE_KEYS = (
    "price_min", "price_max", "turnover_min", "turnover_max",
    "change_pct_min", "change_pct_max",
    "volume_ratio_min", "volume_ratio_max",
    "market_cap_min", "market_cap_max",
    "pe_min", "pe_max", "pb_min", "pb_max",
    "roe_min", "turnover_amt_min", "amplitude_max",
    "main_inflow_min",
)

TECH_KEYS = ("ma_aligned", "ma5_bull", "ma5_bear", "ma10_bull", "ma10_bear",
             "ma20_bull", "ma20_bear", "ma60_bull", "ma60_bear",
             "macd_golden_cross", "kdj_golden_cross",
             "breakout_volume", "consecutive_up")

BOARD_KEYS = ("board_sh_main", "board_sz_main", "board_chi_next",
              "board_star", "board_bse", "include_st")


def _needs_tech_check(filters):
    for k in TECH_KEYS:
        if filters.get(k):
            return True
    return False


def _check_board(filters, stock):
    code = stock.get("code", "")
    name = stock.get("name", "")

    # 板块过滤: 默认全部不打勾 = 全部允许; 打了 False = 排除
    # 如果 filters 里没有 board 相关 key，默认全部通过
    has_board_filter = any(filters.get(k) is not None for k in BOARD_KEYS)
    if not has_board_filter:
        return False

    if filters.get("board_sh_main") is False and code.startswith("6") and not code.startswith("688"):
        return True
    if filters.get("board_sz_main") is False and code.startswith(("00", "001")):
        return True
    if filters.get("board_chi_next") is False and code.startswith("30"):
        return True
    if filters.get("board_star") is False and code.startswith("688"):
        return True
    if filters.get("board_bse") is False and (code.startswith("8") or code.startswith("4")):
        return True
    if filters.get("include_st") is False and ("ST" in name or "*ST" in name):
        return True
    return False


def _check_simple(filters, s):
    checks_ok = 0
    checks_near = 0
    total = 0
    reasons = []

    def check_range(v, k_min, k_max, label, unit=""):
        nonlocal checks_ok, checks_near, total
        vmin = filters.get(k_min)
        vmax = filters.get(k_max)
        if vmin is None and vmax is None:
            return
        total += 1
        ok = True
        if vmin is not None and v < vmin:
            ok = False
        if vmax is not None and v > vmax:
            ok = False
        if ok:
            checks_ok += 1
        else:
            r = f"{label}{v}{unit}"
            if vmin is not None and vmax is not None:
                r += f" 不在范围({vmin}-{vmax})"
            elif vmin is not None:
                r += f" 低于{vmin}"
            else:
                r += f" 高于{vmax}"
            reasons.append(r)

    check_range(s["price"], "price_min", "price_max", "股价", "元")
    check_range(s["change_pct"], "change_pct_min", "change_pct_max", "涨跌幅", "%")
    check_range(s["turnover_rate"], "turnover_min", "turnover_max", "换手率", "%")
    check_range(s["volume_ratio"], "volume_ratio_min", "volume_ratio_max", "量比")
    check_range(s["market_cap"], "market_cap_min", "market_cap_max", "市值", "亿")
    check_range(s.get("pe", 0), "pe_min", "pe_max", "PE")
    check_range(s.get("pb", 0), "pb_min", "pb_max", "PB")

    roe_min = filters.get("roe_min")
    if roe_min is not None:
        total += 1
        if s.get("roe", 0) >= roe_min:
            checks_ok += 1
        else:
            reasons.append(f"ROE{s.get('roe',0)}% 低于{roe_min}%")

    ta_min = filters.get("turnover_amt_min")
    if ta_min is not None:
        total += 1
        if s.get("turnover_amt", 0) >= ta_min:
            checks_ok += 1
        else:
            reasons.append(f"成交额{s.get('turnover_amt',0):.1f}亿 低于{ta_min}亿")

    amp_max = filters.get("amplitude_max")
    if amp_max is not None:
        total += 1
        if s.get("amplitude", 0) <= amp_max:
            checks_ok += 1
        else:
            reasons.append(f"振幅{s.get('amplitude',0)}% 超过{amp_max}%")

    mi_min = filters.get("main_inflow_min")
    if mi_min is not None:
        total += 1
        if s.get("main_inflow", 0) >= mi_min:
            checks_ok += 1
        else:
            reasons.append(f"主力净流入{s.get('main_inflow',0):.0f}万 低于{mi_min}万")

    return checks_ok, checks_near, total, reasons


def _check_technicals(filters, code, price=0):
    t = datasource.compute_all_technicals(code)
    ok = 0
    total = 0
    reasons = []

    if filters.get("ma_aligned"):
        total += 1
        if t["ma"]["status"] in ("aligned", "near"):
            ok += 1
        else:
            reasons.append("均线非多头排列")

    mas = t["ma"].get("mas", {})
    for n in (5, 10, 20, 60):
        key_bull = f"ma{n}_bull"
        key_bear = f"ma{n}_bear"
        ma_val = mas.get(f"ma{n}", 0) if mas else 0
        if filters.get(key_bull) and ma_val > 0:
            total += 1
            if price > ma_val:
                ok += 1
            else:
                reasons.append(f"{n}日线非多头(价{price:.1f}<MA{n}{ma_val:.1f})")
        if filters.get(key_bear) and ma_val > 0:
            total += 1
            if price < ma_val:
                ok += 1
            else:
                reasons.append(f"{n}日线非空头(价{price:.1f}>MA{n}{ma_val:.1f})")

    if filters.get("macd_golden_cross"):
        total += 1
        if t["macd"]["status"] == "golden_cross":
            ok += 1
        else:
            reasons.append(f"MACD非金叉({t['macd'].get('status','?')})")

    if filters.get("kdj_golden_cross"):
        total += 1
        if t["kdj"]["status"] == "golden_cross":
            ok += 1
        else:
            reasons.append(f"KDJ非金叉({t['kdj'].get('status','?')})")

    if filters.get("consecutive_up"):
        need = filters["consecutive_up"]
        total += 1
        if t["consecutive"]["up"] >= need:
            ok += 1
        else:
            reasons.append(f"连续收阳{t['consecutive']['up']}天 < {need}天")

    if filters.get("breakout_volume"):
        total += 1
        if t["consecutive"]["volume_up"] >= 1:
            ok += 1
        else:
            reasons.append("未放量突破")

    return ok, total, reasons, t


def _check_all_simple(filters, s):
    ok, near, total, reasons = _check_simple(filters, s)
    return ok == total if total > 0 else True, reasons


def screen(stocks, strategy_name, ma_checker=None):
    st = _load_strategy(strategy_name)
    filters = st.get("filters", {})
    sim_cfg = st.get("similar", {})
    sim_enabled = sim_cfg.get("enabled", False)
    need_tech = _needs_tech_check(filters)

    # 第一遍：纯内存过滤 (排除 + 简单数值)
    candidates = []
    for s in stocks:
        if _check_board(filters, s):
            continue
        stock = {
            "code": s.get("code", ""), "name": s.get("name", ""),
            "price": s.get("price", 0), "change_pct": s.get("change_pct", 0),
            "turnover_rate": s.get("turnover_rate", 0),
            "volume_ratio": s.get("volume_ratio", 0),
            "market_cap": s.get("market_cap", 0),
            "main_inflow": s.get("main_inflow", 0),
            "pe": s.get("pe", 0), "pb": s.get("pb", 0),
            "roe": s.get("roe", 0), "turnover_amt": s.get("turnover_amt", 0),
            "amplitude": s.get("amplitude", 0),
            "match_type": "exact", "similar_reasons": [],
            "ma_status": "no", "mas": {},
            "macd": None, "kdj": None, "consecutive": None,
        }
        passed, simple_reasons = _check_all_simple(filters, s)
        if passed:
            candidates.append(stock)
        elif sim_enabled:
            stock["match_type"] = "similar"
            stock["similar_reasons"].extend(simple_reasons)
            candidates.append(stock)

    # 按换手率排序，技术指标只查前 100 只
    candidates.sort(key=lambda x: x["turnover_rate"], reverse=True)
    need_tech_for = [c for c in candidates if c["match_type"] == "exact" and need_tech]

    tech_batch = need_tech_for[:100]
    for stock in tech_batch:
        tech_ok, tech_total, tech_reasons, tech_data = _check_technicals(filters, stock["code"], stock.get("price", 0))
        stock["ma_status"] = tech_data["ma"]["status"]
        stock["mas"] = tech_data["ma"].get("mas", {})
        stock["macd"] = tech_data["macd"]
        stock["kdj"] = tech_data["kdj"]
        stock["consecutive"] = tech_data["consecutive"]
        if tech_ok < tech_total:
            if sim_enabled:
                stock["match_type"] = "similar"
                stock["similar_reasons"].extend(tech_reasons)
            else:
                stock["match_type"] = "_rejected"

    # ma_checker fallback for legacy compatibility
    if not need_tech and ma_checker and filters.get("ma_aligned"):
        for stock in [c for c in candidates if c["match_type"] == "exact"][:100]:
            status, mas = ma_checker(stock["code"])
            stock["ma_status"] = status
            stock["mas"] = mas
            if status not in ("aligned", "near"):
                if sim_enabled:
                    stock["match_type"] = "similar"
                    stock["similar_reasons"].append("均线未多头排列")
                else:
                    stock["match_type"] = "_rejected"

    exact = [c for c in candidates if c["match_type"] == "exact"]
    similar = [c for c in candidates if c["match_type"] == "similar"]

    return st.get("name", strategy_name), exact, similar


def _load_strategy(name):
    path = os.path.join(STRATEGIES_DIR, f"{name}.json")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    from .strategy_mgr import PRESETS
    if name in PRESETS:
        return PRESETS[name]
    raise FileNotFoundError(f"策略不存在: {name}")
