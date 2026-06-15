# -*- coding: utf-8 -*-
"""策略解析器 — 本地正则 + Groq AI"""

import re, json
import urllib.request as _rq

CMP_GT = r'(?:>|＞|大于|超过|高于)'
CMP_LT = r'(?:<|＜|小于|低于|不到|不超过)'
CMP_RANGE = r'(?:-|~|到|至)'

PATTERNS = [
    # 价格
    (rf'(?:股价|价格)\D*(\d+\.?\d*)\s*{CMP_RANGE}\s*(\d+\.?\d*)', "price_range"),
    (rf'(?:股价|价格)\s*{CMP_GT}\s*(\d+\.?\d*)', "price_min"),
    (rf'(?:股价|价格)\s*{CMP_LT}\s*(\d+\.?\d*)', "price_max"),

    # 换手率
    (rf'换手[率]?\s*{CMP_GT}\s*(\d+\.?\d*)', "turnover_min"),
    (rf'换手[率]?\s*{CMP_LT}\s*(\d+\.?\d*)', "turnover_max"),
    (rf'换手[率]?\s*(\d+\.?\d*)\s*{CMP_RANGE}\s*(\d+\.?\d*)', "turnover_range"),

    # 涨跌幅
    (rf'(?:涨跌幅?|涨幅|涨)\s*{CMP_GT}\s*(\d+\.?\d*)', "change_pct_min"),
    (rf'(?:涨跌幅?|涨幅|涨)\s*{CMP_LT}\s*(\d+\.?\d*)', "change_pct_max"),
    (rf'(?:涨跌幅?|涨幅|涨)\s*(\d+\.?\d*)\s*{CMP_RANGE}\s*(\d+\.?\d*)', "change_pct_range"),

    # 跌幅专用
    (rf'跌幅\s*{CMP_LT}\s*(\d+\.?\d*)', "decline_max"),
    (rf'跌幅\s*{CMP_GT}\s*(\d+\.?\d*)', "decline_min"),

    # 量比
    (rf'量比\s*{CMP_GT}\s*(\d+\.?\d*)', "volume_ratio_min"),
    (rf'量比\s*{CMP_LT}\s*(\d+\.?\d*)', "volume_ratio_max"),

    # 市值
    (rf'(?:总市值|流通市值|市值)\s*{CMP_LT}\s*(\d+\.?\d*)\s*(?:亿)?', "market_cap_max"),
    (rf'(?:总市值|流通市值|市值)\s*{CMP_GT}\s*(\d+\.?\d*)\s*(?:亿)?', "market_cap_min"),
    (rf'(?:总市值|流通市值|市值)\s*(\d+\.?\d*)\s*{CMP_RANGE}\s*(\d+\.?\d*)\s*(?:亿)?', "market_cap_range"),

    # 市盈率 PE
    (rf'(?:市盈率|PE|pe)\s*{CMP_LT}\s*(\d+\.?\d*)', "pe_max"),
    (rf'(?:市盈率|PE|pe)\s*{CMP_GT}\s*(\d+\.?\d*)', "pe_min"),
    (rf'(?:市盈率|PE|pe)\s*(\d+\.?\d*)\s*{CMP_RANGE}\s*(\d+\.?\d*)', "pe_range"),

    # 市净率 PB
    (rf'(?:市净率|PB|pb)\s*{CMP_LT}\s*(\d+\.?\d*)', "pb_max"),
    (rf'(?:市净率|PB|pb)\s*{CMP_GT}\s*(\d+\.?\d*)', "pb_min"),

    # 成交额
    (rf'(?:成交额|交易额)\s*{CMP_GT}\s*(\d+\.?\d*)\s*(?:亿|万)?', "turnover_amt_min"),
    (rf'(?:成交额|交易额)\s*{CMP_LT}\s*(\d+\.?\d*)\s*(?:亿|万)?', "turnover_amt_max"),

    # 振幅
    (rf'振幅\s*{CMP_LT}\s*(\d+\.?\d*)', "amplitude_max"),
    (rf'振幅\s*{CMP_GT}\s*(\d+\.?\d*)', "amplitude_min"),

    # ROE
    (rf'(?:ROE|roe|净资产收益率)\s*{CMP_GT}\s*(\d+\.?\d*)', "roe_min"),

    # 主力净流入
    (rf'(?:主力[资金净]*流入|主力净流入|主力买入)\s*{CMP_GT}\s*(\d+\.?\d*)\s*(?:万|亿)?', "main_inflow_min"),

    # 连续天数
    (r'连续\s*(\d+)\s*(?:日|天|个交易日)\s*(?:收阳|上涨|阳线)', "consecutive_up"),
    (r'连续\s*(\d+)\s*(?:日|天|个交易日)\s*(?:收阴|下跌|阴线)', "consecutive_down"),
    (r'连续\s*(\d+)\s*(?:日|天|个交易日)\s*(?:放量)', "consecutive_volume_up"),

    # 均线
    (r'均线多头|多头排列|多头均线', "ma_aligned"),
    (r'均线空头|空头排列|空头均线', "ma_aligned_false"),
    (rf'站上\s*(\d+)\s*日[均]?线', "above_ma"),

    # 放量
    (r'放量突破|放量上涨|放量拉升', "breakout_volume"),

    # MACD
    (r'MACD\s*金叉', "macd_golden_cross"),
    (r'MACD\s*死叉', "macd_death_cross"),

    # KDJ
    (r'KDJ\s*金叉', "kdj_golden_cross"),
    (r'KDJ\s*死叉', "kdj_death_cross"),

    # 均线多空
    (r'(\d+)\s*日(?:均线)?\s*多头', "ma_n_bull"),
    (r'(\d+)\s*日(?:均线)?\s*空头', "ma_n_bear"),

    # 板块 (排除→打勾取消)
    (r'(?:排除|去掉|去除|剔除|不要|非)\s*(?:了)?\s*ST', "include_st_false"),
    (r'(?:排除|去掉|去除|剔除|不要|非)\s*(?:了)?\s*(?:科创|688)', "board_star_false"),
    (r'(?:排除|去掉|去除|剔除|不要|非)\s*(?:了)?\s*(?:创业|300)', "board_chi_next_false"),
    (r'(?:排除|去掉|去除|剔除|不要|非)\s*(?:了)?\s*(?:北交|北证)', "board_bse_false"),
    (r'(?:排除|去掉|去除|剔除|不要|非)\s*(?:了)?\s*(?:沪市|上证)', "board_sh_main_false"),
    (r'(?:排除|去掉|去除|剔除|不要|非)\s*(?:了)?\s*(?:深市|深证)', "board_sz_main_false"),
    (r'(?:只[要看]|只要|仅|仅限|限于)\s*主板', "main_board_only"),
    (r'(?:包含|包括|要)\s*ST', "include_st"),
]

