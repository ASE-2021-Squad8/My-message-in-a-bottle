function get_day_message(day, month, year) {
  console.log(month);
  $.get('/api/calendar/' + day + "/" + month + "/" + year , function (data) { write_message(data, day, month, year); });
}

function write_message(data, day, month, year){
    var messages =  document.getElementById('sentmsg');
    messages.innerHTML = ``
    var int_month = parseInt(month, 10) + 1;
    if(data.length == 0){
      var display_html = `<h4 style="color:red">No messages sent for the day: ${day}/${int_month}/${year}</h4>`
      messages.innerHTML += display_html;
    }
    else{
        var display_html = `<h3 style="color:red">Your daily message</h3>`
        for (var i = 0; i < data.length; i++) {
        current_msg = JSON.parse(data[i]);
        var text = current_msg.future ? "Will be sent at": "Sent at";
        display_html += `
              <h4 style="color:red"> ${text} ${current_msg.hour}:${current_msg.minute}</h4>
              <h4 style="color:black"> Recipient Mail: ${current_msg.email}
              Text message: ${current_msg.text}</h4>
              `;

        
        if(current_msg.candelete){
            display_html += `<div><button onclick="delete_and_reload(${current_msg.message_id},${day}, ${month}, ${year})">Withdraw</button></div></br>`;
        }
        

      }
      messages.innerHTML += display_html;
    }
}

function delete_and_reload(msg_id, day, month, year){
  $.ajax({
    url: '/api/lottery/message/delete/' + msg_id,
    type: 'DELETE',
    dataType: "json",
    success: function (data) {
      var msg = data.message_id == -1 ? "Ops something went wrong, take a look at delivery date": "Message deleted!";

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
      days += `<div class="today"><button id="myBtn" onclick="get_day_message('${i}', '${date.getMonth()}', '${date.getFullYear()}')">${i}</button></div>`;
    } else {
      days += `<div><button onclick="get_day_message('${i}', '${date.getMonth()}', '${date.getFullYear()}')">${i}</button></div>`;
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