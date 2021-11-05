function get_recipient() {
    $.ajax({
        url: "/user/get_recipients",
        contentType: "application/json",
        dataType: "json",
        success: function (data, status) {
            console.log("status " + status);
            items = data;
            $.each(items, function (i, item) {
                $('#recipient').append($('<option>', {
                    value: item.id,
                    text: item.email
                }));
            });
            loaded = true;
        },
        error: function (a, b, c) {
            console.log(a + " " + b + " " + c)
        }
    });
}

$(document).ready(function () {
    get_recipient();
    $.get('/api/message/draft/all', buildTable)
});

function buildTable(data) {
    var table = document.getElementById('draftsTable')

    if (data.length == 0) {
        table.innerHTML = "No drafts!"
        return
    }

    table.innerHTML = `<thead class="thead-dark">
        <tr class="bg-info">
        <th scope="col">Recipient</th>
        <th scope="col">E-mail</th>
        <th scope="col">Text</th>
        <th scope="col">Actions</th>
    </tr>
    </thead>`

    for (var i = 0; i < data.length; i++) {
        msg = data[i]
        user = ""
        $.ajax({
            url: '/api/user/' + msg.recipient,
            type: 'GET',
            async: false,
            dataType: 'json',
            success: function (response) { user = response }
        })

        if (msg.media) {
            msg.text += `<br><a href={{ url_for("static", filename="user_uploads/MEDIA") }}>View attachment</a>`.replace("MEDIA", msg.media)
        }

        var row = `<tr>
                        <td>${user.firstname + " " + user.lastname}</td>
                        <td>${user.email}</td>
                        <td>${msg.text}</td>
                        <td><input id="removeattachment" type="button" value="Purge attachment" onclick="removeAttachment(${msg.message_id})" />
                            <input id="editdraft" type="button" value="Edit" onclick="editDraft(${msg.message_id})" />
                            <input id="deldraft" type="button" value="Delete" onclick="deleteDraft(${msg.message_id})" /></td>
                  </tr>`

        table.innerHTML += row
    }
}

function deleteDraft(draft_id) {
    $.ajax({
        url: '/api/message/draft/' + draft_id,
        type: 'DELETE',
        success: function () {
            alert("Draft deleted")
            location.reload(true)
        },
    })
}

function removeAttachment(draft_id) {
    $.ajax({
        url: '/api/message/draft/' + draft_id + '/attachment',
        type: 'DELETE',
        success: function () {
            location.reload(true)
        },
    })
}

function editDraft(draft_id) {
    $.ajax({
        url: '/api/message/draft/' + draft_id,
        type: 'GET',
        dataType: 'json',
        success: function (response) {
            console.log(response)
            var text = document.getElementById('text')
            var recipient = document.getElementById('recipient')
            var draft_hidden_field = document.getElementById('draft_id')

            text.value = response.text
            recipient.value = response.recipient
            draft_hidden_field.value = draft_id
        }
    })
}