LABELS = {
    "price_min":"最低价","price_max":"最高价",
    "turnover_min":"最低换手率(%)","turnover_max":"最高换手率(%)",
    "change_pct_min":"最低涨跌幅(%)","change_pct_max":"最高涨跌幅(%)",
    "volume_ratio_min":"最低量比","volume_ratio_max":"最高量比",
    "market_cap_min":"最低市值(亿)","market_cap_max":"最高市值(亿)",
    "pe_min":"最低PE","pe_max":"最高PE",
    "pb_min":"最低PB","pb_max":"最高PB",
    "turnover_amt_min":"最低成交额","turnover_amt_max":"最高成交额",
    "amplitude_min":"最低振幅(%)","amplitude_max":"最高振幅(%)",
    "roe_min":"最低ROE(%)",
    "main_inflow_min":"最低主力净流入",
    "consecutive_up":"连续收阳(天)","consecutive_down":"连续收阴(天)",
    "consecutive_volume_up":"连续放量(天)",
    "ma_aligned":"均线多头排列","above_ma":"站上均线",
    "ma5_bull":"5日线多头","ma5_bear":"5日线空头",
    "ma10_bull":"10日线多头","ma10_bear":"10日线空头",
    "ma20_bull":"20日线多头","ma20_bear":"20日线空头",
    "ma60_bull":"60日线多头","ma60_bear":"60日线空头",
    "breakout_volume":"放量突破",
    "macd_golden_cross":"MACD金叉","macd_death_cross":"MACD死叉",
    "kdj_golden_cross":"KDJ金叉","kdj_death_cross":"KDJ死叉",
    "board_sh_main":"沪市主板","board_sz_main":"深市主板",
    "board_chi_next":"创业板","board_star":"科创板","board_bse":"北交所",
    "include_st":"包含ST",
    "main_board_only":"仅限主板",
}


