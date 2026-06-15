# 大A雷达

> 免费开源的 A 股条件筛选 + 自选追踪 + 多通道推送工具。双击即用，零配置。

## 快速上手

1. 下载 
2. 双击 `大A雷达.exe`
3. 点击「开始」查看今日行情
4. 去「自选股」搜索添加你关注的股票
5. 去「策略」选择筛选策略（自带 3 个模板）
6. 去「通知」开启推送（可选）

---

## 功能一览

| 模块 | 说明 |
|---|---|
| 🏠 运行 | 大盘指数 + 自选股行情 + 策略筛选结果，一键运行 |
| ⭐ 自选股 | 模糊搜索（输入"茅台"自动匹配代码）、成本价盈亏计算、卡片式管理 |
| 🎯 策略 | 3 个预设模板 + 填表式自定义 + Tag 超市（技术指标自由组合）+ 大白话输入 |
| 📬 通知 | 电脑弹窗 / iPhone(Bark) / 钉钉 / 飞书 / 微信(Server酱)，7 天自由勾选时间 |

## 策略筛选

### 预设模板
- **稳健筛选** — 10-100 元、换手活跃、均线多头、仅主板
- **动量突破** — 放量上涨、涨幅 3%-9%、中小市值
- **超跌反弹** — 超卖信号、量比放大、可能反弹

### 自定义条件
分四组填写：行情（股价/涨跌幅/换手率/量比）、基本面（市值/PE/PB/ROE）、技术形态（Tag 超市多选）、板块（默认全选）。

支持的自然语言输入（本地正则解析，不联网）：
```
股价10-100元 换手>7% 非ST 均线多头 5日多头 MACD金叉 排除科创
```

## 通知推送

| 通道 | 门槛 |
|---|---|
| 💻 电脑弹窗 | 零配置，默认开启 |
| 📱 Bark (iPhone) | App Store 下载 Bark → 复制 Key |
| 💬 钉钉 | 建群 → 智能群助手 → Webhook |
| 🐦 飞书 | 群机器人 → Webhook |
| 💚 Server酱 (微信) | 注册 [sct.ftqq.com](https://sct.ftqq.com/) → SendKey |

## 数据源

双源自动切换，任意源挂了自动切：

| 源 | 说明 |
|---|---|
| 东方财富 | 主力，字段最全，部分网络需代理 |
| 新浪财经 | 兜底，免费无需注册，直连可用 |

行情数据自动缓存到本地 SQLite，网络不通时使用最近一次缓存。

## 从源码运行

```bash
pip install customtkinter
python gui.py
```

## 打包 EXE

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name 大A雷达 \
  --add-data "engine;engine" \
  --add-data "strategies;strategies" \
  --add-data "config.json;." \
  --hidden-import customtkinter gui.py
```

## 项目结构

```
股票/
  gui.py                 GUI 主程序
  briefing.py            CLI 入口（计划任务用）
  config.json            配置（自选/策略/通知）
  engine/
    core.py              调度中心
    datasource.py         双源数据层（东财+新浪+缓存）
    screener.py           本地筛选引擎
    parser.py             自然语言解析（本地正则）
    notifier.py           多通道推送
    strategy_mgr.py       策略管理
    config_mgr.py          配置读写
    watchlist_mgr.py      自选股管理
  strategies/            预设策略 JSON
```

## 系统要求

- Windows 10/11（64位）
- 不需要 Python 环境（EXE 自带）
- 不需要注册任何账号（除非使用推送功能）

## 反馈与贡献

遇到 Bug 或有功能建议？请在 [Issues](../../issues) 页面提交，尽可能附上截图和错误信息。

## 许可

MIT License — 仅供学习研究，不构成投资建议。

---

🤖 由 [Claude Code](https://claude.ai/code) 辅助开发
