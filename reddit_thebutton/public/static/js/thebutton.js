r.thebutton = {
    init: function() {
        this._chart = new google.visualization.PieChart($('.thebutton-pie').get(0));

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
          var secondsLeft = $('#thebutton-timer').val()
          $.request('press_button', {"seconds": secondsLeft}, function(response) {
            console.log(response);
          })
        })
    },

    _drawPie: function(secondsLeft) {
      var totalSeconds = 60;
      var secondsSpent = totalSeconds - secondsLeft;
      var data = google.visualization.arrayToDataTable([
        ['', ''],
        ['gone', secondsSpent],
        ['remaining', secondsLeft],
      ]);

      var options = {
        legend: 'none',
        pieSliceText: 'none',
        slices: {
          0: { color: '#C8C8C8' },
          1: { color: '#4A4A4A' }
        },
        enableInteractivity: false
      };

      this._chart.draw(data, options);
    },

    _onExpired: function(message) {
        var expiredSeconds = message.seconds_elapsed;
        r.debug("timer expired " + expiredSeconds + " ago");
        $('.thebutton-wrap').removeClass('c-hidden').addClass('complete');
        $('#thebutton-timer').val(0);
        r.thebutton._drawPie(0);
    },

    _onNotStarted: function(message) {
        r.debug("timer hasn't started");
    },

    _onJustExpired: function(message) {
        r.debug("timer just expired");
        $('.thebutton-wrap').removeClass('c-hidden').addClass('complete');
    },

    _onTicking: function(message) {
        var secondsLeft = message.seconds_left;
        var numParticipants = message.participants_text;

        r.debug(secondsLeft + " seconds remaining");
        r.debug(numParticipants + " users have pushed the button");
        r.thebutton._drawPie(parseInt(secondsLeft, 10));
        $('#thebutton-timer').val(parseInt(message.seconds_left, 10));
        $('.thebutton-wrap').removeClass('c-hidden complete');
        $('.thebutton-participants').text(message.participants_text);
    },
}

r.thebutton.init()
