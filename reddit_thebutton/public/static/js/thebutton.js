r.thebutton = {
    init: function() {
        r.debug("in r.thebutton.init()")

        if (r.config.thebutton_websocket) {
            r.debug("got thebutton_websocket")
            this._websocket = new r.WebSocket(r.config.thebutton_websocket)
            this._websocket.on({
                "message:expired": this._onExpired,
                "message:not_started": this._onNotStarted,
                "message:just_expired": this._onJustExpired,
                "message:ticking": this._onTicking,
            }, this)
            this._websocket.start()
        } else {
            r.debug("didn't get thebutton_websocket")
        }

        $('#thebutton').on('click', function(e) {
          e.preventDefault();
          e.stopPropagation();
          $.request('press_button', {"eschaton": "immanentized"}, function(response) {
            console.log(response);
          })
        })
    },

    _onExpired: function(message) {
        var expiredSeconds = message.seconds_elapsed;
        r.debug("timer expired " + expiredSeconds + " ago");
    },

    _onNotStarted: function(message) {
        r.debug("timer hasn't started");
    },

    _onJustExpired: function(message) {
        r.debug("timer just expired");
    },

    _onTicking: function(message) {
        var secondsLeft = message.seconds_left;
        r.debug(secondsLeft + " seconds remaining");
        $('#thebutton-timer').val(parseInt(message.seconds_left, 10));
    },
}

r.thebutton.init()
