

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
    let url = new URL(window.location.href);

    if (resetPage) {
        url.searchParams.set('page', '1');
        window.history.replaceState({}, '', url);
    }

    const currentSearch = $('#search').val() || '';

    $.ajax({
        beforeSend: function(request) {
            request.setRequestHeader("X-CSRFToken", getCookie('csrftoken'));
        },
        url: "refresh_moderators",
        type: "POST",
        headers: {
            'X-Mobile-View': window.innerWidth < 768 ? 'true' : 'false'
        },
        data: {
            url: url.toString(),
            search: currentSearch
        },

        success: function(data) {
            $("#results_moderators").html(data);


        },

        error: function(xhr, errmsg, err) {
            let error;
            const data = xhr.responseJSON;

            if (data !== undefined) {
                if ('message' in data) {
                    error = data['message'];
                } else {
                    error = errmsg;
                }
            } else {
                if (err === "Forbidden") {
                    error = 'You do not have the rights to execute this operation. Please contact the administrator.';
                } else {
                    error = 'An unexpected error occurred. Please retry. If the issue persists, contact your administrator.';
                }
            }

            alertify.error(error);
            return false;
        }
    });
}


function resend_verification() {
    $.ajax({
        url: "resend_verification",
        type: "POST",
        success: function(data) {
            alertify.success(data.message || 'A verification email has been sent.');
        },
        error: function(xhr, errmsg) {
            const data = xhr.responseJSON;
            alertify.error((data && data.message) || errmsg || 'Unable to resend verification email.');
        }
    });
}



function value_edit(session_id) {

    $.ajax({
        beforeSend: function(request) {
            request.setRequestHeader("X-CSRFToken", getCookie('csrftoken'));
        },
        url : "get_modal_edit_value",
        type : "POST",
                headers: {
            'X-Mobile-View': window.innerWidth < 768 ? 'true' : 'false'
        },
        data : {
            session_id : session_id

        },

        success : function(data) {
            //console.log("success");
            $("#modal-view").html(data);
            $("#modal-view").show();

            setTimeout(function() {
                    const $name = $("#moderator_name");
                    if ($name.length && !$name.prop('readonly')) {
                        $name.focus();
                    }
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


function isCpcModerator(name) {
    return (name || '').trim().toUpperCase() === 'CPC';
}

function validateModeratorFields(name, email) {
    name = (name || '').trim();
    email = (email || '').trim();
    const hasName = !!name;
    const hasEmail = !!email;

    if (!hasName && !hasEmail) {
        return null;
    }
    if (isCpcModerator(name) && hasName) {
        return null;
    }
    if (hasName && hasEmail) {
        return null;
    }
    return 'Moderator name and email must both be filled, or both left empty to remove.';
}


function save_edit_value(session_id) {
    const name = ($('#moderator_name').val() || '').trim();
    const email = ($('#moderator_email').val() || '').trim();
    const validationError = validateModeratorFields(name, email);

    if (validationError) {
        alertify.error(validationError);
        return;
    }

    $.ajax({
        beforeSend: function(request) {
            request.setRequestHeader("X-CSRFToken", getCookie('csrftoken'));
        },
        url : "update_modal_edit_value",
        type : "POST",
        data : {
            session_id : session_id,
            moderator_name: name,
            moderator_email: email

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


