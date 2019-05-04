/** YTCTF Platform
 * Copyright © 2018-2019 Evgeniy Filimonov <evgfilim1@gmail.com>
 * See full NOTICE at http://github.com/YummyTacos/YTCTF
 */

$('textarea').on('input', function (){
    $(this)
        .height(0)
        .height(this.scrollHeight);
}).trigger('input');

$('#show-flag').click(function () {
    let flagField = $('#flag');
    let self = $(this);
    let currentType = flagField.attr('type');
    if (currentType === 'password') {
        flagField.attr('type', 'text');
        self.text('Скрыть флаг');
        self.toggleClass('btn-warning btn-success');
    } else {
        flagField.attr('type', 'password');
        self.text('Показать флаг');
        self.toggleClass('btn-warning btn-success');
    }
    return false;
});

$('#page-back').click(function () {
    history.back();
});
