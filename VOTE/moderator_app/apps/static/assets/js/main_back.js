

function getCookie(name) {
    var cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        var cookies = document.cookie.split(';');
        for (var i = 0; i < cookies.length; i++) {
            var cookie = jQuery.trim(cookies[i]);
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

function csrfSafeMethod(method) {
    // these HTTP methods do not require CSRF protection
    return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
}

$.ajaxSetup({
    beforeSend: function(xhr, settings) {
        if (!csrfSafeMethod(settings.type) && !this.crossDomain) {
            xhr.setRequestHeader("X-CSRFToken", getCookie("csrftoken"));
        }
    }
});




function refresh_moderator_table(resetPage = false) {
    //console.log('refresh')

    let url = new URL(window.location.href);

    if (resetPage) {
        url.searchParams.set('page', '1');
        window.history.replaceState({}, '', url);
    }

    $.ajax({
        beforeSend: function(request) {
            request.setRequestHeader("X-CSRFToken", getCookie('csrftoken'));
        },
        url : "refresh_moderators",
        type : "POST",
        data : {
                url : url.toString(),
                search : currentSearch
        },

        success : function(data) {
            //console.log("success");
            $("#results_moderators").html(data);
        },

        // handle a non-successful response
        error : function(xhr,errmsg,err) {

            data = xhr.responseJSON
            if (data !== undefined) {
                //console.log(data)
                if ('message' in data) {
                    error = data['message']
                } else {
                    error = errmsg
                }
            } else {
                if(err == "Forbidden") {
                    error = 'You do not have the rights to execute this operation. Please contact the administrator.'
                }
                else {
                    error = 'An unexpected error occured. Please retry. If the issue still occurs, contact your administrator.'
                }

            }

            alertify.error(error);
            return false;
        }
    });
};


function value_edit(session_id) {

    $.ajax({
        beforeSend: function(request) {
            request.setRequestHeader("X-CSRFToken", getCookie('csrftoken'));
        },
        url : "get_modal_edit_value",
        type : "POST",
        data : {
            session_id : session_id

        },

        success : function(data) {
            //console.log("success");
            $("#modal-view").html(data);
            $("#modal-view").show();

            setTimeout(function() {
                    $("#moderator_name").focus();
            }, 200);

            var modal = document.getElementById("modal-view");

            window.onclick = function(event) {
                if (event.target == modal) {
                    close_modal()
                }
            }

        },

        // handle a non-successful response
        error : function(xhr,errmsg,err) {
            alertify.error(errmsg)
        }
    });

}


function save_edit_value(session_id) {

    $.ajax({
        beforeSend: function(request) {
            request.setRequestHeader("X-CSRFToken", getCookie('csrftoken'));
        },
        url : "update_modal_edit_value",
        type : "POST",
        data : {
            session_id : session_id,
            moderator_name : $('#modal-content #moderator_name').val(),
            moderator_email : $('#modal-content #moderator_email').val()

        },

        success : function(data) {
            //console.log("success");
            alertify.success('Moderator Updated')
            close_modal()
            refresh_moderator_table()
        },

        // handle a non-successful response
        error : function(xhr,errmsg,err) {
            data = xhr.responseJSON
            if (data !== undefined) {
                //console.log(data)
                if ('message' in data) {
                    error = data['message']
                } else {
                    error = errmsg
                }
            } else {
                error = 'An unexpected error occured. Please retry. If the issue still occurs, contact your administrator'
            }

            alertify.error(error);

        }
    });

}




