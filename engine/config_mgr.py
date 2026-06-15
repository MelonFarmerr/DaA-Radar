import json, os, base64, sys

def _data_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CFG_PATH = os.path.join(_data_dir(), "config.json")

def _bundled_cfg():
    if not getattr(sys, 'frozen', False):
        return None
    meipass = getattr(sys, '_MEIPASS', '')
    path = os.path.join(meipass, "config.json")
    return path if os.path.exists(path) else None

CURRENT_VERSION = 3

DEFAULT_CONFIG = {
    "version": CURRENT_VERSION,
    "watch_list": [
        {"code": "600519", "name": "贵州茅台", "cost": 0, "notes": ""},
        {"code": "002594", "name": "比亚迪", "cost": 0, "notes": ""},
        {"code": "300750", "name": "宁德时代", "cost": 0, "notes": ""},
    ],
    "strategy": "steady",
    "schedule": {
        "enabled": False,
        "time": "10:00",
        "days": [1, 2, 3, 4, 5]
    },
    "notifications": {
        "windows_toast": {"enabled": True},
        "bark": {"enabled": False, "key": ""},
        "dingtalk": {"enabled": False, "webhook": ""},
        "feishu": {"enabled": False, "webhook": ""},
        "server_chan": {"enabled": False, "key": ""},
    },
    "database": "stock_history.db",
    "groq_key": "",
    "appearance": {
        "theme": "dark",
        "font_scale": 1
    }
}


def _obfuscate(text):
    if not text:
        return ""
    return base64.b64encode(text.encode()).decode()


def _deobfuscate(text):
    if not text:
        return ""
    try:
        return base64.b64decode(text.encode()).decode()
    except Exception:
        return text


class ConfigManager:
    def __init__(self, path=None):
        self._path = path or CFG_PATH
        self._data = None
        self.load()

    def load(self):
        if not os.path.exists(self._path):
            bundled = _bundled_cfg()
            if bundled:
                import shutil
                shutil.copy(bundled, self._path)
            else:
                self._data = dict(DEFAULT_CONFIG)
                self.save()
                return self._data
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                self._data = json.load(f)
        except (json.JSONDecodeError, IOError):
            self._data = dict(DEFAULT_CONFIG)
            self.save()
        self._migrate()
        self._deobfuscate_keys()
        return self._data

    def save(self):
        data = json.loads(json.dumps(self._data, ensure_ascii=False))
        self._obfuscate_keys(data)
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _obfuscate_keys(self, data):
        if data.get("groq_key"):
            data["groq_key"] = _obfuscate(data["groq_key"])
        for ch in data.get("notifications", {}).values():
            if ch.get("key"):
                ch["key"] = _obfuscate(ch["key"])
            if ch.get("webhook"):
                ch["webhook"] = _obfuscate(ch["webhook"])

    def _deobfuscate_keys(self):
        if self._data.get("groq_key"):
            self._data["groq_key"] = _deobfuscate(self._data["groq_key"])
        for ch in self._data.get("notifications", {}).values():
            if ch.get("key"):
                ch["key"] = _deobfuscate(ch["key"])
            if ch.get("webhook"):
                ch["webhook"] = _deobfuscate(ch["webhook"])

    def _migrate(self):
        v = self._data.get("version", 0)
        if v < 1:
            pass
        if v < 2:
            self._data.setdefault("schedule", {}).setdefault("enabled", False)
            self._data["schedule"].setdefault("days", [1, 2, 3, 4, 5])
            self._data.setdefault("notifications", DEFAULT_CONFIG["notifications"])
            self._data["version"] = 2
            self.save()
        if v < 3:
            self._data.setdefault("appearance", {"theme": "dark", "font_scale": 1})
            self._data["version"] = 3
            self.save()

    @property
    def data(self):
        return self._data

    def get(self, key, default=None):
        return self._data.get(key, default)

    def set(self, key, value):
        self._data[key] = value
        self.save()

    def update(self, d):
        self._data.update(d)
        self.save()
