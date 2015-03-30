from pylons import c, g

from r2.lib import websockets
from r2.lib.pages import Reddit
from r2.lib.wrapped import Templated
from reddit_thebutton.models import (
    ACCOUNT_CREATION_CUTOFF,
    ButtonPressByUser,
    get_num_participants,
    has_timer_expired,
)


class TheButtonBase(Reddit):
    def __init__(self, content):
        websocket_url = websockets.make_url("/thebutton", max_age=24 * 60 * 60)
        extra_js_config = {"thebutton_websocket": websocket_url}
        Reddit.__init__(self, content=content, extra_js_config=extra_js_config)


class TheButton(Templated):
    def __init__(self):
        self.is_active = g.live_config['thebutton_is_active']
        self.num_participants = get_num_participants()
        self.has_expired = has_timer_expired()

        if c.user_is_loggedin:
            self.too_new = c.user._date > ACCOUNT_CREATION_CUTOFF
            self.has_pressed = ButtonPressByUser.has_pressed(c.user)
        else:
            self.too_new = False
            self.has_pressed = False

        Templated.__init__(self)
