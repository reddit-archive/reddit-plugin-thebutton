from datetime import datetime, timedelta
from time import sleep
from uuid import uuid1, UUID

from babel.numbers import format_number
from pycassa.cassandra.ttypes import NotFoundException
from pycassa.system_manager import TIME_UUID_TYPE
from pycassa.util import convert_uuid_to_time
from pylons import g

from r2.lib import websockets
from r2.lib.db import tdb_cassandra
from r2.models import Account
from r2.models.keyvalue import NamedGlobals


TIME_EXPIRED_KEY = "THE_BUTTON_TIME_EXPIRED"
CURRENT_PRESS_KEY = "THE_BUTTON_CURRENT_PRESS"
PARTICIPANTS_KEY = "THE_BUTTON_PARTICIPANTS"
EXPIRATION_TIME = timedelta(seconds=60)
EXPIRATION_FUDGE_SECONDS = 2
UPDATE_INTERVAL_SECONDS = 1
ACCOUNT_CREATION_CUTOFF = datetime(2015, 4, 1, 0, 0, tzinfo=g.tz)


def _EXPIRED_KEY():
    return "%s.%s" % (g.live_config["thebutton_id"], TIME_EXPIRED_KEY)


def _CURRENT_PRESS_KEY():
    return "%s.%s" % (g.live_config["thebutton_id"], CURRENT_PRESS_KEY)


class ButtonPressesByDate(tdb_cassandra.View):
    _use_db = True
    _connection_pool = 'main'
    _compare_with = TIME_UUID_TYPE
    _extra_schema_creation_args = {
        "key_validation_class": tdb_cassandra.ASCII_TYPE,
    }
    _write_consistency_level = tdb_cassandra.CL.ONE
    _read_consistency_level = tdb_cassandra.CL.ONE

    """
    Track all button presses. TimeUUID for column names, Account._id36 for
    column value. rowkey based on date buckets.
    """

    @classmethod
    def _rowkey(cls, dt):
        # use a new row every 5 minutes
        minute_bucket = dt.minute / 5 * 5 # 12 values per hour: 0, 5, 10, ...
        time_pieces = (dt.year, dt.month, dt.day, dt.hour, minute_bucket)
        time_part = "%04d-%02d-%02d-%02d-%02d" % time_pieces
        return "%s.%s" % (g.live_config["thebutton_id"], time_part)

    @classmethod
    def press(cls, user):
        u = uuid1()
        timestamp = convert_uuid_to_time(u)
        dt = datetime.fromtimestamp(timestamp, tz=g.tz)
        rowkey = cls._rowkey(dt)
        column = {u: user._id36}
        cls._cf.insert(rowkey, column,
            write_consistency_level=cls._write_consistency_level)
        return dt

    @classmethod
    def get_recent_press(cls):
        now = datetime.now(g.tz)
        rowkeys = [cls._rowkey(now + timedelta(minutes=i)) for i in (0, 5, 10)]
        columns_by_row = cls._cf.multiget(rowkeys, column_count=1,
            column_reversed=True,
            read_consistency_level=cls._read_consistency_level)

        dts = []
        for rowkey, column in columns_by_row.iteritems():
            dt = column.values()[0]
            dts.append(dt)

        if dts:
            return max(dts)


class ButtonPressByUser(tdb_cassandra.View):
    _use_db = True
    _connection_pool = 'main'
    _compare_with = tdb_cassandra.DateType()
    _extra_schema_creation_args = {
        "key_validation_class": tdb_cassandra.ASCII_TYPE,
    }
    _write_consistency_level = tdb_cassandra.CL.ONE
    _read_consistency_level = tdb_cassandra.CL.ONE

    @classmethod
    def _rowkey(cls, user):
        return "%s.%s" % (g.live_config["thebutton_id"], user._id36)

    @classmethod
    def pressed(cls, user, dt):
        rowkey = cls._rowkey(user)
        column = {dt: ''}
        cls._cf.insert(rowkey, column,
            write_consistency_level=cls._write_consistency_level)

    @classmethod
    def has_pressed(cls, user):
        rowkey = cls._rowkey(user)
        try:
            cls._cf.get(rowkey, column_count=1,
                read_consistency_level=cls._read_consistency_level)
        except NotFoundException:
            return False
        else:
            return True


