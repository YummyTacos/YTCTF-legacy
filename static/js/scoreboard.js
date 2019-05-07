/** YTCTF Platform
 * Copyright © 2018-2019 Evgeniy Filimonov <evgfilim1@gmail.com>
 * See full NOTICE at http://github.com/YummyTacos/YTCTF
 */

const show_all = $('#show-all');

function escapeHTML(s) {
    return (s+'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

function generateRow(userData) {
    let t = '';
    if (userData.is_self) {
        t = ' scoreboard-self';
    }
    return `
<div class="scoreboard-row${t}">
    <div class="scoreboard-info">
        <a class="scoreboard-user" href="/user/${userData.user_id}">
            ${escapeHTML(userData.username)}
        </a>
        <div class="scoreboard-extra">${escapeHTML(userData.extra)}</div>
    </div>
    <div class="scoreboard-points">${userData.points}</div>
</div>`;
}

function getData() {
    let link = '/api/internal/scoreboard';
    if (show_all.is(':checked')) {
        link += '?type=all'
    }
    $.get(link).done(function (data) {
        const scoreboard = $('#scoreboard');
        scoreboard.removeClass('scoreboard-loading');
        scoreboard.empty();
        for (let i = 0; i < data.length; i++) {
            const row = generateRow(data[i]);
            scoreboard.append(row);
        }
        if (data.length === 0) {
            scoreboard.append('<p class="empty-set"><i>Список пуст</i></p>');
        }
    });
}

function worker() {
    getData();
    setTimeout(worker, 5000);
}

show_all.click(function () {
    getData();
});

worker();