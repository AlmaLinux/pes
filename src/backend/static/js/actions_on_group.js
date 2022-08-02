// delete a group
$(document).ready(function($) {
    $(".delete-icon.delete-group").click(function() {
        if (confirm('Delete this group?')) {
            $.ajax('/api/groups', {
                contentType: 'application/json',
                type: 'DELETE',
                data: JSON.stringify({
                    'id': $(this).data("group-id"),
                }),
                success: function() {
                    $(document).ajaxStop(function() {
                        if (window.document.location.toString().includes('/group_of_actions')) {
                            location.reload();
                        } else {
                            window.document.location = '/group_of_actions';
                        }
                    })
                }
            });
        }
    });
});
