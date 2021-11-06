function get_day_message(day, month, year) {
  console.log(month);
  $.get('/api/calendar/' + day + "/" + month + "/" + year, function (data) { write_message(data, day, month, year); });
}

function write_message(data, day, month, year) {
  console.log(data)

  // Set model up to read message
  var modal = document.getElementById("modal_read");
  var modal_text = document.getElementById("modal_read_text");
  var btn = document.getElementById("myBtn");
  var span = document.getElementsByClassName("close")[0];
  modal.style.display = "block";
  modal_text.innerHTML = "";

  var int_month = parseInt(month, 10) + 1;
  if (data.length == 0) {
    var display_html = `<h4>No messages for the day: ${day}/${int_month}/${year}</h4>`
    modal_text.innerHTML += display_html;
  } else {
    var display_html = `<h3>Your daily messages</h3><hr>`
    for (var i = 0; i < data.length; i++) {
      current_msg = data[i];
      var text = current_msg.future ? "Will be sent at" : "Sent at";
      display_html += `
              <h4> ${text} ${current_msg.delivered}</h4>
              <h5>Recipient: ${current_msg.email}</h5><br>
              ${current_msg.text}<br><hr>
              `;
      if (current_msg.candelete) {
        display_html += `<div><button type="button" class="btn btn-danger" onclick="delete_and_reload(${current_msg.message_id},${day}, ${month}, ${year})">Withdraw</button></div></br>`;
      }
    }
    modal_text.innerHTML += display_html;
  }


  // Set up modal closing
  span.onclick = function () {
    modal.style.display = "none";
  }
  window.onclick = function (event) {
    if (event.target == modal) {
      modal.style.display = "none";
    }
  }
}

function delete_and_reload(msg_id, day, month, year) {
  $.ajax({
    url: '/api/lottery/message/delete/' + msg_id,
    type: 'DELETE',
    dataType: "json",
    success: function (data) {
      var msg = data.message_id == -1 ? "Ops something went wrong, take a look at delivery date" : "Message deleted!";

      alert(msg);
      get_day_message(day, month, year);
    },
  });

}

const date = new Date();

const renderCalendar = () => {
  date.setDate(1);

  const monthDays = document.querySelector(".days");

  const lastDay = new Date(
    date.getFullYear(),
    date.getMonth() + 1,
    0
  ).getDate();

  const prevLastDay = new Date(
    date.getFullYear(),
    date.getMonth(),
    0
  ).getDate();

  const firstDayIndex = date.getDay();

  const lastDayIndex = new Date(
    date.getFullYear(),
    date.getMonth() + 1,
    0
  ).getDay();

  const nextDays = 7 - lastDayIndex - 1;

  const months = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
  ];

  document.querySelector(".date h1").innerHTML = months[date.getMonth()];

  document.querySelector(".date p").innerHTML = date.getFullYear();

  let days = "";

  for (let x = firstDayIndex; x > 0; x--) {
    days += `<div class="prev-date">${prevLastDay - x + 1}</div>`;
  }

  for (let i = 1; i <= lastDay; i++) {
    if (
      i === new Date().getDate() &&
      date.getMonth() === new Date().getMonth()
    ) {
      days += `<div class="today"><button class="btn btn-outline-white" id="myBtn" onclick="get_day_message('${i}', '${date.getMonth()}', '${date.getFullYear()}')">${i}</button></div>`;
    } else {
      days += `<div><button class="btn btn-outline-primary" onclick="get_day_message('${i}', '${date.getMonth()}', '${date.getFullYear()}')">${i}</button></div>`;
    }
  }

  for (let j = 1; j <= nextDays; j++) {
    days += `<div class="next-date">${j}</div>`;
    monthDays.innerHTML = days;
  }
};

document.querySelector(".prev").addEventListener("click", () => {
  date.setMonth(date.getMonth() - 1);
  renderCalendar();
});

document.querySelector(".next").addEventListener("click", () => {
  date.setMonth(date.getMonth() + 1);
  renderCalendar();
});

renderCalendar();