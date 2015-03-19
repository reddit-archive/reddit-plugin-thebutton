from pylons import c, g

from r2.controllers import add_controller
from r2.controllers.api import ApiController
from r2.controllers.reddit_base import RedditController
from r2.lib.validator import (
    validate,
    VModhash,
    VUser,
)
from r2.models.keyvalue import NamedGlobals

from reddit_thebutton.models import (
    ButtonPressesByDate,
    ButtonPressByUser,
    EXPIRATION_TIME,
    get_current_press,
    has_timer_expired,
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
    )
    def POST_press_button(self):
        if ButtonPressByUser.has_pressed(c.user) and not c.user.employee:
            return

        if has_timer_expired():
            # time has expired: no longer possible to press the button
            return

        previous_press_time = get_current_press()
        press_time = ButtonPressesByDate.press(c.user)
        ButtonPressByUser.pressed(c.user, press_time)
        set_current_press(press_time)

        # should time elapsed be tracked somewhere?
        flair_text = str(press_time)
        if previous_press_time:
            time_elapsed_at_press = (press_time - previous_press_time)
            time_remaining_at_press = EXPIRATION_TIME - time_elapsed_at_press
            seconds_remaining = max(0, int(time_remaining_at_press.total_seconds()))
            flair_css = "%s-seconds" % seconds_remaining
        else:
            flair_css = "first-press"

        setattr(c.user, 'flair_%s_text' % g.thebutton_srid, flair_text)
        setattr(c.user, 'flair_%s_css_class' % g.thebutton_srid, flair_css)
        c.user._commit()


@add_controller
class ButtonController(RedditController):
    def GET_button(self):
        content = TheButton()
        return TheButtonBase(content=content).render()
