#!/usr/bin/env python3
"""克克股市晨报 v2 — 计划任务用 CLI"""
import sys, os
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from engine.core import Core
from engine import datasource, notifier, screener


def build_report(date_str, indices, watch_stocks, exact, similar, strategy_name, news):
    lines = [f"克克股市晨报 {date_str}", "=" * 30, ""]
    lines.append("【大盘指数】")
    for name, info in indices.items():
        c = "红" if info["change_pct"] > 0 else "绿"
        lines.append(f"  {name}: {info['price']:.2f} ({info['change_pct']:+.2f}%) {c}")
    lines.append("")

    if watch_stocks:
        lines.append("【自选股】")
        for w in watch_stocks:
            lines.append(f"  {w.get('name','')}({w.get('code','')}) ¥{w.get('price',0):.2f} {w.get('change_pct',0):+.2f}%")
            lines.append(f"    换手率{w.get('turnover_rate',0):.2f}% | PE{w.get('pe',0):.1f} | 市值{w.get('market_cap',0):.1f}亿")
        lines.append("")

    lines.append(f"【{strategy_name}】")
    if exact:
        lines.append("  --- 完全符合 ---")
        for i, s in enumerate(exact[:8], 1):
            ma = " ★均线多头" if s.get("ma_status") == "aligned" else ""
            lines.append(f"  {i}. {s['name']}({s['code']}) ¥{s['price']:.2f} {s['change_pct']:+.2f}%")
            lines.append(f"     换手率{s['turnover_rate']:.1f}% | 量比{s['volume_ratio']:.1f} | 主力净流入{s.get('main_inflow',0):.0f}万{ma}")

    if similar:
        lines.append("  --- 相似 ---")
        base = len(exact[:8]) + 1
        for i, s in enumerate(similar[:6], base):
            reasons = "；".join(s.get("similar_reasons", []))
            lines.append(f"  {i}. {s['name']}({s['code']}) ¥{s['price']:.2f} (相似) {reasons}")
            lines.append(f"     换手率{s['turnover_rate']:.1f}% | 量比{s['volume_ratio']:.1f}")

    if not exact and not similar:
        lines.append("  今天没有符合或接近条件的票")

    lines.append("")
    if news:
        lines.append("【今日要闻】")
        for n in news[:3]:
            lines.append(f"  - {n}")
        lines.append("")
    lines.append("以上为市场数据分析，不构成投资建议")
    return "\n".join(lines)


if __name__ == "__main__":
    core = Core()
    cfg = core.cfg.data
    strategy = cfg["strategy"]
    td = datasource.today_str()

    indices, idx_fresh = datasource.get_indices()
    all_stocks, scan_fresh = datasource.scan_market()
    st_name, exact, similar = screener.screen(all_stocks, strategy)
    watch_data = core.watchlist.get_all_data()
    news = datasource.get_news()

    report = build_report(td, indices, watch_data, exact, similar, st_name, news)

    sc = cfg.get("notifications", {})
    if any(sc.get(ch, {}).get("enabled") for ch in sc):
        title = f"克克晨报 {td} | 上证{indices.get('上证指数',{}).get('price','?'):.0f}"
        notifier.push_all(sc, title, report)
        print("  微信已推送 ✅")

    try:
        print(report[:2000])
    except Exception:
        print("  (终端编码限制，完整报告已推微信)")
