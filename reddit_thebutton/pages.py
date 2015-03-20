from pylons import c

from r2.lib import websockets
from r2.lib.pages import Reddit
from r2.lib.wrapped import Templated
from reddit_thebutton.models import (
    ACCOUNT_CREATION_CUTOFF,
    get_num_participants,
)


class TheButtonBase(Reddit):
    def __init__(self, content):
        websocket_url = websockets.make_url("/thebutton", max_age=24 * 60 * 60)
        extra_js_config = {"thebutton_websocket": websocket_url}
        Reddit.__init__(self, content=content, extra_js_config=extra_js_config)


class TheButton(Templated):
    def __init__(self):
        websocket_url = websockets.make_url("/thebutton", max_age=24 * 60 * 60)
        self.num_participants = get_num_participants()
        too_new = c.user_is_loggedin and c.user._date > ACCOUNT_CREATION_CUTOFF
        self.too_new = too_new

        Templated.__init__(self, websocket_url=websocket_url)
