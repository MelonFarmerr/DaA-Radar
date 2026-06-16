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

    def get_stock_data(self, code, cache_ttl=600):
        info, fresh = datasource.get_stock(code, cache_ttl=cache_ttl)
        return info, fresh

    def get_all_data(self, cache_ttl=600):
        from .scheduler import batch_run
        items = list(self.list)
        if not items:
            return []

        def _fetch(w):
            info, fresh = datasource.get_stock(w["code"], cache_ttl=cache_ttl)
            if info:
                info["cost"] = w.get("cost", 0)
                info["_fresh"] = fresh
                return info
            return {"code": w["code"], "name": w["name"], "price": 0,
                    "change_pct": 0, "cost": w.get("cost", 0), "_fresh": False}

        results = batch_run(_fetch, items)
        return [results.get(i) for i in range(len(items)) if results.get(i) is not None]
