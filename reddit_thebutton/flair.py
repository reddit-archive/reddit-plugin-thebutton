from pylons import g

from r2.lib import amqp
from r2.lib.db.thing import Thing
from r2.models import Comment, Link
from reddit_thebutton.models import ACCOUNT_CREATION_CUTOFF


@g.stats.amqp_processor('buttonflair_q')
def update_flairs(msg):
    """Add non presser flair to posters/commenters in thebutton SR"""
    fullname = msg.body

    thing = Thing._by_fullname(fullname)
    if (not isinstance(thing, (Comment, Link)) or
            thing.sr_id != g.live_config["thebutton_srid"]):
        return

    author = thing.author_slow
    sr = thing.subreddit_slow

    if not author.flair_css_class(sr._id):
        if author._date < ACCOUNT_CREATION_CUTOFF:
            flair_class = g.live_config["thebutton_nopress_flair_class"]
            flair_text = g.live_config["thebutton_nopress_flair_text"]
        else:
            flair_class = g.live_config["thebutton_cantpress_flair_class"]
            flair_text = g.live_config["thebutton_cantpress_flair_text"]

        if flair_class:
            author.set_flair(sr, css_class=flair_class, text=flair_text)


def process_flair():
    amqp.consume_items('buttonflair_q', update_flairs)
