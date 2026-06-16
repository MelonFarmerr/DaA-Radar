import os, threading, time
from .config_mgr import ConfigManager
from .watchlist_mgr import WatchlistManager
from .strategy_mgr import StrategyManager, PRESETS
from . import datasource, screener, notifier


class Core:
    def __init__(self, config_path=None):
        datasource.ensure_ready()
        self.cfg = ConfigManager(config_path)
        self.watchlist = WatchlistManager(self.cfg)
        self.strategy = StrategyManager(self.cfg)
        self._running = False
        self.last_results = None
        self.last_run_time = None

        self.on_log = None
        self.on_progress = None
        self.on_status = None
        self.on_done = None

    # ── 自选股 ──
    def search_stock(self, keyword):
        return self.watchlist.search(keyword)

    def add_stock(self, code, cost=0):
        return self.watchlist.add(code, cost)

    def remove_stock(self, code):
        self.watchlist.remove(code)

    # ── 策略 ──
    @property
    def preset_strategies(self):
        return self.strategy.presets

    @property
    def current_strategy_key(self):
        return self.strategy.current_key

    @property
    def current_strategy_name(self):
        return self.strategy.current_name

    def switch_strategy(self, key):
        return self.strategy.switch(key)

    def parse_prompt(self, prompt):
        return self.strategy.parse_prompt(prompt)

    def describe_filters(self, filters):
        return self.strategy.describe(filters)

    def save_custom_strategy(self, name, desc, filters):
        return self.strategy.save_custom(name, desc, filters)

    @property
    def fields_meta(self):
        return self.strategy.fields_meta

    # ── 通知 ──
    def test_notify(self, channel=None):
        settings = self.cfg.get("notifications", {})
        if channel:
            settings = {channel: settings.get(channel, {})}
        return notifier.push_all(settings, "大A雷达 · 测试",
                                 "如果你看到这条消息，说明通知配置成功 ✅")

    def install_schedule(self, time_str=None, days=None):
        if time_str is None:
            time_str = self.cfg.get("schedule", {}).get("time", "10:00")
        if days is None:
            days = self.cfg.get("schedule", {}).get("days", [1, 2, 3, 4, 5])
        self.cfg.update({"schedule": {"enabled": True, "time": time_str, "days": days}})
        notifier.install_scheduled_task(
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "briefing.py"),
            time_str, days
        )

    def uninstall_schedule(self):
        notifier.uninstall_scheduled_task()
        self.cfg.set("schedule", self.cfg.get("schedule", {}).copy())
        self.cfg._data["schedule"]["enabled"] = False
        self.cfg.save()

    # ── 运行 ──
    def run_screening(self):
        if self._running:
            return
        self._running = True
        self._emit_status("● 运行中", "#3b82f6")

        def _run():
            try:
                self._emit_log("", clear=True)
                td = datasource.today_str()
                self._emit_log(f"--- {td}  策略: {self.strategy.current_name} ---")

                self._emit_progress(1, 4, "拉取大盘数据…")
                indices, idx_fresh = datasource.get_indices()
                if not idx_fresh:
                    self._emit_log("⚠️ 大盘数据来自缓存，可能不是最新")
                for n, i in indices.items():
                    self._emit_log(f"  {n}: {i['price']:.2f} ({i['change_pct']:+.2f}%)")

                self._emit_progress(2, 4, "扫描全市场…")
                all_stocks, scan_fresh = datasource.scan_market()
                if not scan_fresh:
                    self._emit_log("⚠️ 市场数据来自缓存，可能不是最新")
                if len(all_stocks) == 0:
                    self._emit_log("⚠️ 全市场扫描暂时不可用（网络节点问题），请稍后重试")
                    self._emit_log("  自选股行情仍可正常查看")
                else:
                    self._emit_log(f"  已获取 {len(all_stocks)} 只股票")

                self._emit_progress(3, 4, "执行策略筛选…")
                st_name, exact, similar = screener.screen(all_stocks, self.strategy.current_key,
                                                          ma_checker=None)
                self._emit_log(f"  完全符合 {len(exact)} 只，相似 {len(similar)} 只")

                self._emit_progress(4, 4, "获取自选股行情…")
                watch_data = self.watchlist.get_all_data()

                self.news = datasource.get_news()

                self.last_results = {
                    "date": td, "indices": indices, "idx_fresh": idx_fresh,
                    "watch_stocks": watch_data,
                    "exact": exact, "similar": similar,
                    "strategy_name": st_name, "scan_fresh": scan_fresh,
                    "news": self.news,
                }
                self.last_run_time = td

                self._emit_log("\n--- 完成 ---")

                sc = self.cfg.get("notifications", {})
                if any(sc.get(ch, {}).get("enabled") for ch in sc):
                    title = f"大A雷达 {td} | 符合{len(exact)}只 相似{len(similar)}只"
                    body = f"{st_name}: 完全符合{len(exact)}只, 相似{len(similar)}只"
                    if watch_data:
                        body += "\n\n【自选股】"
                        shown = 0
                        for w in watch_data:
                            if not w.get("price") or shown >= 3:
                                break
                            pct = w.get("change_pct", 0)
                            sign = "+" if pct >= 0 else ""
                            body += f"\n  {w.get('name','')} ¥{w.get('price',0):.2f} {sign}{pct:.2f}%"
                            c = w.get("cost", 0)
                            if c and w.get("price"):
                                pl = (w["price"] - c) / c * 100
                                body += f"  盈亏{pl:+.1f}%"
                            shown += 1
                        body += "\n  （详情请到应用界面查看）"
                    if self.news:
                        body += f"\n\n今日要闻: {self.news[0]}"
                    notifier.push_all(sc, title, body)
                    self._emit_log("📱 通知已推送")

                self._emit_done(self.last_results)

            except Exception as e:
                self._emit_log(f"❌ 错误: {e}")
                self._emit_status("● 出错", "#ef4444")
            finally:
                self._running = False

        threading.Thread(target=_run, daemon=True).start()

    def _emit_log(self, msg, clear=False):
        if self.on_log:
            self.on_log(msg, clear)

    def _emit_progress(self, step, total, label):
        if self.on_progress:
            self.on_progress(step, total, label)

    def _emit_status(self, text, color):
        if self.on_status:
            self.on_status(text, color)

    def _emit_done(self, results):
        if self.on_done:
            self.on_done(results)

    # ── 刷新股票列表 ──
    def refresh_stock_index(self):
        return datasource.refresh_index()

    # ── 自动刷新 ──
    def start_auto_refresh(self, interval_sec=30):
        if hasattr(self, '_refresh_timer') and self._refresh_timer:
            return
        self._refresh_running = True
        self._refresh_timer = threading.Thread(target=self._auto_refresh_loop,
                                               args=(interval_sec,), daemon=True)
        self._refresh_timer.start()

    def stop_auto_refresh(self):
        self._refresh_running = False
        self._refresh_timer = None

    def _auto_refresh_loop(self, interval_sec):
        while getattr(self, '_refresh_running', False):
            try:
                indices, idx_fresh = datasource.get_indices()
                watch_data = self.watchlist.get_all_data(cache_ttl=5)
                if self.on_done:
                    self.on_done({
                        "date": datasource.today_str(), "indices": indices,
                        "idx_fresh": idx_fresh, "watch_stocks": watch_data,
                        "exact": [], "similar": [], "strategy_name": "", "scan_fresh": True,
                        "news": [], "_auto": True,
                    })
            except Exception:
                pass
            time.sleep(interval_sec)
