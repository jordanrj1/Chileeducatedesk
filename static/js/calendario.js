/* Calendario de actividades (/calendario): muestra la agenda vigente por mes, semana o lista con FullCalendar,
   que está guardado en static/vendor (sin internet). Un clic en un evento abre la actividad; en pantallas
   angostas parte en la vista de lista. */
document.addEventListener("DOMContentLoaded", function () {
  var el = document.getElementById("calendario");
  if (!el || !window.FullCalendar) return;
  var estado = document.getElementById("f-estado");
  var historicas = document.getElementById("f-historicas");
  var extras = ["zona", "responsable", "organizacion"].map(function (n) { return [n, document.getElementById("f-" + n)]; });
  var cal = new FullCalendar.Calendar(el, {
    locale: "es", firstDay: 1, initialView: window.innerWidth < 768 ? "listWeek" : "dayGridMonth",
    height: "auto", navLinks: true, nowIndicator: true,
    headerToolbar: { left: "prev,next today", center: "title", right: "dayGridMonth,timeGridWeek,listWeek" },
    eventTimeFormat: { hour: "2-digit", minute: "2-digit", hour12: false },
    events: function (info, ok, fail) {
      var q = new URLSearchParams({ start: info.startStr, end: info.endStr });
      if (estado.value) q.set("estado", estado.value);
      if (historicas.checked) q.set("historicas", "1");
      extras.forEach(function (par) { if (par[1] && par[1].value) q.set(par[0], par[1].value); });
      fetch(el.dataset.eventos + "?" + q.toString(), { credentials: "same-origin" })
        .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); }).then(ok).catch(fail);
    },
    // F26 P: el título del evento es corto; el estado, el proyecto (si es tarea) y el lugar van en el detalle al pasar el mouse
    eventDidMount: function (a) {
      var x = a.event.extendedProps;
      a.el.title = [a.event.title, x.estado, x.proyecto ? "Proyecto: " + x.proyecto : "", x.lugar].filter(Boolean).join(" · ");
    },
  });
  cal.render();
  estado.addEventListener("change", function () { cal.refetchEvents(); });
  historicas.addEventListener("change", function () { cal.refetchEvents(); });
  extras.forEach(function (par) { if (par[1]) par[1].addEventListener("change", function () { cal.refetchEvents(); }); });
  // «Aplicar filtros» (o Enter) vuelve a pedir los eventos sin recargar la página y cierra el panel «Filtros»
  var form = document.getElementById("filtros-calendario");
  if (form) form.addEventListener("submit", function (e) {
    e.preventDefault();
    var mas = form.querySelector("details[open]");
    if (mas) mas.open = false;
    cal.refetchEvents();
  });
});
