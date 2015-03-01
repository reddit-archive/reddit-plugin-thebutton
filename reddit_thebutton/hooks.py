from pylons import g, c

from r2.lib import websockets
from r2.lib.hooks import HookRegistrar
from r2.models import Subreddit, Link, Comment

from reddit_thebutton.pages import TheButton

hooks = HookRegistrar()


@hooks.on("hot.get_content")
def add_thebutton(controller):
    return TheButton()


@hooks.on('js_config')
def add_js_config(config):
    if getattr(c.site, '_id', None) == g.thebutton_srid:
        config['thebutton_websocket'] = websockets.make_url("/thebutton",
                                                            max_age=24 * 60 * 60)
