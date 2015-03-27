from pylons import c, g

from r2.controllers import add_controller
from r2.controllers.api import ApiController
from r2.controllers.reddit_base import RedditController
from r2.lib.validator import (
    validate,
    VInt,
    VModhash,
    VUser,
)

from reddit_thebutton.models import (
    ACCOUNT_CREATION_CUTOFF,
    ButtonPressByUser,
    get_seconds_left,
    has_timer_expired,
    has_timer_started,
    press_button,
    set_current_press,
)

from reddit_thebutton.pages import (
    TheButtonBase,
    TheButton,
)


@add_controller
class ButtonApiController(ApiController):
    @validate(
        VUser(),
        VModhash(),
        client_seconds_remaining=VInt('seconds', min=0, max=60),
    )
    def POST_press_button(self, client_seconds_remaining):
        if not g.live_config['thebutton_is_active']:
            return

        if c.user._date > ACCOUNT_CREATION_CUTOFF:
            return

        if ButtonPressByUser.has_pressed(c.user) and not c.user.employee:
            return

        if has_timer_expired():
            # time has expired: no longer possible to press the button
            return

        has_started = has_timer_started()

        if not has_started and not c.user.employee:
            # only employees can make the first press
            return

        if client_seconds_remaining is None:
            seconds_remaining = max(0, int(get_seconds_left()))
        else:
            seconds_remaining = client_seconds_remaining

        press_button(c.user)

        # don't flair on first press (the starter)
        if not has_started:
            return

        if seconds_remaining > 51:
            flair_css = "press-6"
        elif seconds_remaining > 41:
            flair_css = "press-5"
        elif seconds_remaining > 31:
            flair_css = "press-4"
        elif seconds_remaining > 21:
            flair_css = "press-3"
        elif seconds_remaining > 11:
            flair_css = "press-2"
        else:
            flair_css = "press-1"

        flair_text = "%ss" % seconds_remaining

        setattr(c.user, 'flair_%s_text' % g.live_config["thebutton_srid"], flair_text)
        setattr(c.user, 'flair_%s_css_class' % g.live_config["thebutton_srid"], flair_css)
        c.user._commit()


@add_controller
class ButtonController(RedditController):
    def GET_button(self):
        content = TheButton()
        return TheButtonBase(content=content).render()
