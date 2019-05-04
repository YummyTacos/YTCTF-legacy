/** YTCTF Platform
 * Copyright © 2018-2019 Evgeniy Filimonov <evgfilim1@gmail.com>
 * See full NOTICE at http://github.com/YummyTacos/YTCTF
 */

const form = $('form');
const formData = form.serialize();

$(window).on('beforeunload', function(e) {
    if (form.serialize() !== formData) {
        return 'Вы уверены, что хотите покинуть страницу? Изменения не будут сохранены.';
    }
    e = null;
});

form.on('submit', function() {
    $(window).off('beforeunload');
    return true;
});