#!/usr/bin/env python3
import os, sys, json, time, re
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from engine.core import Core
from engine.strategy_mgr import STRAT_FIELDS

import customtkinter as ctk
from tkinter import messagebox
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

A = "#3b82f6"; AH = "#60a5fa"; D = "#ef4444"; G = "#22c55e"; Y = "#eab308"
B0 = "#0b0f19"; B1 = "#131927"; B2 = "#1a2235"; T = "#e2e8f0"; M = "#64748b"
FH = ("Microsoft YaHei UI", 13, "bold")
FB = ("Microsoft YaHei UI", 12)
FS = ("Microsoft YaHei UI", 11)
FM = ("Consolas", 10)
FT = ("Microsoft YaHei UI", 15, "bold")
FL = ("Microsoft YaHei UI", 17, "bold")

APP_NAME = "大A雷达 v1.0"
WIN_W, WIN_H = 900, 700


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.core = Core()
        self._cards = {}
        self._sel = None
        self._search_results = []
        self._search_idx = 0
        self._custom_fields = {}
        self._last_results = None

        self.title(APP_NAME)
        self.geometry(f"{WIN_W}x{WIN_H}")
        self.minsize(720, 540)
        self.configure(fg_color=B0)
        self._center()
        self._bind_core()
        self._build()
        self._show_welcome()

    def _center(self):
        self.update_idletasks()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"{WIN_W}x{WIN_H}+{(sw - WIN_W) // 2}+{(sh - WIN_H) // 2}")

    def _bind_core(self):
        self.core.on_log = lambda msg, clear: self.after(0, self._on_log, msg, clear)
        self.core.on_progress = lambda s, t, l: self.after(0, self._on_progress, s, t, l)
        self.core.on_status = lambda txt, clr: self.after(0, self._on_status, txt, clr)
        self.core.on_done = lambda r: self.after(0, self._on_done, r)

    # ═══════════ BUILD ═══════════
    def _build(self):
        h = ctk.CTkFrame(self, fg_color="transparent")
        h.pack(fill="x", padx=28, pady=(18, 2))
        ctk.CTkLabel(h, text=APP_NAME, font=("Microsoft YaHei UI", 18, "bold"), text_color=A).pack(side="left")
        self._st = ctk.CTkLabel(h, text="● 就绪", font=FS, text_color=M)
        self._st.pack(side="left", padx=12)
        ctk.CTkLabel(h, text="© MelonFarmerr  ·  数据仅供参考 不构成投资建议", font=("Microsoft YaHei UI", 10), text_color="#475569").pack(side="right")

        self._tabs = ctk.CTkTabview(self, fg_color=B0,
                                     segmented_button_fg_color=B1, segmented_button_selected_color=A,
                                     segmented_button_unselected_color=B1,
                                     segmented_button_selected_hover_color=AH, text_color=T, border_width=0)
        self._tabs.pack(fill="both", expand=True, padx=24, pady=2)
        for t in ["运  行", "自选股", "策  略", "通  知"]:
            self._tabs.add(t)
        self._tabs.set("运  行")
        self._build_run()
        self._build_watch()
        self._build_strat()
        self._build_notify()

    # ═══════════ 运行 ═══════════
    def _build_run(self):
        t = self._tabs.tab("运  行")

        top = ctk.CTkFrame(t, fg_color=B1, corner_radius=12)
        top.pack(fill="x", padx=4, pady=(6, 4))
        i1 = ctk.CTkFrame(top, fg_color="transparent")
        i1.pack(fill="x", padx=16, pady=(12, 4))
        ctk.CTkLabel(i1, text="当前:", font=FS, text_color=M).pack(side="left")
        self._lbl_s = ctk.CTkLabel(i1, text="", font=FH, text_color=A)
        self._lbl_s.pack(side="left", padx=6)
        self._lbl_w = ctk.CTkLabel(i1, text="", font=FS, text_color=M)
        self._lbl_w.pack(side="left", padx=12)

        bar = ctk.CTkFrame(top, fg_color="transparent")
        bar.pack(fill="x", padx=16, pady=(4, 12))
        self._br = ctk.CTkButton(bar, text="▶  开  始", font=FT, fg_color=A, hover_color=AH,
                                  text_color="#fff", corner_radius=10, height=42, width=150,
                                  command=self._do_run)
        self._br.pack(side="left")
        self._prog_bar = ctk.CTkProgressBar(bar, fg_color=B2, progress_color=A, height=6, width=200)
        self._prog_bar.pack(side="left", padx=14)
        self._prog_bar.set(0)
        self._prog_lbl = ctk.CTkLabel(bar, text="", font=FS, text_color=M)
        self._prog_lbl.pack(side="left")
        self._lbl_last = ctk.CTkLabel(bar, text="", font=FS, text_color=M)
        self._lbl_last.pack(side="right")
        self._refresh_info()

        self._result_area = ctk.CTkScrollableFrame(t, fg_color="transparent",
                                                    scrollbar_button_color="#334155",
                                                    scrollbar_button_hover_color="#475569")
        ctk.CTkLabel(self._result_area, text="点击「开始」查看行情与筛选结果",
                      font=FB, text_color=M).pack(pady=40)
        self._result_area.pack(fill="both", expand=True, padx=4, pady=(2, 6))

        lc = ctk.CTkFrame(t, fg_color=B1, corner_radius=10)
        lc.pack(fill="x", padx=4, pady=(2, 4))
        self._log = ctk.CTkTextbox(lc, font=FM, fg_color="#060a14", text_color="#64748b",
                                    border_width=0, corner_radius=8, height=80)
        self._log.pack(fill="x", padx=10, pady=8)

    def _show_welcome(self):
        if not self.core.last_run_time:
            self._lbl_last.configure(text="还没有运行过")

    def _refresh_info(self):
        self._lbl_s.configure(text=self.core.current_strategy_name)
        cs = [w["code"] for w in self.core.watchlist.list]
        self._lbl_w.configure(text="自选: " + (", ".join(cs) if cs else "无"))
        if self.core.last_run_time:
            self._lbl_last.configure(text=f"上次: {self.core.last_run_time}")

    def _do_run(self):
        self._log.delete("1.0", "end")
        self._prog_bar.set(0)
        self._prog_lbl.configure(text="")
        self._br.configure(text="...", state="disabled")
        self.core.run_screening()

    def _on_log(self, msg, clear):
        if clear:
            self._log.delete("1.0", "end")
        self._log.insert("end", msg + "\n")
        self._log.see("end")

    def _on_progress(self, step, total, label):
        self._prog_bar.set(step / total if total else 0)
        self._prog_lbl.configure(text=label)

    def _on_status(self, text, color):
        self._st.configure(text=text, text_color=color)

    def _on_done(self, results):
        self._prog_bar.set(1)
        self._prog_lbl.configure(text="✅ 完成")
        self._st.configure(text="● 就绪", text_color=M)
        self._br.configure(text="▶  开  始", state="normal")
        self._refresh_info()
        self._last_results = results
        self._show_results(results)

    def _show_results(self, results):
        self._result_area.pack_forget()
        for w in self._result_area.winfo_children():
            w.destroy()

        if not results:
            self._result_area.pack(fill="both", expand=True, padx=4, pady=(2, 6))
            return

        self._result_area.pack(fill="both", expand=True, padx=4, pady=(2, 6))

        if results.get("idx_fresh") is False or results.get("scan_fresh") is False:
            ctk.CTkLabel(self._result_area, text="⚠️ 数据来自缓存，可能不是最新",
                          font=FS, text_color=Y).pack(anchor="w", padx=8, pady=2)

        watch = results.get("watch_stocks", [])
        if watch:
            ctk.CTkLabel(self._result_area, text="📌 自选股", font=FH, text_color=A).pack(anchor="w", padx=8, pady=(8, 2))
            for s in watch:
                if not s.get("price"):
                    continue
                c = s.get("cost", 0)
                frm = ctk.CTkFrame(self._result_area, fg_color=B2, corner_radius=8)
                frm.pack(fill="x", pady=2, padx=4)
                inn = ctk.CTkFrame(frm, fg_color="transparent")
                inn.pack(fill="both", expand=True, padx=12, pady=8)
                ctk.CTkLabel(inn, text=s.get("name", ""), font=FH, text_color=T).pack(side="left")
                ctk.CTkLabel(inn, text=s.get("code", ""), font=FS, text_color=M).pack(side="left", padx=8)
                pct = s.get("change_pct", 0)
                clr = G if pct >= 0 else D
                ctk.CTkLabel(inn, text=f"¥{s.get('price',0):.2f}  {pct:+.2f}%", font=FB,
                              text_color=clr).pack(side="right")
                if c and s.get("price"):
                    pl = (s["price"] - c) / c * 100
                    ctk.CTkLabel(inn, text=f"盈亏 {pl:+.1f}%", font=FS,
                                  text_color=G if pl >= 0 else D).pack(side="right", padx=12)

        exact = results.get("exact", [])
        similar = results.get("similar", [])
        if exact:
            total = len(exact)
            shown = min(total, 50)
            label = f"📋 完全符合  {total} 只"
            if total > 50:
                label += f" (显示前{shown}只)"
            ctk.CTkLabel(self._result_area, text=label,
                          font=FH, text_color=G).pack(anchor="w", padx=8, pady=(12, 2))
            for s in exact[:shown]:
                self._result_card(s, G)

        if similar:
            total = len(similar)
            shown = min(total, 30)
            label = f"📎 相似  {total} 只"
            if total > 30:
                label += f" (显示前{shown}只)"
            ctk.CTkLabel(self._result_area, text=label,
                          font=FH, text_color=Y).pack(anchor="w", padx=8, pady=(10, 2))
            for s in similar[:shown]:
                self._result_card(s, Y)

        if not exact and not similar:
            ctk.CTkLabel(self._result_area, text="今天没有符合或接近条件的票",
                          font=FB, text_color=M).pack(pady=16)

    def _result_card(self, s, accent):
        frm = ctk.CTkFrame(self._result_area, fg_color=B2, corner_radius=8)
        frm.pack(fill="x", pady=2, padx=4)
        inn = ctk.CTkFrame(frm, fg_color="transparent")
        inn.pack(fill="both", expand=True, padx=12, pady=8)
        ctk.CTkLabel(inn, text=f"{s.get('name','')}  {s.get('code','')}", font=FH, text_color=T).pack(anchor="w")
        row = ctk.CTkFrame(inn, fg_color="transparent")
        row.pack(fill="x", pady=(2, 0))
        pct = s.get("change_pct", 0)
        ctk.CTkLabel(row, text=f"¥{s.get('price',0):.2f}  {pct:+.2f}%", font=FB,
                      text_color=G if pct >= 0 else D).pack(side="left")
        ctk.CTkLabel(row, text=f"换手{s.get('turnover_rate',0):.1f}%  量比{s.get('volume_ratio',0):.1f}",
                      font=FS, text_color=M).pack(side="left", padx=10)
        tags = []
        if s.get("ma_status") == "aligned":
            tags.append("均线多头")
        if s.get("macd") and s["macd"].get("status") == "golden_cross":
            tags.append("MACD金叉")
        if s.get("kdj") and s["kdj"].get("status") == "golden_cross":
            tags.append("KDJ金叉")
        if tags:
            ctk.CTkLabel(row, text="  ".join(tags), font=FS, text_color=A).pack(side="left", padx=4)
        if s.get("similar_reasons"):
            ctk.CTkLabel(inn, text=" | ".join(s["similar_reasons"]), font=FS, text_color=M).pack(anchor="w", pady=(1, 0))

    # ═══════════ 自选股 ═══════════
    def _build_watch(self):
        t = self._tabs.tab("自选股")
        c = ctk.CTkFrame(t, fg_color=B1, corner_radius=12)
        c.pack(fill="x", padx=4, pady=(6, 4))
        ctk.CTkLabel(c, text="搜索股票名称或代码", font=FH, text_color=T).pack(anchor="w", padx=16, pady=(12, 4))

        sr = ctk.CTkFrame(c, fg_color="transparent")
        sr.pack(fill="x", padx=16, pady=(0, 2))
        self._we = ctk.CTkEntry(sr, font=FB, fg_color=B2, border_width=0, height=34,
                                 placeholder_text="例如: 茅台 / 600519")
        self._we.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self._we.bind("<KeyRelease>", self._on_search_type)
        self._we.bind("<Return>", self._on_search_enter)
        self._we.bind("<Down>", self._on_search_down)
        self._we.bind("<Up>", self._on_search_up)
        ctk.CTkButton(sr, text="＋ 添加", font=FB, fg_color=A, hover_color=AH,
                       corner_radius=8, height=34, width=80, command=self._do_add).pack(side="left")

        cr = ctk.CTkFrame(c, fg_color="transparent")
        cr.pack(fill="x", padx=16, pady=(2, 10))
        ctk.CTkLabel(cr, text="成本价 (选填):", font=FS, text_color=M).pack(side="left", padx=(0, 4))
        self._wc = ctk.CTkEntry(cr, width=80, font=FB, fg_color=B2, border_width=0, height=28, placeholder_text="¥")
        self._wc.pack(side="left")

        self._drop = ctk.CTkFrame(c, fg_color="#0f172a", corner_radius=8)

        lc = ctk.CTkFrame(t, fg_color=B1, corner_radius=12)
        lc.pack(fill="both", expand=True, padx=4, pady=(2, 6))
        self._cs = ctk.CTkScrollableFrame(lc, fg_color="transparent",
                                           scrollbar_button_color="#334155",
                                           scrollbar_button_hover_color="#475569", height=280)
        self._cs.pack(fill="both", expand=True, padx=8, pady=8)
        self._watch_cards()

    def _on_search_type(self, event):
        if hasattr(self, '_search_timer') and self._search_timer:
            self.after_cancel(self._search_timer)
        self._search_timer = self.after(250, self._do_search)

    def _do_search(self):
        kw = self._we.get().strip()
        self._drop.pack_forget()
        if len(kw) < 1:
            self._search_results = []
            return
        self._search_results = self.core.search_stock(kw)
        self._search_idx = 0
        if not self._search_results:
            return
        for w in self._drop.winfo_children():
            w.destroy()
        self._drop.pack(fill="x", padx=16, pady=(0, 4))
        for i, s in enumerate(self._search_results[:8]):
            lbl = ctk.CTkLabel(self._drop, text=f"{s['code']}  {s['name']}",
                                font=FB, text_color=T, anchor="w", padx=12, pady=5,
                                fg_color="#0f172a")
            lbl.pack(fill="x")
            lbl.bind("<Button-1>", lambda e, idx=i: self._pick_search(idx))
        self._highlight_search()

    def _on_search_enter(self, event):
        if self._search_results and 0 <= self._search_idx < len(self._search_results):
            self._we.delete(0, "end")
            self._we.insert(0, self._search_results[self._search_idx]["code"])
            self._drop.pack_forget()
            self._search_results = []
            self._do_add()
        else:
            self._do_add()

    def _on_search_down(self, event):
        if self._search_results:
            self._search_idx = min(self._search_idx + 1, len(self._search_results) - 1)
            self._highlight_search()

    def _on_search_up(self, event):
        if self._search_results:
            self._search_idx = max(self._search_idx - 1, 0)
            self._highlight_search()

    def _highlight_search(self):
        for i, w in enumerate(self._drop.winfo_children()):
            w.configure(fg_color="#1e3a5f" if i == self._search_idx else "#0f172a")

    def _pick_search(self, idx):
        s = self._search_results[idx]
        self._we.delete(0, "end")
        self._we.insert(0, s["code"])
        self._drop.pack_forget()
        self._search_results = []

    def _do_add(self):
        code = self._we.get().strip()
        if not code:
            return
        cost = self._wc.get().strip()
        self.core.add_stock(code, float(cost) if cost else 0)
        self._we.delete(0, "end")
        self._wc.delete(0, "end")
        self._watch_cards()
        self._refresh_info()

    def _watch_cards(self):
        for f in self._cards.values():
            f.destroy()
        self._cards.clear()
        self.update_idletasks()
        watch_data = self.core.watchlist.get_all_data()
        for info in watch_data:
            cd = info.get("code", "")
            nm = info.get("name", cd)
            price = info.get("price", 0)
            pct = info.get("change_pct", 0)
            cost = info.get("cost", 0)
            fresh = info.get("_fresh", False)

            frm = ctk.CTkFrame(self._cs, fg_color=B2, corner_radius=8, height=52)
            frm.pack(fill="x", pady=2, padx=2)
            frm.pack_propagate(False)
            inn = ctk.CTkFrame(frm, fg_color="transparent")
            inn.pack(fill="both", expand=True, padx=12)

            left = ctk.CTkFrame(inn, fg_color="transparent")
            left.pack(side="left")
            ctk.CTkLabel(left, text=f"{nm}  {cd}", font=FH, text_color=T).pack(anchor="w")
            sub = ctk.CTkFrame(left, fg_color="transparent")
            sub.pack(anchor="w", pady=(1, 0))
            pct_clr = G if pct >= 0 else D
            ctk.CTkLabel(sub, text=f"¥{price:.2f}  {pct:+.2f}%", font=FB, text_color=pct_clr).pack(side="left")
            if not fresh:
                ctk.CTkLabel(sub, text=" ·缓存", font=FS, text_color=Y).pack(side="left")

            right = ctk.CTkFrame(inn, fg_color="transparent")
            right.pack(side="right")
            if cost and price:
                pl = (price - cost) / cost * 100
                pl_clr = G if pl >= 0 else D
                ctk.CTkLabel(right, text=f"成本¥{cost:.2f}  盈亏{pl:+.1f}%", font=FB, text_color=pl_clr).pack(side="right")

            ctk.CTkButton(inn, text="✕", font=FS, fg_color="transparent", hover_color=D,
                           corner_radius=4, height=24, width=24,
                           command=lambda c=cd: self._do_del(c)).pack(side="right", padx=(4, 0))

            for wg in (frm, inn, left, sub) + tuple(sub.winfo_children()) + tuple(left.winfo_children()):
                if not isinstance(wg, ctk.CTkButton):
                    wg.bind("<Button-1>", lambda e, c=cd: self._pick_stock(c))

            self._cards[cd] = frm
        self._cs.update_idletasks()
        self.update_idletasks()

    def _pick_stock(self, cd):
        if self._sel == cd:
            self._cards[cd].configure(fg_color=B2)
            self._sel = None
            return
        if self._sel and self._sel in self._cards:
            self._cards[self._sel].configure(fg_color=B2)
        self._cards[cd].configure(fg_color="#1e3a5f")
        self._sel = cd

    def _do_del(self, cd):
        w = next((x for x in self.core.watchlist.list if x["code"] == cd), None)
        nm = w["name"] if w else cd
        if not messagebox.askyesno("确认", f"确定要删除 {nm} ({cd}) 吗？"):
            return
        self.core.remove_stock(cd)
        if self._sel == cd:
            self._sel = None
        self._watch_cards()
        self._refresh_info()

    # ═══════════ 策略 ═══════════
    def _build_strat(self):
        t = self._tabs.tab("策  略")
        self._strat_content = ctk.CTkScrollableFrame(t, fg_color="transparent",
                                                      scrollbar_button_color="#334155",
                                                      scrollbar_button_hover_color="#475569")
        self._strat_content.pack(fill="both", expand=True, padx=4, pady=4)
        self._build_strat_view()

    def _build_strat_view(self):
        for w in self._strat_content.winfo_children():
            w.destroy()

        presets = self.core.preset_strategies
        cur_key = self.core.current_strategy_key

        ctk.CTkLabel(self._strat_content, text="选择策略", font=FH, text_color=T).pack(anchor="w", padx=8, pady=(8, 4))

        for p in presets:
            active = p["key"] == cur_key
            clr = A if active else B1
            card = ctk.CTkFrame(self._strat_content, fg_color=clr, corner_radius=8)
            card.pack(fill="x", pady=2, padx=4)
            inner = ctk.CTkFrame(card, fg_color="transparent")
            inner.pack(fill="both", expand=True, padx=14, pady=8)
            ctk.CTkLabel(inner, text=p["name"], font=FH,
                          text_color="#fff" if active else T).pack(anchor="w")
            ctk.CTkLabel(inner, text=p["desc"], font=FS,
                          text_color="#cbd5e1" if active else M).pack(anchor="w")
            if not active:
                for ch in (inner,) + tuple(inner.winfo_children()):
                    ch.bind("<Button-1>", lambda e, k=p["key"]: self._do_switch_strat(k))
                card.bind("<Button-1>", lambda e, k=p["key"]: self._do_switch_strat(k))

        # Custom strategy card
        custom_active = cur_key == "custom"
        custom_clr = A if custom_active else B1
        custom_card = ctk.CTkFrame(self._strat_content, fg_color=custom_clr, corner_radius=8)
        custom_card.pack(fill="x", pady=2, padx=4)
        custom_inner = ctk.CTkFrame(custom_card, fg_color="transparent")
        custom_inner.pack(fill="both", expand=True, padx=14, pady=8)
        custom_desc = self.core.strategy.describe(self._custom_fields) if self._custom_fields else "未设置条件"
        ctk.CTkLabel(custom_inner, text="自定义策略", font=FH,
                      text_color="#fff" if custom_active else T).pack(anchor="w")
        self._custom_card_label = ctk.CTkLabel(custom_inner, text=custom_desc, font=FS,
                                                text_color="#cbd5e1" if custom_active else M)
        self._custom_card_label.pack(anchor="w")
        if not custom_active:
            for ch in (custom_inner,) + tuple(custom_inner.winfo_children()):
                ch.bind("<Button-1>", lambda e: self._toggle_custom())
            custom_card.bind("<Button-1>", lambda e: self._toggle_custom())

        self._custom_expanded = custom_active
        self._custom_frame = ctk.CTkFrame(self._strat_content, fg_color=B1, corner_radius=10)
        if self._custom_expanded:
            self._build_custom_form()

    def _do_switch_strat(self, key):
        self.core.switch_strategy(key)
        self._build_strat_view()
        self._refresh_info()

    def _toggle_custom(self):
        self._custom_expanded = not self._custom_expanded
        if self._custom_expanded:
            self._build_custom_form()
        else:
            self._custom_frame.pack_forget()

    def _build_custom_form(self):
        for w in self._custom_frame.winfo_children():
            w.destroy()
        self._custom_frame.pack(fill="x", padx=4, pady=(2, 4))
        self._cf_vars = {}

        sections = [
            ("📊 行情", [
                ("pair", "股价", "price_min", "price_max", "元"),
                ("pair", "涨跌幅", "change_pct_min", "change_pct_max", "%"),
                ("pair", "换手率", "turnover_min", "turnover_max", "%"),
                ("pair", "量比", "volume_ratio_min", "volume_ratio_max", ""),
                ("single", "成交额 ≥", "turnover_amt_min", "亿"),
                ("single", "振幅 ≤", "amplitude_max", "%"),
            ]),
            ("💰 基本面", [
                ("pair", "市值", "market_cap_min", "market_cap_max", "亿"),
                ("pair", "PE", "pe_min", "pe_max", ""),
                ("pair", "PB", "pb_min", "pb_max", ""),
                ("single", "ROE ≥", "roe_min", "%"),
            ]),
            ("🏢 板块 (默认全选, 取消即排除)", [
                ("bool", "沪市主板 (60xxxx)", "board_sh_main"),
                ("bool", "深市主板 (00xxxx)", "board_sz_main"),
                ("bool", "创业板 (30xxxx)", "board_chi_next"),
                ("bool", "科创板 (688xxx)", "board_star"),
                ("bool", "北交所 (8x/4x)", "board_bse"),
                ("bool", "包含 ST 股", "include_st"),
            ]),
        ]

        for sname, fields in sections:
            ctk.CTkLabel(self._custom_frame, text=sname, font=FH, text_color=A).pack(anchor="w", padx=16, pady=(10, 2))

            # Build pairs in a grid: 2 pairs per row
            pairs_in_row = []
            bools_in_row = []

            for fdef in fields:
                ftype = fdef[0]

                if ftype == "pair":
                    pairs_in_row.append(fdef)
                    if len(pairs_in_row) == 2:
                        self._make_pair_row(pairs_in_row)
                        pairs_in_row = []
                elif ftype == "single":
                    pairs_in_row.append(fdef)
                    if len(pairs_in_row) == 2:
                        self._make_pair_row(pairs_in_row)
                        pairs_in_row = []
                elif ftype == "bool":
                    bools_in_row.append(fdef)
                    if len(bools_in_row) == 3:
                        self._make_bool_row(bools_in_row)
                        bools_in_row = []

            if pairs_in_row:
                self._make_pair_row(pairs_in_row)
            if bools_in_row:
                self._make_bool_row(bools_in_row)

        self._build_tech_tags()

        btns = ctk.CTkFrame(self._custom_frame, fg_color="transparent")
        btns.pack(fill="x", padx=16, pady=(12, 6))
        ctk.CTkButton(btns, text="🔄 全部清空", font=FB, fg_color=B2, hover_color="#475569",
                       corner_radius=8, height=34, command=self._cf_clear).pack(side="left")
        ctk.CTkButton(btns, text="💾 保存并应用", font=FH, fg_color=G, hover_color="#4ade80",
                       corner_radius=8, height=34, command=self._cf_save).pack(side="right", padx=8)
        ctk.CTkButton(btns, text="收起 ▲", font=FB, fg_color=B2, hover_color="#475569",
                       corner_radius=8, height=34, width=80, command=self._toggle_custom).pack(side="right")

        prompt_frame = ctk.CTkFrame(self._custom_frame, fg_color="transparent")
        prompt_frame.pack(fill="x", padx=16, pady=(0, 10))
        self._prompt_expanded = False
        self._prompt_btn = ctk.CTkButton(prompt_frame, text="不想填表？用大白话输入 ▼", font=FS,
                                          fg_color="transparent", hover_color="#232d42",
                                          text_color=M, command=self._toggle_prompt)
        self._prompt_btn.pack(anchor="w")
        self._prompt_area = ctk.CTkFrame(self._custom_frame, fg_color="transparent")

    def _make_pair_row(self, fdefs):
        row = ctk.CTkFrame(self._custom_frame, fg_color="transparent")
        row.pack(fill="x", padx=16, pady=2)
        for fdef in fdefs:
            ftype = fdef[0]
            if ftype == "pair":
                label, kmin, kmax, unit = fdef[1], fdef[2], fdef[3], fdef[4]
                pair = ctk.CTkFrame(row, fg_color="transparent")
                pair.pack(side="left", padx=(0, 24), pady=3)
                ctk.CTkLabel(pair, text=f"{label} ", font=FS, text_color=M).pack(side="left")
                e1 = ctk.CTkEntry(pair, font=FB, fg_color=B2, border_width=0, height=28, width=58)
                v1 = self._custom_fields.get(kmin, "")
                if v1: e1.insert(0, str(int(v1)) if isinstance(v1, float) and v1 == int(v1) else str(v1))
                e1.pack(side="left")
                e1.bind("<FocusOut>", lambda ev, k=kmin, e=e1: self._cf_set_num(k, e.get()))
                ctk.CTkLabel(pair, text=f" ~ {unit}", font=FS, text_color=M).pack(side="left")
                e2 = ctk.CTkEntry(pair, font=FB, fg_color=B2, border_width=0, height=28, width=58)
                v2 = self._custom_fields.get(kmax, "")
                if v2: e2.insert(0, str(int(v2)) if isinstance(v2, float) and v2 == int(v2) else str(v2))
                e2.pack(side="left")
                e2.bind("<FocusOut>", lambda ev, k=kmax, e=e2: self._cf_set_num(k, e.get()))
            elif ftype == "single":
                label, key, unit = fdef[1], fdef[2], fdef[3]
                pair = ctk.CTkFrame(row, fg_color="transparent")
                pair.pack(side="left", padx=(0, 24), pady=3)
                ctk.CTkLabel(pair, text=f"{label} ", font=FS, text_color=M).pack(side="left")
                e = ctk.CTkEntry(pair, font=FB, fg_color=B2, border_width=0, height=28, width=58)
                v = self._custom_fields.get(key, "")
                if v: e.insert(0, str(int(v)) if isinstance(v, float) and v == int(v) else str(v))
                e.pack(side="left")
                if unit:
                    ctk.CTkLabel(pair, text=f" {unit}", font=FS, text_color=M).pack(side="left")
                e.bind("<FocusOut>", lambda ev, k=key, ee=e: self._cf_set_num(k, ee.get()))

    def _make_bool_row(self, fdefs):
        row = ctk.CTkFrame(self._custom_frame, fg_color="transparent")
        row.pack(fill="x", padx=16, pady=2)
        _board_defaults = {"board_sh_main":True,"board_sz_main":True,"board_chi_next":True,
                           "board_star":True,"board_bse":True}
        for fdef in fdefs:
            label, key = fdef[1], fdef[2]
            default = _board_defaults.get(key, False)
            val = self._custom_fields.get(key, default)
            var = ctk.BooleanVar(value=val)
            cb = ctk.CTkCheckBox(row, text=label, variable=var, font=FS, text_color=T,
                                  fg_color=A, hover_color=AH, border_width=2, border_color="#475569")
            cb.pack(side="left", padx=(0, 20), pady=3)
            var.trace_add("write", lambda *a, k=key, v=var: self._cf_set_bool(k, v))
            self._cf_vars[key] = var

    def _toggle_prompt(self):
        self._prompt_expanded = not self._prompt_expanded
        if self._prompt_expanded:
            self._prompt_btn.configure(text="不想填表？用大白话输入 ▲")
            for w in self._prompt_area.winfo_children():
                w.destroy()
            self._prompt_area.pack(fill="x", padx=16, pady=(0, 8))
            ctk.CTkLabel(self._prompt_area, text="输入结构化条件，本地正则自动解析",
                          font=FS, text_color=M).pack(anchor="w")
            pr = ctk.CTkFrame(self._prompt_area, fg_color="transparent")
            pr.pack(fill="x", pady=(4, 0))
            self._nl = ctk.CTkEntry(pr, font=FB, fg_color=B2, border_width=0, height=34,
                                     placeholder_text="例如: 股价10-100元 换手>7% 非ST 非科创 均线多头")
            self._nl.pack(side="left", fill="x", expand=True, padx=(0, 8))
            self._nl.bind("<Return>", lambda e: self._do_parse())
            ctk.CTkButton(pr, text="解析", font=FB, fg_color=A, hover_color=AH,
                           corner_radius=8, height=34, width=70,
                           command=self._do_parse).pack(side="left")
            self._parse_result = ctk.CTkLabel(self._prompt_area, text="", font=FS, text_color=M)
            self._parse_result.pack(anchor="w", pady=(4, 0))
        else:
            self._prompt_btn.configure(text="不想填表？用大白话输入 ▼")
            self._prompt_area.pack_forget()

    def _do_parse(self):
        prompt = self._nl.get().strip()
        if not prompt:
            return
        result = self.core.parse_prompt(prompt)
        if result:
            self._custom_fields.update(result)
            self._parse_result.configure(text=f"解析完成: {self.core.describe_filters(result)}", text_color=G)
            self._build_custom_form()
        else:
            self._parse_result.configure(text="未能解析，请尝试: 股价10-100元 换手>7% 非ST", text_color=D)

    def _cf_set_bool(self, key, var):
        self._custom_fields[key] = var.get()

    def _cf_set_num(self, key, val):
        try:
            self._custom_fields[key] = float(val) if '.' in val else int(val)
        except ValueError:
            if not val.strip():
                self._custom_fields.pop(key, None)

    def _build_tech_tags(self):
        INDICATORS = ["5日均线","10日均线","20日均线","60日均线",
                      "均线排列","MACD","KDJ","放量突破","连续收阳","主力净流入"]
        COND_MAP = {
            "5日均线": ["多头 (价>MA5)","空头 (价<MA5)"],
            "10日均线": ["多头 (价>MA10)","空头 (价<MA10)"],
            "20日均线": ["多头 (价>MA20)","空头 (价<MA20)"],
            "60日均线": ["多头 (价>MA60)","空头 (价<MA60)"],
            "均线排列": ["多头排列 (MA多头)"],
            "MACD": ["金叉","死叉"],
            "KDJ": ["金叉","死叉"],
            "放量突破": ["放量突破"],
            "连续收阳": ["≥ N天"],
            "主力净流入": ["≥ N万"],
        }
        KEY_MAP = {
            ("5日均线","多头 (价>MA5)"): ("ma5_bull","5日多头"),
            ("5日均线","空头 (价<MA5)"): ("ma5_bear","5日空头"),
            ("10日均线","多头 (价>MA10)"): ("ma10_bull","10日多头"),
            ("10日均线","空头 (价<MA10)"): ("ma10_bear","10日空头"),
            ("20日均线","多头 (价>MA20)"): ("ma20_bull","20日多头"),
            ("20日均线","空头 (价<MA20)"): ("ma20_bear","20日空头"),
            ("60日均线","多头 (价>MA60)"): ("ma60_bull","60日多头"),
            ("60日均线","空头 (价<MA60)"): ("ma60_bear","60日空头"),
            ("均线排列","多头排列 (MA多头)"): ("ma_aligned","均线多头排列"),
            ("MACD","金叉"): ("macd_golden_cross","MACD金叉"),
            ("MACD","死叉"): ("macd_death_cross","MACD死叉"),
            ("KDJ","金叉"): ("kdj_golden_cross","KDJ金叉"),
            ("KDJ","死叉"): ("kdj_death_cross","KDJ死叉"),
            ("放量突破","放量突破"): ("breakout_volume","放量突破"),
        }

        ctk.CTkLabel(self._custom_frame, text="📈 技术形态 (双选添加)", font=FH, text_color=A).pack(anchor="w", padx=16, pady=(10,2))

        sel = ctk.CTkFrame(self._custom_frame, fg_color="transparent")
        sel.pack(fill="x", padx=16, pady=4)

        self._tech_ind = ctk.CTkOptionMenu(sel, values=INDICATORS, font=FB,
                                            fg_color=B2, button_color=A, button_hover_color=AH,
                                            dropdown_fg_color=B1, dropdown_text_color=T,
                                            dropdown_font=FS, width=130,
                                            command=self._on_tech_ind_change)
        self._tech_ind.pack(side="left", padx=(0,6))
        self._tech_ind.set("5日均线")

        self._tech_con = ctk.CTkOptionMenu(sel, values=COND_MAP["5日均线"], font=FB,
                                            fg_color=B2, button_color=A, button_hover_color=AH,
                                            dropdown_fg_color=B1, dropdown_text_color=T,
                                            dropdown_font=FS, width=170,
                                            command=self._on_tech_con_change)
        self._tech_con.pack(side="left", padx=(0,6))
        self._tech_con.set(COND_MAP["5日均线"][0])

        self._tech_extra = ctk.CTkEntry(sel, font=FB, fg_color=B2, border_width=0,
                                         height=30, width=50, placeholder_text="N")
        self._tech_extra_label = ctk.CTkLabel(sel, text="", font=FS, text_color=M)

        self._tech_cond_map = COND_MAP
        self._tech_key_map = KEY_MAP
        self._tech_indicators = INDICATORS

        ctk.CTkButton(sel, text="＋ 添加", font=FB, fg_color=A, hover_color=AH,
                       corner_radius=6, height=30, width=70,
                       command=self._tech_add).pack(side="left", padx=8)

        self._tech_tags_frame = ctk.CTkFrame(self._custom_frame, fg_color="transparent")
        self._tech_tags_frame.pack(fill="x", padx=16, pady=4)

        self._tech_tags = []
        for k, v in self._custom_fields.items():
            if v is True and k in ("ma_aligned","ma5_bull","ma5_bear","ma10_bull","ma10_bear",
                                    "ma20_bull","ma20_bear","ma60_bull","ma60_bear",
                                    "macd_golden_cross","macd_death_cross",
                                    "kdj_golden_cross","kdj_death_cross","breakout_volume"):
                for (ik, ck), (fk, label) in self._tech_key_map.items():
                    if fk == k:
                        self._tech_tags.append((fk, label))
                        break
            elif k in ("consecutive_up","main_inflow_min") and v:
                label = f"连续收阳 ≥{int(v)}天" if k == "consecutive_up" else f"主力净流入 ≥{int(v)}万"
                self._tech_tags.append((k, label))
        self._refresh_tech_tags()

    def _on_tech_ind_change(self, choice):
        conds = self._tech_cond_map[choice]
        self._tech_con.configure(values=conds)
        self._tech_con.set(conds[0])
        self._tech_extra.pack_forget()
        self._tech_extra_label.pack_forget()
        if choice in ("连续收阳","主力净流入"):
            self._tech_extra.pack(side="left", padx=(2,2))
            self._tech_extra_label.pack(side="left")
            self._tech_extra_label.configure(text="天" if choice=="连续收阳" else "万")

    def _on_tech_con_change(self, choice):
        pass

    def _tech_add(self):
        ind = self._tech_ind.get()
        con = self._tech_con.get()
        extra = self._tech_extra.get().strip() if self._tech_extra.winfo_ismapped() else ""

        if ind in ("连续收阳","主力净流入"):
            if not extra or not extra.isdigit():
                return
            n = int(extra)
            key = "consecutive_up" if ind == "连续收阳" else "main_inflow_min"
            if key in [t[0] for t in self._tech_tags]:
                return
            label = f"连续收阳 ≥{n}天" if ind == "连续收阳" else f"主力净流入 ≥{n}万"
            self._custom_fields[key] = n
            self._tech_tags.append((key, label))
            self._tech_extra.delete(0,"end")
        else:
            mapped = self._tech_key_map.get((ind, con))
            if not mapped:
                return
            key, label = mapped
            if key not in [t[0] for t in self._tech_tags]:
                self._custom_fields[key] = True
                self._tech_tags.append((key, label))
        self._refresh_tech_tags()

    def _tech_remove(self, idx):
        if idx < len(self._tech_tags):
            key = self._tech_tags[idx][0]
            self._tech_tags.pop(idx)
            if key in self._custom_fields:
                del self._custom_fields[key]
            self._refresh_tech_tags()

    def _refresh_tech_tags(self):
        for w in self._tech_tags_frame.winfo_children():
            w.destroy()
        for i, (key, label) in enumerate(self._tech_tags):
            tag = ctk.CTkFrame(self._tech_tags_frame, fg_color="#1e3a5f", corner_radius=6)
            tag.pack(side="left", padx=3, pady=3)
            inner = ctk.CTkFrame(tag, fg_color="transparent")
            inner.pack(fill="both", expand=True, padx=(10,2), pady=4)
            ctk.CTkLabel(inner, text=label, font=FS, text_color="#93c5fd").pack(side="left")
            btn = ctk.CTkButton(inner, text="✕", font=FS,
                                 fg_color="transparent", hover_color=D,
                                 corner_radius=3, width=20, height=20)
            btn.pack(side="left", padx=(4,2))
            btn.configure(command=lambda idx=i: self._tech_remove(idx))
        self._custom_frame.update_idletasks()

    def _cf_clear(self):
        self._custom_fields.clear()
        self._tech_tags = []
        self._build_custom_form()

    def _cf_save(self):
        desc = self.core.describe_filters(self._custom_fields) if self._custom_fields else "未设置条件"
        self.core.save_custom_strategy("自定义策略", desc, self._custom_fields)
        self._build_strat_view()
        self._refresh_info()
        self._tabs.set("运  行")

    def _cf_use(self):
        if not self._custom_fields:
            return
        desc = self.core.describe_filters(self._custom_fields)
        self.core.save_custom_strategy("自定义策略", desc, self._custom_fields)
        self._build_strat_view()
        self._refresh_info()
        self._tabs.set("运  行")

    # ═══════════ 通知 ═══════════
    def _build_notify(self):
        t = self._tabs.tab("通  知")
        sf = ctk.CTkScrollableFrame(t, fg_color="transparent",
                                     scrollbar_button_color="#334155",
                                     scrollbar_button_hover_color="#475569")
        sf.pack(fill="both", expand=True, padx=4, pady=4)

        ns = self.core.cfg.get("notifications", {})

        channels = [
            ("windows_toast", "💻 电脑弹窗 (Win10/11 通知栏)", "完全免费，无需任何配置", True, None),
            ("bark", "📱 iPhone (Bark)", "App Store 下载 Bark → 复制 Key 填进来", False, "Key"),
            ("dingtalk", "💬 钉钉机器人", "建群 → 智能群助手 → 添加机器人 → 复制 Webhook", False, "Webhook"),
            ("feishu", "🐦 飞书机器人", "飞书群 → 群机器人 → 添加 → 复制 Webhook", False, "Webhook"),
            ("server_chan", "💚 微信 (Server酱)", "注册 https://sct.ftqq.com/ → 绑定微信 → 复制 SendKey 填进来", False, "SendKey"),
        ]

        ctk.CTkLabel(sf, text="推送通道", font=FH, text_color=T).pack(anchor="w", padx=8, pady=(6, 6))

        for key, title, desc, default_on, placeholder in channels:
            card = ctk.CTkFrame(sf, fg_color=B1, corner_radius=8)
            card.pack(fill="x", pady=2, padx=4)
            inn = ctk.CTkFrame(card, fg_color="transparent")
            inn.pack(fill="both", expand=True, padx=14, pady=8)

            ch_cfg = ns.get(key, {})
            enabled = ch_cfg.get("enabled", default_on)
            var = ctk.BooleanVar(value=enabled)

            top_r = ctk.CTkFrame(inn, fg_color="transparent")
            top_r.pack(fill="x")
            ctk.CTkCheckBox(top_r, text=title, variable=var, font=FH, text_color=T,
                             fg_color=A, hover_color=AH, border_width=2, border_color="#475569",
                             command=lambda k=key, v=var: self._notif_toggle(k, v)).pack(side="left")
            test_btn = ctk.CTkButton(top_r, text="测试", font=FS, fg_color=B2, hover_color="#475569",
                           corner_radius=6, height=26, width=54,
                           command=lambda k=key: self._test_notif(k))
            test_btn.pack(side="right", padx=4)
            setattr(self, f"_notif_btn_{key}", test_btn)

            ctk.CTkLabel(inn, text=desc, font=FS, text_color=M).pack(anchor="w")

            if placeholder:
                val = ch_cfg.get("key", "") or ch_cfg.get("webhook", "")
                e = ctk.CTkEntry(inn, font=FB, fg_color=B2, border_width=0, height=30,
                                  placeholder_text=placeholder)
                e.insert(0, val)
                e.pack(fill="x", pady=(4, 0))
                e.bind("<FocusOut>", lambda ev, k=key, ee=e: self._notif_save_val(k, ee.get()))

            setattr(self, f"_notif_{key}_var", var)

        ctk.CTkLabel(sf, text="", font=FS).pack()
        ctk.CTkLabel(sf, text="定时推送", font=FH, text_color=T).pack(anchor="w", padx=8, pady=(8, 4))
        sc = self.core.cfg.get("schedule", {})
        sched_card = ctk.CTkFrame(sf, fg_color=B1, corner_radius=8)
        sched_card.pack(fill="x", pady=2, padx=4)
        si = ctk.CTkFrame(sched_card, fg_color="transparent")
        si.pack(fill="both", expand=True, padx=14, pady=10)

        self._sched_enabled = ctk.BooleanVar(value=sc.get("enabled", False))
        ctk.CTkCheckBox(si, text="开启定时推送", variable=self._sched_enabled, font=FH,
                         text_color=T, fg_color=A, hover_color=AH, border_width=2, border_color="#475569").pack(anchor="w")

        days_row = ctk.CTkFrame(si, fg_color="transparent")
        days_row.pack(fill="x", pady=(8, 4))
        ctk.CTkLabel(days_row, text="推送日:", font=FS, text_color=M).pack(side="left", padx=(0, 8))
        ds = sc.get("days", [1, 2, 3, 4, 5])
        day_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        self._day_vars = {}
        for i, dn in enumerate(day_names):
            v = ctk.BooleanVar(value=(i + 1) in ds)
            ctk.CTkCheckBox(days_row, text=dn, variable=v, font=FS, text_color=T,
                             fg_color=A, hover_color=AH, border_width=2, border_color="#475569", width=30).pack(side="left", padx=4)
            self._day_vars[i + 1] = v

        time_row = ctk.CTkFrame(si, fg_color="transparent")
        time_row.pack(fill="x", pady=(6, 0))
        ctk.CTkLabel(time_row, text="推送时间:", font=FS, text_color=M).pack(side="left", padx=(0, 6))
        hh = sc.get("time", "10:00").split(":")[0]
        mm = sc.get("time", "10:00").split(":")[1] if ":" in sc.get("time", "10:00") else "00"
        self._tv_h = ctk.CTkEntry(time_row, font=FB, fg_color=B2, border_width=0,
                                   height=30, width=42, justify="center")
        self._tv_h.insert(0, hh)
        self._tv_h.pack(side="left")
        ctk.CTkLabel(time_row, text=" : ", font=FB, text_color=T).pack(side="left")
        self._tv_m = ctk.CTkEntry(time_row, font=FB, fg_color=B2, border_width=0,
                                   height=30, width=42, justify="center")
        self._tv_m.insert(0, mm)
        self._tv_m.pack(side="left")
        ctk.CTkLabel(time_row, text="  (24小时制)", font=FS, text_color=M).pack(side="left")

        btn_row = ctk.CTkFrame(si, fg_color="transparent")
        btn_row.pack(fill="x", pady=(10, 0))
        ctk.CTkButton(btn_row, text="💾 保存设置", font=FH, fg_color=A, hover_color=AH,
                       corner_radius=10, height=36, command=self._save_notify).pack(side="right", padx=4)

    def _notif_toggle(self, key, var):
        ns = self.core.cfg.get("notifications", {})
        ns.setdefault(key, {})["enabled"] = var.get()
        self.core.cfg.set("notifications", ns)

    def _notif_save_val(self, key, val):
        ns = self.core.cfg.get("notifications", {})
        if key in ("bark", "server_chan"):
            ns.setdefault(key, {})["enabled"] = ns.get(key, {}).get("enabled", False)
            ns[key]["key"] = val.strip()
        else:
            ns.setdefault(key, {})["enabled"] = ns.get(key, {}).get("enabled", False)
            ns[key]["webhook"] = val.strip()
        self.core.cfg.set("notifications", ns)

    def _test_notif(self, channel):
        btn = getattr(self, f"_notif_btn_{channel}", None)
        if self._last_results:
            r = self._last_results
            body = f"{r.get('strategy_name','')}: 符合{len(r.get('exact',[]))}只 相似{len(r.get('similar',[]))}只"
            watch = r.get("watch_stocks", [])
            if watch:
                body += "\n\n【自选股】"
                shown = 0
                for w in watch:
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
        else:
            body = "如果你看到这条消息，说明通知配置成功 ✅"
        try:
            from engine import notifier as _nf
            settings = self.core.cfg.get("notifications", {})
            _nf.push_all({channel: settings.get(channel, {})}, f"{APP_NAME} · 测试", body)
            if btn:
                btn.configure(text="已发送 ✅", fg_color=G, hover_color="#4ade80", state="disabled")
                self.after(2000, lambda b=btn: b.configure(text="测试", fg_color=B2, hover_color="#475569", state="normal"))
        except Exception as e:
            if btn:
                btn.configure(text="失败", fg_color=D, hover_color="#f87171")
                self.after(2000, lambda b=btn: b.configure(text="测试", fg_color=B2, hover_color="#475569", state="normal"))
            messagebox.showerror("测试失败", str(e))

    def _save_notify(self):
        h = self._tv_h.get().strip()
        m = self._tv_m.get().strip()
        if not re.match(r'^\d{1,2}$', h) or not re.match(r'^\d{1,2}$', m):
            messagebox.showerror("格式错误", "时间格式不对哦！\n请按 24 小时制输入数字，例如 08 : 30")
            return
        hh, mm = int(h), int(m)
        if hh < 0 or hh > 23 or mm < 0 or mm > 59:
            messagebox.showerror("格式错误", f"时间不合法: {h}:{m}\n小时: 0-23, 分钟: 0-59")
            return
        time_str = f"{hh:02d}:{mm:02d}"

        ns = self.core.cfg.get("notifications", {})
        for key in ["windows_toast", "bark", "dingtalk", "feishu", "server_chan"]:
            var = getattr(self, f"_notif_{key}_var", None)
            if var:
                ns.setdefault(key, {})["enabled"] = var.get()
        self.core.cfg.set("notifications", ns)

        days = sorted([d for d, v in self._day_vars.items() if v.get()])
        if not days:
            messagebox.showerror("格式错误", "请至少选择一个推送日")
            return

        self.core.cfg.update({"schedule": {
            "enabled": self._sched_enabled.get(),
            "time": time_str,
            "days": days,
        }})

        if self._sched_enabled.get():
            try:
                self.core.install_schedule(time_str, days)
                day_names = {1:"周一",2:"周二",3:"周三",4:"周四",5:"周五",6:"周六",7:"周日"}
                ds = " ".join(day_names[d] for d in days)
                messagebox.showinfo("保存成功", f"定时推送已设置 ✅\n{ds}  {time_str}")
            except Exception as e:
                messagebox.showerror("计划任务失败", str(e))
        else:
            try:
                self.core.uninstall_schedule()
            except Exception:
                pass
            messagebox.showinfo("保存成功", "设置已保存 ✅")


if __name__ == "__main__":
    App().mainloop()
