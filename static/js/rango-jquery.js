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

    $('.rango-add').click(function () {
        var catid = $(this).attr('data-catid');
        var url = $(this).attr('data-url');
        var title = $(this).attr('data-title');
        var me = $(this);
        $.get('/rango/add/', {
            category_id: catid,
            url: url, title: title
        }, function (data) {
            $('#pages').html(data);
            me.hide();
        });
    });
});