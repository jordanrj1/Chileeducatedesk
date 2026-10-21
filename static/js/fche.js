/* Comportamientos comunes:
   - aviso de cambios sin guardar (DA-03);
   - borrador en la pestaña si la sesión vence o el servidor falla (AC-E2, AC-E3, UI-E6), con el nombre elegido en los buscadores;
   - un solo envío por formulario aunque se haga doble clic (UI-E1);
   - Enter en el cuadro de «+ Crear sector» crea el sector en vez de enviar el formulario;
   - «Tipo de registro» de una persona: marcar un tipo muestra su sección;
   - barra de filtros de los listados: dirección sin campos vacíos y «Más filtros» que se cierra con Esc;
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
      // buscadores: también el nombre elegido, para poder volver a mostrarlo (la opción puede no estar en la página)
      if (el.tagName === "SELECT" && el.hasAttribute("data-selector") && el.selectedIndex >= 0 && el.value) {
        var o = el.options[el.selectedIndex];
        datos[el.name + "::texto"] = o.getAttribute("data-texto") || o.textContent;
      }
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
      if (el.value) return;
      var valor = borrador.datos[el.name];
      if (el.tagName === "SELECT" && el.hasAttribute("data-selector")) {
        var texto = borrador.datos[el.name + "::texto"];
        var existe = Array.prototype.some.call(el.options, function (o) { return o.value === valor; });
        if (!valor || (!existe && !texto)) return;
        if (!existe) { var nueva = new Option(texto, valor); nueva.setAttribute("data-texto", texto); el.appendChild(nueva); }
        el.value = valor;
        el.dispatchEvent(new CustomEvent("fche:restaurado")); // el buscador muestra el nombre
        recuperados++;
        return;
      }
      el.value = valor; recuperados++;
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
    if (!e.target.name) return; // cuadros para filtrar o buscar (sin nombre): no son datos del formulario
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

  // Barra de filtros de los listados (generico/_filtros.html). Sin JavaScript todo funciona igual; con él:
  // la dirección queda sin los campos vacíos ni los valores predeterminados (así «← Volver» y «Exportar» la llevan limpia),
  // y «Más filtros» se cierra con Esc o con un clic fuera.
  document.addEventListener("submit", function (e) {
    var form = e.target;
    if (e.defaultPrevented || !form.matches("form[data-filtros]")) return;
    var limpios = new URLSearchParams();
    new FormData(form).forEach(function (valor, nombre) {
      if (typeof valor !== "string" || valor.trim() === "") return;
      var campo = form.elements[nombre];
      var defecto = campo && campo.getAttribute ? campo.getAttribute("data-defecto") : "";
      if (defecto && valor === defecto) return;
      limpios.append(nombre, valor);
    });
    e.preventDefault();
    var consulta = limpios.toString();
    window.location.assign(window.location.pathname + (consulta ? "?" + consulta : ""));
  });
  document.addEventListener("keydown", function (e) {
    if (e.key !== "Escape") return;
    var abierto = document.querySelector("details.fche-filtros__mas[open]");
    if (!abierto) return;
    abierto.open = false;
    abierto.querySelector("summary").focus();
  });
  document.addEventListener("click", function (e) {
    var dentro = e.target.closest("details.fche-filtros__mas");
    Array.prototype.forEach.call(document.querySelectorAll("details.fche-filtros__mas[open]"), function (d) { if (d !== dentro) d.open = false; });
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

  // Atajo de teclado: «/» o Ctrl/⌘+K llevan al buscador global (salvo que se esté escribiendo en un campo).
  document.addEventListener("keydown", function (e) {
    var destino = e.target, escribiendo = destino.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(destino.tagName);
    var atajo = (e.key === "/" && !escribiendo) || ((e.ctrlKey || e.metaKey) && (e.key === "k" || e.key === "K"));
    if (!atajo) return;
    var buscador = document.getElementById("buscador-global");
    if (!buscador) return;
    e.preventDefault();
    buscador.focus();
    buscador.select();
  });

  // Enter en un cuadro con data-enter-dispara (p. ej. el nombre del sector nuevo) pulsa su botón en vez de enviar
  // el formulario completo, que guardaría sin el sector escrito.
  document.addEventListener("keydown", function (e) {
    if (e.key !== "Enter" || e.isComposing || !e.target.closest) return;
    var cuadro = e.target.closest("[data-enter-dispara]");
    if (!cuadro) return;
    e.preventDefault();
    var boton = document.getElementById(cuadro.getAttribute("data-enter-dispara"));
    if (boton && !boton.disabled) boton.click();
  });

  // «+ Otro territorio» (territorio/_destinos.html): agrega una fila copiando su <template>, sin recargar. Sin JavaScript
  // el botón de <noscript> vuelve a dibujar el formulario con una fila más.
  document.addEventListener("DOMContentLoaded", function () {
    Array.prototype.forEach.call(document.querySelectorAll("[data-agregar-fila]"), function (b) { b.hidden = false; });
  });
  document.addEventListener("click", function (e) {
    var boton = e.target.closest && e.target.closest("[data-agregar-fila]");
    if (!boton) return;
    var caja = boton.closest("[data-filas]");
    var plantilla = caja && caja.querySelector("template[data-filas-plantilla]");
    var total = caja && caja.querySelector("input[name$='-TOTAL_FORMS']");
    var maximo = caja && caja.querySelector("input[name$='-MAX_NUM_FORMS']");
    if (!plantilla || !total) return;
    var n = parseInt(total.value, 10) || 0;
    if (maximo && n >= parseInt(maximo.value, 10)) { boton.disabled = true; return; }
    var envoltorio = document.createElement("div");
    envoltorio.innerHTML = plantilla.innerHTML.replace(/__prefix__/g, String(n));
    var fila = envoltorio.firstElementChild;
    caja.querySelector("[data-filas-lista]").appendChild(fila);
    total.value = n + 1;
    if (window.htmx) window.htmx.process(fila);
    var primera = fila.querySelector("select:not([disabled])");
    if (primera) primera.focus();
  });

  // «Tipo de registro» de una persona (personas/_fichas.html): al marcar o desmarcar un tipo se muestra u oculta su sección,
  // sin recargar. Sin JavaScript, el botón «Mostrar secciones» vuelve a dibujar el formulario sin guardar.
  function mostrarFichas(form) {
    var marcadas = {};
    Array.prototype.forEach.call(form.querySelectorAll("[data-tipo-ficha]"), function (c) { if (c.checked) marcadas[c.getAttribute("data-tipo-ficha")] = true; });
    Array.prototype.forEach.call(form.querySelectorAll("[data-ficha-seccion]"), function (s) { s.hidden = !marcadas[s.getAttribute("data-ficha-seccion")]; });
  }
  document.addEventListener("change", function (e) {
    if (e.target.matches && e.target.matches("[data-tipo-ficha]") && e.target.form) mostrarFichas(e.target.form);
  });
  window.addEventListener("pageshow", function () { // al volver con «Atrás», el navegador puede recordar las casillas
    Array.prototype.forEach.call(document.querySelectorAll("form"), function (f) { if (f.querySelector("[data-tipo-ficha]")) mostrarFichas(f); });
  });

  // Resultados de búsqueda: marca las palabras buscadas (sin distinguir mayúsculas ni tildes).
  function sinTildes(c) { return c.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().charAt(0) || c; }
  function resaltar(raiz, termino) {
    var palabras = termino.split(/\s+/).map(function (p) { return Array.prototype.map.call(p, sinTildes).join(""); }).filter(function (p) { return p.length >= 2; });
    if (!palabras.length) return;
    var recorrido = document.createTreeWalker(raiz, NodeFilter.SHOW_TEXT), nodos = [];
    while (recorrido.nextNode()) { if (recorrido.currentNode.parentNode.closest("a, .small")) nodos.push(recorrido.currentNode); }
    nodos.forEach(function (nodo) {
      var texto = nodo.nodeValue, plano = Array.prototype.map.call(texto, sinTildes).join(""), marcas = [];
      palabras.forEach(function (p) { var i = plano.indexOf(p); while (i !== -1) { marcas.push([i, i + p.length]); i = plano.indexOf(p, i + p.length); } });
      if (!marcas.length) return;
      marcas.sort(function (a, b) { return a[0] - b[0]; });
      var frag = document.createDocumentFragment(), pos = 0;
      marcas.forEach(function (m) {
        if (m[0] < pos) return;
        frag.appendChild(document.createTextNode(texto.slice(pos, m[0])));
        var mark = document.createElement("mark"); mark.textContent = texto.slice(m[0], m[1]); frag.appendChild(mark);
        pos = m[1];
      });
      frag.appendChild(document.createTextNode(texto.slice(pos)));
      nodo.parentNode.replaceChild(frag, nodo);
    });
  }
  document.addEventListener("DOMContentLoaded", function () {
    Array.prototype.forEach.call(document.querySelectorAll("[data-resaltar]"), function (lista) { resaltar(lista, lista.dataset.resaltar || ""); });
  });

  // Avisos de éxito: se cierran solos después de unos segundos (los errores y advertencias se quedan).
  document.addEventListener("DOMContentLoaded", function () {
    Array.prototype.forEach.call(document.querySelectorAll("[data-autocerrar]"), function (aviso) {
      window.setTimeout(function () {
        if (window.bootstrap && window.bootstrap.Alert) window.bootstrap.Alert.getOrCreateInstance(aviso).close();
        else aviso.remove();
      }, 6000);
    });
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

  // Campos que solo aplican según otro campo (p. ej. «Comuna que administra» solo si el tipo es Municipalidad).
  function campoCondicional(raiz) {
    Array.prototype.forEach.call((raiz || document).querySelectorAll("[data-mostrar-si-campo]"), function (el) {
      var form = el.form || document, origen = form.querySelector("[name='" + el.dataset.mostrarSiCampo + "']");
      var caja = el.closest(".fche-campo") || el.parentNode;
      if (!origen || !caja) return;
      function aplicar() {
        var ver = origen.value === el.dataset.mostrarSiValor || !!el.value && origen.value === "";
        caja.hidden = !ver;
      }
      origen.addEventListener("change", aplicar);
      aplicar();
    });
  }
  // Más condiciones: según una casilla marcada o según si otro campo está vacío; y la edad calculada desde la fecha.
  function camposSegun(raiz) {
    var r = raiz || document;
    function enlazar(sel, atributo, regla) {
      Array.prototype.forEach.call(r.querySelectorAll(sel), function (el) {
        var form = el.form || document, origen = form.querySelector("[name='" + el.getAttribute(atributo) + "']");
        var caja = el.closest(".fche-campo") || el.parentNode;
        if (!origen || !caja) return;
        function aplicar() { caja.hidden = !regla(origen); }
        origen.addEventListener("change", aplicar); origen.addEventListener("input", aplicar); aplicar();
      });
    }
    enlazar("[data-mostrar-si-marcado]", "data-mostrar-si-marcado", function (o) { return o.checked; });
    enlazar("[data-ocultar-si-marcado]", "data-ocultar-si-marcado", function (o) { return !o.checked; });
    enlazar("[data-mostrar-si-vacio]", "data-mostrar-si-vacio", function (o) { return !o.value; });
    Array.prototype.forEach.call(r.querySelectorAll("input[data-edad]"), function (el) {
      var aviso = document.createElement("div"); aviso.className = "form-text"; aviso.setAttribute("aria-live", "polite");
      el.insertAdjacentElement("afterend", aviso);
      function calcular() {
        var f = el.value ? new Date(el.value + "T00:00:00") : null, hoy = new Date();
        if (!f || isNaN(f)) { aviso.textContent = ""; return; }
        var edad = hoy.getFullYear() - f.getFullYear(), m = hoy.getMonth() - f.getMonth();
        if (m < 0 || (m === 0 && hoy.getDate() < f.getDate())) edad--;
        aviso.textContent = edad >= 0 ? "Tiene " + edad + (edad === 1 ? " año." : " años.") : "La fecha está en el futuro.";
      }
      el.addEventListener("change", calcular); el.addEventListener("input", calcular); calcular();
    });
  }
  document.addEventListener("DOMContentLoaded", function () { campoCondicional(document); camposSegun(document); });
})();
