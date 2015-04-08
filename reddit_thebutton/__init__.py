from r2.lib.configparse import ConfigValue
from r2.lib.js import Module
from r2.lib.plugin import Plugin

class TheButton(Plugin):
    needs_static_build = True

    config = {
        ConfigValue.tuple: [
            "thebutton_caches",
        ],
    }

    live_config = {
        ConfigValue.int: [
            "thebutton_srid",
        ],
        ConfigValue.bool: [
            "thebutton_is_active",
        ],
        ConfigValue.str: [
            "thebutton_nopress_flair_class",
            "thebutton_nopress_flair_text",
            "thebutton_cantpress_flair_class",
            "thebutton_cantpress_flair_text",
        ],
    }

    js = {
        "reddit": Module("reddit.js",
            "websocket.js",
            "thebutton.js",
        )
    }

    def on_load(self, g):
        from r2.lib.cache import CMemcache, MemcacheChain, LocalCache, SelfEmptyingCache

        thebutton_memcaches = CMemcache(
            'thebutton',
            g.thebutton_caches,
            min_compress_len=1400,
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
            controller="buttonapi",
            action="press_button",
        )

    def load_controllers(self):
        from r2.lib.pages import Reddit
        from reddit_thebutton.controllers import (
            ButtonApiController,
        )

        Reddit.extra_stylesheets.append('thebutton.less')

        from reddit_thebutton.hooks import hooks
        hooks.register_all()

    def declare_queues(self, queues):
        from r2.config.queues import MessageQueue
        queues.declare({
            "buttonflair_q": MessageQueue(),
        })

        queues.buttonflair_q << (
            "new_comment",
            "new_link",
        )
