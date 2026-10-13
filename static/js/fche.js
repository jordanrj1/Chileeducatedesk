/* Comportamientos comunes:
   - aviso de cambios sin guardar (DA-03);
   - borrador en la pestaña si la sesión vence o el servidor falla (AC-E2, AC-E3, UI-E6);
   - un solo envío por formulario aunque se haga doble clic (UI-E1);
   - error de una sección cargada con HTMX, con «Reintentar» (DA-05). */
(function () {
  "use strict";
  var sucio = false;
  var PREFIJO = "fche:borrador:";
  var almacen = window.sessionStorage; // por pestaña: se borra al cerrarla (datos personales en equipos compartidos)

  function claveDe(form) { return PREFIJO + window.location.pathname + window.location.search + "#" + (form.id || form.getAttribute("action") || ""); }

  function camposGuardables(form) {
    return Array.prototype.filter.call(form.elements, function (el) {
      return el.name && el.name !== "csrfmiddlewaretoken" && el.name !== "_version" && el.type !== "password" && el.type !== "file" && el.type !== "submit" && el.type !== "button" && el.type !== "hidden";
    });
  }

  function guardarBorrador(form) {
    var datos = {};
    camposGuardables(form).forEach(function (el) {
      if (el.type === "checkbox" || el.type === "radio") { if (el.checked) datos[el.name] = el.value; }
      else datos[el.name] = el.value;
    });
    try { almacen.setItem(claveDe(form), JSON.stringify({ datos: datos, enviado: false })); } catch (e) { /* sin espacio: se ignora */ }
  }

  function restaurarBorrador(form) {
    var crudo;
    try { crudo = almacen.getItem(claveDe(form)); } catch (e) { return; }
    if (!crudo) return;
    var borrador = JSON.parse(crudo), recuperados = 0;
    camposGuardables(form).forEach(function (el) {
      if (!(el.name in borrador.datos)) return;
      if (el.type === "checkbox" || el.type === "radio") return; // no se fuerza: el servidor manda
      if (!el.value) { el.value = borrador.datos[el.name]; recuperados++; }
    });
    if (recuperados) {
      var aviso = document.createElement("div");
      aviso.className = "alert alert-info d-flex justify-content-between align-items-center";
      aviso.setAttribute("role", "status");
      aviso.innerHTML = "<span>Se recuperó lo que habías escrito antes de que se interrumpiera.</span>";
      var descartar = document.createElement("button");
      descartar.type = "button"; descartar.className = "btn btn-sm btn-outline-secondary"; descartar.textContent = "Descartar";
      descartar.addEventListener("click", function () { almacen.removeItem(claveDe(form)); window.location.reload(); });
      aviso.appendChild(descartar);
      form.parentNode.insertBefore(aviso, form);
      sucio = true;
    }
  }

  function marcar(e) {
    var form = e.target.closest("form[data-aviso-cambios]");
    if (form) { sucio = true; guardarBorrador(form); }
  }
  document.addEventListener("input", marcar);
  document.addEventListener("change", marcar);

  document.addEventListener("submit", function (e) {
    var form = e.target;
    // UI-E1: un solo envío. El botón pulsado conserva su nombre y valor.
    if (form.dataset.enviando === "1") { e.preventDefault(); return; }
    form.dataset.enviando = "1";
    var boton = e.submitter;
    if (boton && boton.name) {
      var oculto = document.createElement("input");
      oculto.type = "hidden"; oculto.name = boton.name; oculto.value = boton.value;
      form.appendChild(oculto);
    }
    window.setTimeout(function () {
      Array.prototype.forEach.call(form.querySelectorAll("button[type=submit], button:not([type]), input[type=submit]"), function (b) { b.disabled = true; });
    }, 0);
    sucio = false;
    if (form.matches("[data-aviso-cambios]")) {
      try {
        var crudo = almacen.getItem(claveDe(form));
        if (crudo) { var b = JSON.parse(crudo); b.enviado = true; almacen.setItem(claveDe(form), JSON.stringify(b)); }
      } catch (err) { /* nada */ }
    }
    if (form.matches("[data-cerrar-sesion]")) { try { almacen.clear(); } catch (err) { /* nada */ } }
  });

  // Volver con «Atrás» del navegador: el formulario vuelve a estar disponible.
  window.addEventListener("pageshow", function () {
    Array.prototype.forEach.call(document.querySelectorAll("form[data-enviando='1']"), function (f) {
      delete f.dataset.enviando;
      Array.prototype.forEach.call(f.querySelectorAll("[disabled]"), function (b) { if (b.type === "submit" || b.tagName === "BUTTON") b.disabled = false; });
    });
  });

  document.addEventListener("DOMContentLoaded", function () {
    // Se guardó con éxito: los borradores ya enviados no se necesitan.
    if (document.body.dataset.guardado === "1") {
      for (var i = almacen.length - 1; i >= 0; i--) {
        var k = almacen.key(i);
        if (k && k.indexOf(PREFIJO) === 0) {
          try { if (JSON.parse(almacen.getItem(k)).enviado) almacen.removeItem(k); } catch (e) { almacen.removeItem(k); }
        }
      }
    }
    Array.prototype.forEach.call(document.querySelectorAll("form[data-aviso-cambios]"), restaurarBorrador);
  });

  // «← Volver» y cerrar la pestaña avisan si hay cambios sin guardar. Volver nunca modifica datos.
  document.addEventListener("click", function (e) {
    var enlace = e.target.closest("a.volver");
    if (!enlace || !sucio) return;
    if (!window.confirm("Hay cambios sin guardar. ¿Salir de todos modos?")) { e.preventDefault(); return; }
    Array.prototype.forEach.call(document.querySelectorAll("form[data-aviso-cambios]"), function (f) { almacen.removeItem(claveDe(f)); });
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
