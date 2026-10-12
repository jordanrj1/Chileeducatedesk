document.addEventListener("DOMContentLoaded", function () {
  var el = document.getElementById("calendario");
  if (!el || !window.FullCalendar) return;
  var estado = document.getElementById("f-estado");
  var historicas = document.getElementById("f-historicas");
  var cal = new FullCalendar.Calendar(el, {
    locale: "es", firstDay: 1, initialView: window.innerWidth < 768 ? "listWeek" : "dayGridMonth",
    height: "auto", navLinks: true, nowIndicator: true,
    headerToolbar: { left: "prev,next today", center: "title", right: "dayGridMonth,timeGridWeek,listWeek" },
    eventTimeFormat: { hour: "2-digit", minute: "2-digit", hour12: false },
    events: function (info, ok, fail) {
      var q = new URLSearchParams({ start: info.startStr, end: info.endStr });
      if (estado.value) q.set("estado", estado.value);
      if (historicas.checked) q.set("historicas", "1");
      fetch(el.dataset.eventos + "?" + q.toString(), { credentials: "same-origin" })
        .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); }).then(ok).catch(fail);
    },
    eventDidMount: function (a) { a.el.title = a.event.extendedProps.estado + (a.event.extendedProps.lugar ? " · " + a.event.extendedProps.lugar : ""); },
  });
  cal.render();
  estado.addEventListener("change", function () { cal.refetchEvents(); });
  historicas.addEventListener("change", function () { cal.refetchEvents(); });
});
