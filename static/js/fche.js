/* Comportamientos comunes: aviso de cambios sin guardar (DA-03) y error/reintento de HTMX (DA-05). */
(function () {
  "use strict";
  var sucio = false;

  function marcar(e) {
    if (e.target.closest("form[data-aviso-cambios]")) sucio = true;
  }
  document.addEventListener("input", marcar);
  document.addEventListener("change", marcar);

  // Al enviar el formulario ya no hay cambios pendientes.
  document.addEventListener("submit", function () { sucio = false; });

  // «← Volver» y cerrar la pestaña avisan si hay cambios sin guardar. Volver nunca modifica datos.
  document.addEventListener("click", function (e) {
    var enlace = e.target.closest("a.volver");
    if (enlace && sucio && !window.confirm("Hay cambios sin guardar. ¿Salir de todos modos?")) e.preventDefault();
  });
  window.addEventListener("beforeunload", function (e) {
    if (sucio) { e.preventDefault(); e.returnValue = ""; }
  });

  // Error de una sección cargada con HTMX: mensaje claro y botón para reintentar.
  var ultima = null;
  document.addEventListener("htmx:beforeRequest", function (e) { ultima = e.detail.elt; });
  function mostrarError() {
    var caja = document.getElementById("error-htmx");
    if (caja) caja.hidden = false;
  }
  document.addEventListener("htmx:responseError", mostrarError);
  document.addEventListener("htmx:sendError", mostrarError);
  document.addEventListener("click", function (e) {
    if (e.target.id !== "reintentar") return;
    document.getElementById("error-htmx").hidden = true;
    if (ultima && window.htmx) window.htmx.trigger(ultima, ultima.getAttribute("hx-trigger") ? ultima.getAttribute("hx-trigger").split(" ")[0] : "click");
    else window.location.reload();
  });
})();
