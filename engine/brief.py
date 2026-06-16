"""每日简报 — 模板引擎生成自然语言摘要"""
from . import datasource


def build(indices, watch_stocks, exact, similar, strategy_name):
    parts = []

    # 大盘概况
    sh = indices.get("上证指数", {})
    sz = indices.get("深证成指", {})
    if sh and sz:
        sh_up = sh.get("change_pct", 0) >= 0
        sz_up = sz.get("change_pct", 0) >= 0
        if sh_up and sz_up:
            parts.append("今日A股整体走强，沪市深市双双飘红。")
        elif not sh_up and not sz_up:
            parts.append("今日A股整体承压，沪深两市均有回落。")
        else:
            direction = "沪强深弱" if sh_up else "深强沪弱"
            parts.append(f"今日市场分化，{direction}格局。")

    # 自选股
    if watch_stocks:
        valid = [w for w in watch_stocks if w.get("price")]
        if valid:
            up_count = sum(1 for w in valid if w.get("change_pct", 0) > 0)
            total = len(valid)
            if up_count >= total * 0.7:
                parts.append(f"自选股表现亮眼，{up_count}/{total}只上涨。")
            elif up_count <= total * 0.3:
                parts.append(f"自选股多数走低，仅{up_count}/{total}只上涨。")
            else:
                parts.append(f"自选股涨跌互现，{up_count}/{total}只上涨。")

            top = max(valid, key=lambda w: w.get("change_pct", 0))
            worst = min(valid, key=lambda w: w.get("change_pct", 0))
            if top.get("change_pct", 0) > 3:
                parts.append(f"其中{top.get('name','')}表现突出，涨幅{top['change_pct']:+.1f}%。")
            if worst.get("change_pct", 0) < -3:
                parts.append(f"{worst.get('name','')}回调较大，跌幅{worst['change_pct']:+.1f}%。")
    else:
        parts.append("今日暂无自选股数据。")

    # 筛选结果
    n_exact = len(exact)
    n_sim = len(similar)
    if n_exact > 0:
        top_name = exact[0].get("name", "") if exact else ""
        parts.append(f"「{strategy_name}」策略匹配到{n_exact}只标的" + (f"，其中{top_name}领涨" if top_name else "") + "。")
        if n_sim > 0:
            parts.append(f"另有{n_sim}只相似标的接近筛选条件。")
    elif n_sim > 0:
        parts.append(f"「{strategy_name}」策略暂无完全匹配，但{n_sim}只标的接近条件。")
    else:
        parts.append(f"「{strategy_name}」策略今日无匹配标的。")

    return "".join(parts)


def build_title(indices):
    sh = indices.get("上证指数", {})
    if sh:
        sign = "+" if sh.get("change_pct", 0) >= 0 else ""
        return f"A股日报 | 上证{sh.get('price','?')}{sign}{sh.get('change_pct',0):.2f}%"
    return "A股日报"
