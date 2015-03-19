from r2.lib import websockets
from r2.lib.pages import Reddit
from r2.lib.wrapped import Templated
from reddit_thebutton.models import get_num_participants


class TheButtonBase(Reddit):
    def __init__(self, content):
        websocket_url = websockets.make_url("/thebutton", max_age=24 * 60 * 60)
        extra_js_config = {"thebutton_websocket": websocket_url}
        Reddit.__init__(self, content=content, extra_js_config=extra_js_config)


class TheButton(Templated):
    def __init__(self):
        websocket_url = websockets.make_url("/thebutton", max_age=24 * 60 * 60)
        self.num_participants = get_num_participants()
        Templated.__init__(self, websocket_url=websocket_url)
