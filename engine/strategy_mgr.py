import json, os
from . import parser as _parser

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
STRAT_DIR = os.path.join(ROOT, "strategies")

PRESETS = {
    "steady": {
        "name": "稳健筛选",
        "description": "10-100元、换手活跃、均线多头、仅主板",
        "filters": {
            "price_min": 10, "price_max": 100, "turnover_min": 7.0,
            "ma_aligned": True,
            "board_sh_main": True, "board_sz_main": True,
            "board_star": False, "board_chi_next": False, "board_bse": False,
            "include_st": False,
        },
        "similar": {"enabled": True, "price_tolerance": 2.0, "turnover_tolerance": 2.0},
    },
    "momentum": {
        "name": "动量突破",
        "description": "放量上涨、涨幅3%-9%、中小市值",
        "filters": {
            "price_min": 5, "price_max": 200,
            "change_pct_min": 3.0, "change_pct_max": 9.0,
            "volume_ratio_min": 2.0, "market_cap_max": 500,
            "board_star": False, "include_st": False,
        },
        "similar": {"enabled": True, "change_pct_tolerance": 1.0, "volume_ratio_tolerance": 0.5},
    },
    "oversold": {
        "name": "超跌反弹",
        "description": "跌过头、量比放大、可能反弹",
        "filters": {
            "price_min": 3, "price_max": 100,
            "change_pct_min": -9.0, "change_pct_max": -2.0,
            "volume_ratio_min": 1.5, "include_st": False,
        },
        "similar": {"enabled": True, "change_pct_tolerance": 1.0, "volume_ratio_tolerance": 0.3},
    },
}

STRAT_FIELDS = {
    "price_min": "最低价", "price_max": "最高价",
    "change_pct_min": "最低涨跌幅(%)", "change_pct_max": "最高涨跌幅(%)",
    "turnover_min": "最低换手率(%)", "turnover_max": "最高换手率(%)",
    "volume_ratio_min": "最低量比", "volume_ratio_max": "最高量比",
    "turnover_amt_min": "最低成交额(亿)", "turnover_amt_max": "最高成交额(亿)",
    "amplitude_max": "最高振幅(%)",
    "market_cap_min": "最低市值(亿)", "market_cap_max": "最高市值(亿)",
    "pe_min": "最低PE", "pe_max": "最高PE",
    "pb_min": "最低PB", "pb_max": "最高PB",
    "roe_min": "最低ROE(%)",
    "main_inflow_min": "最低主力净流入(万)",
    "consecutive_up": "连续收阳(天)",
    "ma_aligned": "均线多头排列",
    "ma5_bull": "5日线 多头", "ma5_bear": "5日线 空头",
    "ma10_bull": "10日线 多头", "ma10_bear": "10日线 空头",
    "ma20_bull": "20日线 多头", "ma20_bear": "20日线 空头",
    "ma60_bull": "60日线 多头", "ma60_bear": "60日线 空头",
    "macd_golden_cross": "MACD金叉", "macd_death_cross": "MACD死叉",
    "kdj_golden_cross": "KDJ金叉", "kdj_death_cross": "KDJ死叉",
    "breakout_volume": "放量突破",
    "board_sh_main": "沪市主板", "board_sz_main": "深市主板",
    "board_chi_next": "创业板", "board_star": "科创板",
    "board_bse": "北交所", "include_st": "包含 ST 股",
}


class StrategyManager:
    def __init__(self, config_mgr):
        self._cfg = config_mgr
        os.makedirs(STRAT_DIR, exist_ok=True)

    @property
    def current_key(self):
        return self._cfg.get("strategy", "steady")

    @property
    def current_name(self):
        key = self.current_key
        if key in PRESETS:
            return PRESETS[key]["name"]
        path = os.path.join(STRAT_DIR, f"{key}.json")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f).get("name", key)
        return key

    @property
    def presets(self):
        return [{"key": k, "name": v["name"], "desc": v["description"]} for k, v in PRESETS.items()]

    @property
    def fields_meta(self):
        return STRAT_FIELDS

    def switch(self, key):
        if key in PRESETS:
            self._cfg.set("strategy", key)
            return PRESETS[key]["filters"]
        path = os.path.join(STRAT_DIR, f"{key}.json")
        if os.path.exists(path):
            self._cfg.set("strategy", key)
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f).get("filters", {})
        raise FileNotFoundError(f"策略不存在: {key}")

    def get_filters(self):
        key = self.current_key
        if key in PRESETS:
            return dict(PRESETS[key]["filters"]), PRESETS[key].get("similar", {})
        path = os.path.join(STRAT_DIR, f"{key}.json")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                st = json.load(f)
            return st.get("filters", {}), st.get("similar", {})
        return {}, {}

    def save_custom(self, name, description, filters, similar=None):
        st = {
            "name": name or "自定义策略",
            "description": description or "",
            "filters": filters,
            "similar": similar or {"enabled": False},
        }
        path = os.path.join(STRAT_DIR, "custom.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(st, f, ensure_ascii=False, indent=2)
        self._cfg.set("strategy", "custom")
        return st

    def parse_prompt(self, prompt):
        return _parser.parse_local(prompt)

    def describe(self, filters):
        return _parser.describe(filters)
