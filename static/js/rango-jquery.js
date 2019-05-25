$(document).ready(function () {
    $("#about-btn").click(function (event) {
        alert("You clicked the button using JQuery!");
    });

    $(".ouch").click(function (event) {
        alert("You clicked me! ouch!");
    })

    $("p").hover(function () {
        $(this).css('color', 'red');
    },
        function () {
            $(this).css('color', 'black');
        });
});