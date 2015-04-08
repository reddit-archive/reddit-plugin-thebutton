from pylons import g

from r2.lib.utils import in_chunks
from r2.models import Account, AccountsActiveBySR, Subreddit
from reddit_thebutton.models import ACCOUNT_CREATION_CUTOFF

from collections import Counter


def update_flair_counts():
    flairs = Counter()
    user_ids = []

    sr = Subreddit._byID(g.live_config["thebutton_srid"], data=True)
    raw = AccountsActiveBySR._cf.xget(sr._id36)
    for uid, _ in raw:
        user_ids.append(uid)

    for user_chunk in in_chunks(user_ids, size=100):
        users = Account._byID36(user_chunk, data=True, return_dict=False)
        for user in users:
            flair = user.flair_css_class(sr._id)
            if not flair:
                if user._date < ACCOUNT_CREATION_CUTOFF:
                    flair = "no-press"
                else:
                    flair = "cant-press"

            flairs[flair] += 1

    if 'cheater' in flairs:
        del flairs['cheater']

    sr.flair_counts = sorted(
        flairs.iteritems(),
        key=lambda x: 'z' if x[0] == 'no-press' else x[0],
        reverse=True)
    sr._commit()
