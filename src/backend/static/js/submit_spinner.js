$(document).ready(function($) {
    const dumpButton = $('.submit-button');
    const dumpText = $('.submit-button-text');
    const spinner = $('.spinner-border');
    dumpButton.click(function () {
        $(this).prop('disabled', true);
        dumpText.text(dumpText.data('send-text'));
        spinner.show();
    });
})