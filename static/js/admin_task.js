/** YTCTF Platform
 * Copyright © 2018-2019 Evgeniy Filimonov <evgfilim1@gmail.com>
 * See full NOTICE at http://github.com/YummyTacos/YTCTF
 */

const labelForFiles = $('label[for=files]');
const defaultLabel = labelForFiles.text();
const files = $('#files');

function filesOnInput() {
    const self = files[0];
    if (self.files.length === 0) {
        labelForFiles.text(defaultLabel);
    } else {
        let newLabel = '';
        for (let i = 0; i < self.files.length; i++) {
            newLabel += `"${self.files[i].name}" `
        }
        labelForFiles.text(newLabel);
    }
}

files.on('input', filesOnInput);

$('#flag').attr('type', 'password');

$('#clear-file').click(function () {
    $('#files')[0].value = '';
    filesOnInput();
});

filesOnInput();