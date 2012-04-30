var board_size = 20;

var disconnect_timeout = null;
var disconnect_looking = false;

var allow_notification = false;
var default_title = null;

$().ready(function () {

    default_title = document.title;

    $(window).mousemove(function () {
        allow_notification = false;
        setNotification();
    }).blur(function () {
        allow_notification = true;
    });

    $('#link').val(document.location.protocol + '//' + document.location.host + '/game/' + game.id).mousemove(function () {
        this.focus();
        this.select();
    });

    html = '<table cellpadding="0" cellspacing="0">';
    for (var row = 0; row < board_size; row++) {
        html += '<tr>';
        for (var col = 0; col < board_size; col++) {
            html += '<td id="m' + (board_size * row + col) + '" class="move"></td>';
        }
        html += '</tr>';
    }
    html += '</table>';
    $('#board').html(html);

    $('.move').click(function () {
        if (game.move == you && game.status == 'ok') {
            $('#move').text('Sending...');
        }
        $.post('/move', { id: game.id, to: parseInt($(this).attr('id').substring(1)) });
        return false;
    }).mouseenter(function () {
        $(this).addClass(my_symbol + '-gray');
    }).mouseleave(function () {
        $(this).removeClass(my_symbol + '-gray');
    });

    $('#message').keypress(function (event) {
        if (event.which == '13') {
            event.preventDefault();
            $("#send").click();
        }
    });

    $("#send").click(function () {
        $.post('/chat', { id: game.id, message: $('#message').val() });
        $('#message').val('');
    });

    $("#request").click(function () {
        $(this).hide();
        $('#move').text('Wait for a game creating...');
        $.post('/system', { id: game.id, request: true });
    });

    updateGame();
    if (token != 'null') {
        var channel = new goog.appengine.Channel(token);
        channel.open({
            onopen: onOpened,
            onmessage: onMessage,
            onerror: pageReload,
            onclose: pageReload
        });
    } else {
        $('#move').text('You are not a part of this game.');
        $('.move').removeClass('move').unbind('click mouseenter');
    }
});

function pageReload() {
    document.location.reload();
}

function gotoGame(id) {
    document.location = '/game/' + id;
}

function onOpened() {
    $.post('/system', { id: game.id, opened: true });
    statusSend();
    setInterval(statusSend, 9000);
}

function statusSend(s) {
    if (!s) {
        s = 'ok';
    }
    if (!disconnect_looking && game.move != null) {
        disconnect_looking = true;
        disconnect_timeout = setTimeout(function () {
            game.status = 'off';
            statusUpdate();
            disconnect_looking = false;
        }, 30000);
    }
    $.post('/system', { id: game.id, status: s });
}

function statusUpdate() {
    switch (game.status) {
        case 'off':
            $('#move').text('Partner disconnected!');
            break;
        case 'afk':
            $('#move').text('Partner go away from keyboard!');
            break;
        case 'ok':
            break;
        default:
            $('#move').text('Your version is old!');
            break;
    }
}

function onMessage(message) {
    data = JSON.parse(message.data);
    if (data.status) {
        clearTimeout(disconnect_timeout);
        disconnect_looking = false;
    }
    if ((data.move != null && data.move != game.move) ||
        (data.chat != null && data.chat != game.chat) ||
        (data.status != null && data.status != game.status)) {
        setNotification();
    }
    for (key in data) {
        game[key] = data[key];
    }
    updateGame();
    statusUpdate();
}

function setNotification() {
    var text = '';
    if (allow_notification) {
        text = '( ! ) ' + default_title;
    } else {
        text = default_title;
    }
    if (document.title != text) {
        document.title = text;
    }
}

function updateGame() {
    if (game.request) {
        gotoGame(game.request);
    }
    for (var i = 0; i < game.board.length; i++) {
        var symbol = game.board[i];
        if (symbol != ' ') {
            var cell = $('#m' + i);
            if (cell.hasClass('move')) {
                cell.removeClass('move').unbind('click mouseenter');
                var color = (symbol == my_symbol ? 'green' : 'red')
                cell.addClass(symbol + '-' + color);
            }
        }
    }
    if (game.last) {
        $('.last').removeClass('last');
        $('#m' + game.last).addClass('last');
    }
    if (game.winner) {
        $('.last').removeClass('last');
        for (var i = 0; i < game.winner.count; i++) {
            var pos = board_size * (game.winner.row + i * game.winner.dy) + (game.winner.col + i * game.winner.dx);
            $('#m' + pos).addClass('last')
        }
        var winner = game.board[board_size * game.winner.row + game.winner.col];
        $('#move').text('You are ' + (my_symbol == winner ? 'WINNER!' : 'LOSER!'));
        $('.move').removeClass('move').unbind('click mouseenter');
        if ($('#request').is(':hidden')) {
            $('#request').fadeIn();
        }
    } else {
        if (game.move != null) {
            $('#move').text((game.move == you ? 'You' : 'Partner thinking'));
        } else {
            $('#move').text('There is no second player in this game');
        }
    }
    var chat = $('#chat');
    var text = game.chat;
    text = text.replace(/(x|o):/g, '<b class="chat-$1">$1:</b>');
    text = text.replace(/\n/g, '<br />');
    chat.html(text);
    $('.chat-x').css('color', (my_symbol == 'x' ? '#6c6' : '#c66'));
    $('.chat-o').css('color', (my_symbol == 'o' ? '#6c6' : '#c66'));
    chat.scrollTop(chat[0].scrollHeight);
    
    $('#actions').text(game.actions);
}
