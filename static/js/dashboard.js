// Light UX touch: auto-submit the filter form when a dropdown changes,
// so filtering feels instant without needing a JS framework or extra
// "Apply" click. The search text field still waits for Enter/click so
// typing doesn't refresh the page on every keystroke.
document.addEventListener("DOMContentLoaded", function () {
    var form = document.getElementById("filter-form");
    if (!form) return;

    ["data_category", "legal_basis", "international"].forEach(function (id) {
        var field = document.getElementById(id);
        if (field) {
            field.addEventListener("change", function () {
                form.submit();
            });
        }
    });
});
