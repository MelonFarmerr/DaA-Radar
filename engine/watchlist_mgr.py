from . import datasource


class WatchlistManager:
    def __init__(self, config_mgr):
        self._cfg = config_mgr

    @property
    def list(self):
        return self._cfg.get("watch_list", [])

    def search(self, keyword):
        return datasource.search_stock(keyword)

    def add(self, code, cost=0):
        info, _ = datasource.get_stock(code)
        name = info["name"] if info and info.get("name") else code
        wl = self._cfg.get("watch_list", [])
        for w in wl:
            if w["code"] == code:
                return w
        entry = {"code": code, "name": name, "cost": float(cost) if cost else 0, "notes": ""}
        wl.append(entry)
        self._cfg.set("watch_list", wl)
        return entry

    def remove(self, code):
        wl = self._cfg.get("watch_list", [])
        wl = [w for w in wl if w["code"] != code]
        self._cfg.set("watch_list", wl)

    def get_stock_data(self, code):
        info, fresh = datasource.get_stock(code)
        return info, fresh

    def get_all_data(self):
        result = []
        for w in self.list:
            info, fresh = datasource.get_stock(w["code"])
            if info:
                info["cost"] = w.get("cost", 0)
                info["_fresh"] = fresh
            else:
                info = {"code": w["code"], "name": w["name"], "price": 0,
                        "change_pct": 0, "cost": w.get("cost", 0), "_fresh": False}
            result.append(info)
        return result