def _update_timer():
    expiration_time = has_timer_expired()
    if expiration_time:
        seconds_elapsed = (datetime.now(g.tz) - expiration_time).total_seconds()
        g.log.debug("%s: timer is expired %s ago" % (datetime.now(g.tz), seconds_elapsed))

        websockets.send_broadcast(
            namespace="/thebutton", type="expired",
            payload={"seconds_elapsed": seconds_elapsed})
        return

    seconds_left = round(get_seconds_left())
    if seconds_left < 0:
        g.log.debug("%s: timer just expired" % datetime.now(g.tz))
        mark_timer_expired(datetime.now(g.tz))
        websockets.send_broadcast(
            namespace="/thebutton", type="just_expired", payload={})
    else:
        # TODO: don't update the timer, depend on the frontend to manage it
        g.log.debug("%s: timer is ticking %s" % (datetime.now(g.tz), seconds_left))
        websockets.send_broadcast(
            namespace="/thebutton", type="ticking",
            payload={
                "seconds_left": seconds_left,
                "participants_text": format_number(get_num_participants(), locale='en'),
            },
        )


def update_timer():
    while True:
        g.reset_caches()
        _update_timer()
        sleep(UPDATE_INTERVAL_SECONDS)


def has_timer_expired():
    # note: this only checks if the timer has been marked as expired, it doesn't
    # actually check its value (that's done in check_timer)
    key = _EXPIRED_KEY()
    val = g.thebuttoncache.get(key)
    if val is None:
        try:
            val = NamedGlobals.get(key)
        except NotFoundException:
            # has never been set, set the key
            val = False
            NamedGlobals.set(key, val)
        # update the cache
        g.thebuttoncache.set(key, val)

    if val:
        return _deserialize_datetime(val)

    return val


def mark_timer_expired(expiration_time):
    key = _EXPIRED_KEY()
    serialized = _serialize_datetime(expiration_time)
    NamedGlobals.set(key, serialized)
    g.thebuttoncache.set(key, serialized)


def get_seconds_left():
    current_press = get_current_press()
    if not current_press:
        return EXPIRATION_TIME.total_seconds()

    now = datetime.now(g.tz)
    time_elapsed = now - current_press
    seconds_left = (EXPIRATION_TIME - time_elapsed).total_seconds()

    # fudge the time a little
    if seconds_left <= 0:
        if (seconds_left + EXPIRATION_FUDGE_SECONDS) > 0:
            # return a time that isn't expired: 0 seconds isn't expired--less
            # than 0 is
            return 0.

    return seconds_left


def _serialize_datetime(dt):
    t = (dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second, dt.microsecond)
    return t


def _deserialize_datetime(t):
    dt = datetime(*t)
    dt = dt.replace(tzinfo=g.tz)
    return dt


NONE = "NONE"
def get_current_press():
    key = _CURRENT_PRESS_KEY()
    val = g.thebuttoncache.get(key)
    if val is None:
        try:
            val = NamedGlobals.get(key)
        except NotFoundException:
            val = NONE
        g.thebuttoncache.set(key, val)

    if val == NONE:
        return None
    elif val:
        return _deserialize_datetime(val)


def get_num_participants():
    return g.thebuttoncache.get(PARTICIPANTS_KEY) or 0


def set_current_press(press_time):
    key = _CURRENT_PRESS_KEY()
    serialized = _serialize_datetime(press_time)
    NamedGlobals.set(key, serialized)
    g.thebuttoncache.set(key, serialized)
    g.thebuttoncache.incr(PARTICIPANTS_KEY)


def reset_button():
    expired_key = _EXPIRED_KEY()
    press_key = _CURRENT_PRESS_KEY()

    NamedGlobals._cf.remove(expired_key)
    g.thebuttoncache.delete(expired_key)
    NamedGlobals._cf.remove(press_key)
    g.thebuttoncache.delete(press_key)

    g.thebuttoncache.set(PARTICIPANTS_KEY, 0)


def _delete_button_flair(user_id36s):
    users = Account._byID36(user_id36s, data=True, return_dict=False)
    for user in users:
        g.log.debug("deleting flair for %s" % user.name)
        setattr(user, 'flair_%s_text' % g.thebutton_srid, None)
        setattr(user, 'flair_%s_css_class' % g.thebutton_srid, None)
        user._commit()


def nuclear_reset():
    user_id36s = set()
    CHUNK_SIZE = 100
    for rowkey, columns in ButtonPressByUser._cf.get_range():
        button_id, user_id36 = rowkey.split('.')
        user_id36s.add(user_id36)

        if len(user_id36s) >= CHUNK_SIZE:
            _delete_button_flair(user_id36s)
            user_id36s = set()

    if user_id36s:
        _delete_button_flair(user_id36s)

    ButtonPressByUser._cf.truncate()
    reset_button()