def parse_local(prompt):
    result = {}
    for pattern, key in PATTERNS:
        m = re.search(pattern, prompt, re.IGNORECASE)
        if not m:
            continue

        if key == "price_range":
            a,b=float(m.group(1)),float(m.group(2))
            if a>b: a,b=b,a
            result["price_min"]=a; result["price_max"]=b
        elif key == "turnover_range":
            a,b=float(m.group(1)),float(m.group(2))
            if a>b: a,b=b,a
            result["turnover_min"]=a; result["turnover_max"]=b
        elif key == "change_pct_range":
            a,b=float(m.group(1)),float(m.group(2))
            if a>b: a,b=b,a
            result["change_pct_min"]=a; result["change_pct_max"]=b
        elif key == "market_cap_range":
            a,b=float(m.group(1)),float(m.group(2))
            if a>b: a,b=b,a
            result["market_cap_min"]=a; result["market_cap_max"]=b
        elif key == "pe_range":
            a,b=float(m.group(1)),float(m.group(2))
            if a>b: a,b=b,a
            result["pe_min"]=a; result["pe_max"]=b
        elif key == "decline_max":
            result["change_pct_min"]=-float(m.group(1))
        elif key == "decline_min":
            result["change_pct_max"]=-float(m.group(1))
        elif key in ("price_min","price_max","turnover_min","turnover_max",
                     "change_pct_min","change_pct_max",
                     "volume_ratio_min","volume_ratio_max",
                     "market_cap_min","market_cap_max",
                     "pe_min","pe_max","pb_min","pb_max",
                     "turnover_amt_min","turnover_amt_max",
                     "amplitude_min","amplitude_max",
                     "roe_min","main_inflow_min"):
            result[key]=float(m.group(1))
        elif key in ("consecutive_up","consecutive_down","consecutive_volume_up","above_ma"):
            result[key]=int(m.group(1))
        elif key == "ma_aligned_false":
            result["ma_aligned"]=False
        elif key in ("ma_aligned","breakout_volume","macd_golden_cross","macd_death_cross",
                     "kdj_golden_cross","kdj_death_cross",
                     "main_board_only"):
            result[key]=True
        elif key == "include_st_false":
            result["include_st"]=False
        elif key.startswith("board_") and key.endswith("_false"):
            result[key.replace("_false","")]=False
        elif key == "include_st":
            result[key]=True
        elif key == "ma_n_bull":
            n=m.group(1)
            result[f"ma{n}_bull"]=True
        elif key == "ma_n_bear":
            n=m.group(1)
            result[f"ma{n}_bear"]=True

    # 裸数字范围（如 "10-50块"）
    if "price_min" not in result:
        m=re.search(rf'(?:^|\s)(\d+)\s*{CMP_RANGE}\s*(\d+)\s*(?:块|元)?(?:\s|$)',prompt)
        if m and int(m.group(1))>=5:
            a,b=int(m.group(1)),int(m.group(2))
            if a>b: a,b=b,a
            result["price_min"]=a; result["price_max"]=b

    return result if result else None


def describe(cond):
    parts=[]
    for k,v in cond.items():
        lab=LABELS.get(k,k)
        if isinstance(v,bool):
            parts.append(f"{'Y' if v else 'N'} {lab}")
        elif isinstance(v,float) and v==int(v):
            parts.append(f"{lab}: {int(v)}")
        else:
            parts.append(f"{lab}: {v}")
    return " | ".join(parts)


def parse_ai(prompt, groq_key):
    if not groq_key:
        raise RuntimeError("未配置 Groq Key")
    data=json.dumps({
        "model":"llama-3.1-8b-instant",
        "messages":[{"role":"user","content":
            f"将以下股票筛选条件提取为JSON。可用字段：price_min,price_max,turnover_min,"
            f"change_pct_min,change_pct_max,volume_ratio_min,market_cap_min,market_cap_max,"
            f"pe_min,pe_max,pb_min,pb_max,roe_min,amplitude_max,turnover_amt_min,main_inflow_min,"
            f"consecutive_up,ma_aligned,exclude_st,exclude_star,exclude_chi_next,exclude_bse."
            f"没提到的字段不输出。只输出纯JSON，不要解释。\n\n条件：{prompt}"
        }],
        "max_tokens":400,"temperature":0
    }).encode()
    req=_rq.Request("https://api.groq.com/openai/v1/chat/completions",data=data,
        headers={"Authorization":f"Bearer {groq_key}","Content-Type":"application/json"})
    proxy=_rq.ProxyHandler({"http":"127.0.0.1:7897","https":"127.0.0.1:7897"})
    resp=json.loads(_rq.build_opener(proxy).open(req,timeout=15).read())
    raw=resp["choices"][0]["message"]["content"].strip()
    raw=re.sub(r'```(?:json)?\s*','',raw).replace('```','').strip()
    return json.loads(raw)


def parse(prompt, groq_key=""):
    if groq_key:
        try: return parse_ai(prompt,groq_key)
        except: pass
    r=parse_local(prompt)
    if not r:
        raise RuntimeError(f"无法解析：「{prompt}」。试试：股价10-100元 换手率>7% 非ST")
    return r
