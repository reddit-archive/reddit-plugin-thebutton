from datetime import datetime

from pylons import c, g

from r2.controllers import add_controller
from r2.controllers.api import ApiController
from r2.lib.validator import (
    nop,
    validate,
    VInt,
    VModhash,
    VUser,
)

from reddit_thebutton.models import (
    ACCOUNT_CREATION_CUTOFF,
    ButtonPressByUser,
    check_tick_mac,
    get_seconds_left,
    has_timer_expired,
    has_timer_started,
    press_button,
    set_current_press,
    str_to_datetime,
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
        seconds_remaining=VInt('seconds', min=0, max=60),
        previous_seconds=VInt('prev_seconds'),
        tick_time=nop('tick_time'),
        tick_mac=nop('tick_mac'),
    )
    def POST_press_button(self, seconds_remaining, previous_seconds, tick_time, tick_mac):
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

        cheater = False
        if (seconds_remaining is None or
                previous_seconds is None or
                tick_time is None or
                tick_mac is None):
            # incomplete info from client, just let them press it anyways
            seconds_remaining = max(0, int(get_seconds_left()))
        elif not check_tick_mac(previous_seconds, tick_time, tick_mac):
            # can't trust the values sent by the client
            seconds_remaining = max(0, int(get_seconds_left()))
            cheater = True
        else:
            # client sent a valid mac so we can trust:
            # previous_seconds - the timer value at the last tick
            # tick_time - the datetime at the last tick

            # check to make sure tick_time wasn't too long ago
            then = str_to_datetime(tick_time)
            now = datetime.now(g.tz)
            if (now - then).total_seconds() > 60:
                # client sent an old (but potentially valid) mac, etc.
                seconds_remaining = max(0, int(get_seconds_left()))
                cheater = True

            # check to make sure the seconds remaining they reported isn't too
            # far off from the timer value at the previous tick
            if previous_seconds - seconds_remaining > 10:
                seconds_remaining = max(0, int(get_seconds_left()))
                cheater = True

        press_button(c.user)

        # don't flair on first press (the starter)
        if not has_started:
            return

        if cheater:
            flair_css = "cheater"
        elif seconds_remaining > 51:
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
