// JavaScript for disabling form submissions if there are invalid fields
function form_validate() {
    'use strict'

    // Fetch all the forms we want to apply custom Bootstrap validation styles to
    var forms = document.querySelectorAll('.needs-validation')

    // Loop over them and prevent submission
    Array.prototype.slice.call(forms)
        .forEach(function (form) {
            form.addEventListener('submit', function (event) {
                if (!form.checkValidity()) {
                    event.preventDefault()
                    event.stopPropagation()
                }

                form.classList.add('was-validated')
            }, false)
        })
}

$(document).ready(function () {
    // fadeout flashmessage on click
    $('#flashmessages').click(function () {
        $('#flashmessages').fadeOut('slow');
    });

    // set active class on active menu item
    $('.nav-link').click(function () {
        $('.nav-link').removeClass('active');
        $(this).addClass('active');
    });

});