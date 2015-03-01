r.thebutton = {

    _setTimer: function(ms) {
      var pad = '00000';
      var msString = (ms > 0 ? ms : 0).toString();
      var msStringPadded = pad.substring(0, pad.length - msString.length) + msString;

      for(var i=0; i < 4; i++) {
        r.thebutton._timerTextNodes[i].nodeValue = msStringPadded[i];
      }

      /* Just often enough to feel smooth but not be rendering all the time */
      if (ms % 100 === 0) {
        r.thebutton._drawPie(ms, 60000);
      }
    },

    _countdown: function() {
      r.thebutton._setTimer(r.thebutton._msLeft);
      r.thebutton._msLeft -= 10;
    },

    init: function() {
        this._chart = new google.visualization.PieChart($('.thebutton-pie').get(0));
        this._msLeft = 0;

        // Direct to the textNode for perf
        this._timerTextNodes = [
          $('#thebutton-s-10s').get(0).childNodes[0],
          $('#thebutton-s-1s').get(0).childNodes[0],
          $('#thebutton-s-100ms').get(0).childNodes[0],
          $('#thebutton-s-10ms').get(0).childNodes[0]
        ];

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
          r.thebutton._countdownInterval = window.clearInterval(r.thebutton._countdownInterval);
          r.thebutton._setTimer(99999);
          $.request('press_button', {"seconds": secondsLeft}, function(response) {
            console.log(response);
          })
        })

        this._countdownInterval = window.setInterval(r.thebutton._countdown, 10);
    },

    _drawPie: function(msLeft, msTotal) {
      var msSpent = msTotal - msLeft;
      var data = google.visualization.arrayToDataTable([
        ['', ''],
        ['gone', msSpent],
        ['remaining', msLeft],
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
        r.thebutton._countdownInterval = window.clearInterval(r.thebutton._countdownInterval);
        r.thebutton._setTimer(0);
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

        r.thebutton._msLeft = secondsLeft * 1000;
        if (!r.thebutton._countdownInterval) {
          this._countdownInterval = window.setInterval(r.thebutton._countdown, 10);
        }

        r.debug(secondsLeft + " seconds remaining");
        r.debug(numParticipants + " users have pushed the button");
        $('#thebutton-timer').val(parseInt(message.seconds_left, 10));
        $('.thebutton-wrap').removeClass('c-hidden complete');
        $('.thebutton-participants').text(message.participants_text);
    },
}

r.thebutton.init();
