from pylons import g, c

from r2.lib.hooks import HookRegistrar
from r2.models import Subreddit, Link, Comment

from reddit_thebutton.pages import TheButton

hooks = HookRegistrar()


@hooks.on("hot.get_content")
def add_thebutton(controller):
    return TheButton()
