// approve or not an action
$(document).ready(function($) {
    $(".not-approved-icon").click(function() {
        if (confirm('Approve this action?')) {
            $.ajax('/api/pull_requests', {
                contentType: 'application/json',
                type: 'POST',
                data: JSON.stringify({
                    'id': $(this).data("action-id"),
                }),
                success: function() {
                    $(document).ajaxStop(function() {
                        location.reload();
                    })
                }
            })
        }
    });
});

// delete an action
$(document).ready(function($) {
    $(".delete-icon").click(function() {
        if (confirm('Delete this action?')) {
            $.ajax('/api/actions', {
                contentType: 'application/json',
                type: 'DELETE',
                data: JSON.stringify({
                    'id': $(this).data("action-id"),
                }),
                success: function() {
                    $(document).ajaxStop(function() {
                        if (window.document.location.toString().includes('/actions')) {
                            location.reload();
                        } else {
                            window.document.location = '/actions';
                        }
                    })
                }
            });
        }
    });
});

// search the actions by a package name
$(document).ready(function($){
    const searchActionInput = $('.search-action');
    searchActionInput.bind('searchAction', function(e) {
        if($(this).val()) {
            window.document.location = '/actions?package=' + $(this).val();
        } else {
            window.document.location = '/actions';
        }

    });
    searchActionInput.keypress(function(e) {
        if (e.keyCode === 13) {
            $(this).trigger('searchAction');
        }
    });
});
