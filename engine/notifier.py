import urllib.request, urllib.parse, subprocess, os, json, sys, xml.sax.saxutils as _xml

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PYTHONW = sys.executable.replace("python.exe", "pythonw.exe").replace("pythonw.exe", "pythonw.exe")


def _post(url, data=None, headers=None):
    h = {"User-Agent": "Mozilla/5.0"}
    if headers:
        h.update(headers)
    body = None
    if data:
        body = json.dumps(data).encode() if isinstance(data, dict) else data
    req = urllib.request.Request(url, data=body, headers=h)
    urllib.request.urlopen(req, timeout=10)


def push_windows_toast(title, message):
    try:
        t = _xml.escape(title).replace("'", "''")
        m = _xml.escape(message).replace("'", "''")
        ps = (
            "[Windows.UI.Notifications.ToastNotificationManager,Windows.UI.Notifications,ContentType=WindowsRuntime]|Out-Null;"
            "$t=[Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent("
            "[Windows.UI.Notifications.ToastTemplateType]::ToastText02);"
            f"$t.GetElementsByTagName('text').Item(0).AppendChild($t.CreateTextNode('{t}'))|Out-Null;"
            f"$t.GetElementsByTagName('text').Item(1).AppendChild($t.CreateTextNode('{m}'))|Out-Null;"
            "$n=[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('大A雷达');"
            "$n.Show([Windows.UI.Notifications.ToastNotification]::new($t))"
        )
        subprocess.run(
            ["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", ps],
            capture_output=True, timeout=10
        )
    except Exception:
        pass


def push_bark(key, title, message):
    data = urllib.parse.urlencode({"title": title, "body": message[:4000]}).encode()
    req = urllib.request.Request(
        f"https://api.day.app/{key}/",
        data=data,
        headers={"User-Agent": "Mozilla/5.0"},
    )
    urllib.request.urlopen(req, timeout=10)


def push_dingtalk(webhook, title, message):
    _post(webhook, {"msgtype": "markdown", "markdown": {"title": title, "text": f"## {title}\n\n{message}"}},
          {"Content-Type": "application/json"})


def push_feishu(webhook, title, message):
    _post(webhook, {"msgtype": "interactive", "card": {
        "header": {"title": {"tag": "plain_text", "content": title}},
        "elements": [{"tag": "markdown", "content": message[:4000]}],
    }}, {"Content-Type": "application/json"})


def push_server_chan(key, title, message):
    data = urllib.parse.urlencode({"title": title, "desp": message[:5000]}).encode("utf-8")
    req = urllib.request.Request(
        f"https://sctapi.ftqq.com/{key}.send",
        data=data,
        headers={"User-Agent": "Mozilla/5.0"},
    )
    urllib.request.urlopen(req, timeout=10)


def push_all(settings, title, message):
    results = {}
    if settings.get("windows_toast", {}).get("enabled"):
        try:
            push_windows_toast(title, message)
            results["windows_toast"] = True
        except Exception as e:
            results["windows_toast"] = str(e)

    if settings.get("bark", {}).get("enabled") and settings["bark"].get("key"):
        try:
            push_bark(settings["bark"]["key"], title, message)
            results["bark"] = True
        except Exception as e:
            results["bark"] = str(e)

    if settings.get("dingtalk", {}).get("enabled") and settings["dingtalk"].get("webhook"):
        try:
            push_dingtalk(settings["dingtalk"]["webhook"], title, message)
            results["dingtalk"] = True
        except Exception as e:
            results["dingtalk"] = str(e)

    if settings.get("feishu", {}).get("enabled") and settings["feishu"].get("webhook"):
        try:
            push_feishu(settings["feishu"]["webhook"], title, message)
            results["feishu"] = True
        except Exception as e:
            results["feishu"] = str(e)

    if settings.get("server_chan", {}).get("enabled") and settings["server_chan"].get("key"):
        try:
            push_server_chan(settings["server_chan"]["key"], title, message)
            results["server_chan"] = True
        except Exception as e:
            results["server_chan"] = str(e)

    return results


def install_scheduled_task(script_path, time_str="10:00", days=None):
    if days is None:
        days = [1, 2, 3, 4, 5]
    task_name = "KekeStockBriefing"
    subprocess.run(f'schtasks /delete /tn "{task_name}" /f', shell=True, capture_output=True)
    day_map = {0: "SUN", 1: "MON", 2: "TUE", 3: "WED", 4: "THU", 5: "FRI", 6: "SAT"}
    day_str = ",".join(day_map.get(d, "") for d in sorted(days) if d in day_map)
    if not day_str:
        day_str = "MON,TUE,WED,THU,FRI"
    cmd = (
        f'schtasks /create /tn "{task_name}"'
        f' /tr "\\"{PYTHONW}\\" \\"{script_path}\\""'
        f' /sc weekly /d {day_str}'
        f' /st {time_str}'
        f' /f'
    )
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr or result.stdout)


def uninstall_scheduled_task():
    subprocess.run('schtasks /delete /tn "KekeStockBriefing" /f', shell=True, capture_output=True)
