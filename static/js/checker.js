/** YTCTF Platform
 * Copyright © 2018-2019 Evgeniy Filimonov <evgfilim1@gmail.com>
 * See full NOTICE at http://github.com/YummyTacos/YTCTF
 */

function escapeHTML(s) {
    return (s+'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

function generateTask(taskData) {
    let classes = `task-card rounded ${taskData.category}`;
    if (taskData.solved || taskData.authored) {
        classes += ' solved'
    }
    if (taskData.hidden) {
        classes += ' task-hidden'
    }
    let solvedLine = taskData.solved_count;
    const t = solvedLine % 100;
    if (t % 10 === 0 || t % 10 >= 5 || (11 <= t && t <= 14)) {
        solvedLine += ' человек решили';
    } else if (t % 10 === 1) {
        solvedLine += ' человек решил';
    } else {
        solvedLine += ' человека решили';
    }
    return `
<a href="/task/${taskData.id}" class="${classes}">
    <p class="task-name">${escapeHTML(taskData.task)}</p>
    <span class="task-points">${taskData.points}</span>
    <span class="task-category">${taskData.category}</span>
    <br/>
    <span class="people-solved-count">
        ${solvedLine}
    </span>
</a>`;
}

function getData() {
    let link = '/api/internal/tasks';
    const s = window.location.search;
    const filters = $('button.filter-selected');
    if (s === '') {
        link += '?'
    } else {
        link += s + '&'
    }
    for (let i = 0; i < filters.length; i++) {
        link += filters[i].dataset.param + '&';
    }

    $.get(link.slice(0, -1)).done(function (data) {
        const tasks = $('#tasks');
        if (tasks.hasClass('checker-loading')) {
            tasks.toggleClass('checker-loading task-grid');
        }
        tasks.empty();
        if (data === null || data.length === 0) {
            if (!tasks.hasClass('checker-loading')) {
                tasks.toggleClass('checker-loading task-grid');
            }
            tasks.append('<p class="empty-set"><i>Тасков нет, но вы держитесь там</i></p>');
            return
        }
        for (let i = 0; i < data.length; i++) {
            const task = generateTask(data[i]);
            tasks.append(task);
        }
    });
}

function worker() {
    getData();
    setTimeout(worker, 15000);
}

$('button.filter, button.filter-selected').click(function () {
    $(this).toggleClass('filter filter-selected');
    getData();
});

worker();