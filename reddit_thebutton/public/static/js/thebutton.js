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
      r.thebutton._msLeft = Math.max(0, r.thebutton._msLeft - 10);
    },

    init: function() {
        if($('#thebutton').length === 0) {
          return;
        }

        this._chart = new google.visualization.PieChart($('.thebutton-pie').get(0));
        this._msLeft = 0;
        this._msgSecondsLeft = 0;
        this._tickTime = '';
        this._tickMac = '';
        this._lastMsLeft = Infinity;

        // Direct to the textNode for perf
        this._timerTextNodes = [
          $('#thebutton-s-10s').get(0).childNodes[0],
          $('#thebutton-s-1s').get(0).childNodes[0],
          $('#thebutton-s-100ms').get(0).childNodes[0],
          $('#thebutton-s-10ms').get(0).childNodes[0]
        ];

        r.debug("in r.thebutton.init()")
        this._started = false;

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

        var $theButtonContainer = $('#thebutton').parent();

        $theButtonContainer.on('click', function(e) {
          var $el = $(this);
          if ($el.is('.active.locked')) {
            $el.addClass('unlocking').removeClass('locked');
            setTimeout(function() {
              $el.removeClass('unlocking').addClass('unlocked');
            }, 300);
          }
        });

        $('#thebutton').on('click', function(e) {
          e.preventDefault();
          e.stopPropagation();

          if ($theButtonContainer.hasClass('pressed')) {
            return;
          }

          r.thebutton._countdownInterval = window.clearInterval(r.thebutton._countdownInterval);
          r.thebutton._setTimer(60000);
          var params = {
            seconds: $('#thebutton-timer').val(),
            prev_seconds: r.thebutton._msgSecondsLeft,
            tick_time: r.thebutton._tickTime,
            tick_mac: r.thebutton._tickMac
          };
          $.request('press_button', params, function(response) {
            console.log(response);
          });

          $theButtonContainer.addClass('pressed').removeClass('unlocked');

          r.thebutton.pulse();
        })
    },

    _drawPie: function(msLeft, msTotal) {
      var msSpent = msTotal - msLeft;
      var data = google.visualization.arrayToDataTable([
        ['', ''],
        ['gone', msSpent],
        ['remaining', msLeft],
      ]);

      var options = {
        chartArea: {
          top: 0,
          left: 0,
          width: 70,
          height: 70,
        },
        pieSliceBorderColor: 'transparent',
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
        $('.thebutton-wrap').removeClass('active').addClass('complete');
        r.thebutton._countdownInterval = window.clearInterval(r.thebutton._countdownInterval);
        r.thebutton._setTimer(0);
    },

    _onNotStarted: function(message) {
        r.debug("timer hasn't started");
    },

    _onJustExpired: function(message) {
        r.debug("timer just expired");
        $('.thebutton-wrap').removeClass('active').addClass('complete');

        $el = $('#thebutton').parent();
        $el.removeClass('unlocked locked logged-out pressed too-new not-active').addClass('denied has-expired');
    },

    _onTicking: function(message) {
        if (!r.thebutton._started) {
          var $theButtonContainer = $('#thebutton').parent();
          if ($theButtonContainer.is('.not-active, .locked')) {
            $theButtonContainer.removeClass('denied not-active').addClass('active locked');
          }
          r.thebutton._started = true;
          r.thebutton._countdownInterval = window.setInterval(r.thebutton._countdown, 10);
        }

        var secondsLeft = message.seconds_left;
        this._tickTime = message.now_str;
        this._msgSecondsLeft = secondsLeft;
        this._tickMac = message.tick_mac;
        var numParticipants = message.participants_text;
        var msLeft = secondsLeft * 1000;

        if (msLeft > r.thebutton._lastMsLeft) {
          this.pulse2();
        }
        r.thebutton._lastMsLeft = msLeft;

        r.thebutton._msLeft = secondsLeft * 1000;
        if (!r.thebutton._countdownInterval) {
          this._countdownInterval = window.setInterval(r.thebutton._countdown, 10);
        }

        r.debug(secondsLeft + " seconds remaining");
        r.debug(numParticipants + " users have pushed the button");
        $('#thebutton-timer').val(parseInt(message.seconds_left, 10));
        $('.thebutton-participants').text(message.participants_text);
    },

    // blue pulse on all three divs when user clicks the button
    pulse: function() {
      $els = $('.thebutton-container, .thebutton-pie-container');
      $els.removeClass('pulse pulse2');

      setTimeout(function() {
        $els.addClass('pulse');
      },1)
    },

    // grey pulse on center div when timer resets from another user
    pulse2: function() {
      var $el = $('.thebutton-pie-container');
      var self = this;

      $el.removeClass('pulse pulse2');

      setTimeout(function() {
        $el.addClass('pulse2');
      }, 1);
    },

    _testState: function(state, msLeft) {
      msLeft = msLeft || 60000;

      $el = $('#thebutton').parent();
      var stateClasses = 'denied logged-out too-new has-expired pressed locked unlocked';
      $el.removeClass(stateClasses);
      r.thebutton._msLeft = msLeft;
      r.thebutton.pulse();

      switch (state) {
        case 'logged-out':
          $el.addClass('denied logged-out');
        break;
        case 'too-new':
          $el.addClass('denied too-new');
        break;
        case 'has-expired':
          $el.addClass('denied has-expired');
        break;
        case 'pressed':
          $el.addClass('pressed');
        break;
        case 'unlocked':
          $el.addClass('unlocked');
        break;
        case 'locked':
        default:
          $el.addClass('locked');
        break;
      }
    },
}

$(function() {
  r.thebutton.init();
});