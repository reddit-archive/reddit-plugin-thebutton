from r2.lib.configparse import ConfigValue
from r2.lib.plugin import Plugin


class TheButton(Plugin):
    config = {
        ConfigValue.tuple: [
            "thebutton_caches",
        ],
        ConfigValue.int: [
            "thebutton_srid",
        ],
    }

    live_config = {
        ConfigValue.str: [
            "thebutton_id",
        ],
    }

    def on_load(self, g):
        from r2.lib.cache import CMemcache, MemcacheChain, LocalCache, SelfEmptyingCache

        thebutton_memcaches = CMemcache(
            'thebutton',
            g.thebutton_caches,
            num_clients=g.num_mc_clients,
        )
        localcache_cls = (SelfEmptyingCache if g.running_as_script else LocalCache)
        g.thebuttoncache = MemcacheChain((
            localcache_cls(),
            thebutton_memcaches,
        ))
        g.cache_chains.update(thebutton=g.thebuttoncache)

    def add_routes(self, mc):
        mc(
            "/api/press_button",
            controller="button",
            action="press_button",
        )

    def load_controllers(self):
        from reddit_thebutton.controllers import ButtonController
