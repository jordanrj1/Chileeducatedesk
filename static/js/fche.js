/* Comportamientos comunes:
   - aviso de cambios sin guardar (DA-03);
   - borrador en la pestaña si la sesión vence o el servidor falla (AC-E2, AC-E3, UI-E6), con el nombre elegido en los buscadores;
   - un solo envío por formulario aunque se haga doble clic (UI-E1), con «Guardando…» en el botón pulsado (F26 Ra);
   - Enter en un formulario largo pasa al campo siguiente en vez de enviarlo a medias (F26 Ra);
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
    if ((form.getAttribute("method") || "").toLowerCase() === "post" || form.hasAttribute("hx-post")) {
      ponerGuardando(boton && boton.form === form ? boton : form.querySelector("button[type=submit], button:not([type])"));
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

  // F26 Ra: el botón pulsado muestra «Guardando…» con un giro pequeño y aria-busy mientras se envía.
  function ponerGuardando(boton) {
    if (!boton || boton.tagName !== "BUTTON" || boton.hasAttribute("data-texto-original")) return;
    boton.setAttribute("data-texto-original", boton.innerHTML);
    boton.setAttribute("aria-busy", "true");
    boton.innerHTML = '<span class="spinner-border spinner-border-sm fche-guardando" aria-hidden="true"></span> Guardando…';
  }
  function quitarGuardando(raiz) {
    var botones = raiz.matches && raiz.matches("[data-texto-original]") ? [raiz] : [];
    Array.prototype.push.apply(botones, raiz.querySelectorAll("[data-texto-original]"));
    botones.forEach(function (b) {
      b.innerHTML = b.getAttribute("data-texto-original");
      b.removeAttribute("data-texto-original");
      b.removeAttribute("aria-busy");
    });
  }
  function liberar(form) {
    delete form.dataset.enviando;
    Array.prototype.forEach.call(form.querySelectorAll("[disabled]"), function (b) { if (b.type === "submit" || b.tagName === "BUTTON") b.disabled = false; });
    quitarGuardando(form);
  }

  // Volver con «Atrás» del navegador: el formulario vuelve a estar disponible.
  window.addEventListener("pageshow", function () {
    Array.prototype.forEach.call(document.querySelectorAll("form[data-enviando='1']"), liberar);
    quitarGuardando(document);
  });

  // Botones y formularios HTMX que crean o guardan («Crear y elegir», «+ Crear sector», «Crear y seleccionar»):
  // hx-disabled-elt y hx-sync los bloquean mientras se envían; aquí muestran «Guardando…» y, si la respuesta no
  // reemplazó el formulario (error o «Usar existente»), vuelven a su estado.
  document.addEventListener("htmx:beforeRequest", function (e) {
    var elt = e.detail && e.detail.elt;
    if (elt && elt.tagName === "BUTTON" && elt.hasAttribute("hx-post")) ponerGuardando(elt);
  });
  document.addEventListener("htmx:afterRequest", function (e) {
    var elt = e.detail && e.detail.elt;
    if (!elt || !elt.isConnected || !elt.hasAttribute("hx-post")) return;
    if (elt.tagName === "FORM") liberar(elt); else quitarGuardando(elt);
  });

  // F26 Ra: Enter en un formulario largo (con data-aviso-cambios) pasa al campo siguiente: se guarda solo con el botón.
  // En un área de texto sigue siendo salto de línea. Los buscadores (combobox), el buscador general, los filtros y los
  // formularios de una línea (ingreso, buscar) no tienen data-aviso-cambios o se excluyen aquí. Sin JavaScript, lo normal.
  var NO_SALTA = ["submit", "button", "reset", "image", "file", "search", "checkbox", "radio"];
  document.addEventListener("keydown", function (e) {
    if (e.key !== "Enter" || e.isComposing || e.defaultPrevented || e.ctrlKey || e.metaKey || e.altKey) return;
    var el = e.target;
    if (!el || el.tagName !== "INPUT" || !el.form || !el.form.matches("[data-aviso-cambios]")) return;
    if (NO_SALTA.indexOf((el.type || "text").toLowerCase()) !== -1 || el.getAttribute("role") === "combobox" || el.closest("[data-enter-dispara]")) return;
    e.preventDefault();
    var campos = Array.prototype.filter.call(el.form.elements, function (c) {
      return !c.disabled && c.type !== "hidden" && c.tagName !== "FIELDSET" && c.tagName !== "BUTTON" && c.type !== "submit" &&
        !(c.tagName === "SELECT" && c.hasAttribute("data-selector")) && c.getClientRects().length > 0 && c.tabIndex >= 0;
    });
    var siguiente = campos[campos.indexOf(el) + 1];
    if (siguiente) siguiente.focus();
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
  // F26 P1b: con un solo botón «Filtros», cambiar una lista o casilla a la vista la aplica al tiro
  // (sin JavaScript se aplica con «Aplicar filtros» o con Enter en el buscador).
  document.addEventListener("change", function (e) {
    var campo = e.target;
    if (!campo.closest || !campo.closest(".fche-filtros__campo--principal")) return;
    if (!(campo.tagName === "SELECT" || campo.type === "checkbox")) return;
    var form = campo.closest("form[data-filtros]");
    if (!form || !form.querySelector("details.fche-filtros__mas")) return;
    if (form.requestSubmit) form.requestSubmit(); else form.dispatchEvent(new Event("submit", { cancelable: true, bubbles: true }));
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
    campoCondicional(fila); camposSegun(fila); // la fila nueva muestra solo los campos que corresponden
    fila.dispatchEvent(new CustomEvent("htmx:load", { bubbles: true })); // selector.js arma los buscadores de la fila
    var primera = fila.querySelector("select:not([disabled])");
    if (primera) primera.focus();
  });

  // «Tipo de registro» de una persona (personas/_fichas.html): al marcar o desmarcar un tipo se muestra u oculta su sección,
  // sin recargar. Sin JavaScript, el botón «Mostrar secciones» vuelve a dibujar el formulario sin guardar.
  function mostrarFichas(form) {
    var marcadas = {};
    Array.prototype.forEach.call(form.querySelectorAll("[data-tipo-ficha]"), function (c) { if (c.checked) marcadas[c.getAttribute("data-tipo-ficha")] = true; });
    Array.prototype.forEach.call(form.querySelectorAll("[data-ficha-seccion]"), function (s) { s.hidden = !marcadas[s.getAttribute("data-ficha-seccion")]; });
    // F26 P2: lo que ya pide la sección de un tipo marcado no se repite en «Organización y comunidad»
    Array.prototype.forEach.call(form.querySelectorAll("[data-ocultar-si-tipo]"), function (el) {
      var caja = el.closest(".fche-campo");
      if (caja) caja.hidden = el.getAttribute("data-ocultar-si-tipo").split(" ").some(function (t) { return marcadas[t]; });
    });
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
  // data-mostrar-si-valor admite varios valores separados por espacio. Si el campo del que depende está oculto, este también
  // se oculta (p. ej. «Viene por» depende del rol, que depende del tipo de relación).
  function campoCondicional(raiz) {
    Array.prototype.forEach.call((raiz || document).querySelectorAll("[data-mostrar-si-campo]"), function (el) {
      var form = el.form || document, origen = form.querySelector("[name='" + el.dataset.mostrarSiCampo + "']");
      var caja = el.closest(".fche-campo") || el.parentNode;
      if (!origen || !caja) return;
      var valores = (el.dataset.mostrarSiValor || "").split(" ");
      function aplicar() {
        var cajaOrigen = origen.closest(".fche-campo");
        var conDato = el.type === "checkbox" ? el.checked : !!el.value;
        var ver = valores.indexOf(origen.value) !== -1 || conDato && origen.value === "";
        caja.hidden = !ver || !!(cajaOrigen && cajaOrigen.hidden);
        // Si todos los campos de una sección quedan ocultos, también su título (p. ej. «Si es menor de edad»).
        var bloque = caja.closest("fieldset.fche-bloque");
        if (bloque) bloque.hidden = !Array.prototype.some.call(bloque.querySelectorAll(".fche-campo"), function (c) { return !c.hidden; });
      }
      (el.form || origen).addEventListener("change", aplicar);
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
  // La ventana «+ Crear…» llega por HTMX: sus campos condicionales (RUT o documento extranjero) se enlazan al llegar
  document.addEventListener("htmx:afterSwap", function (e) { if (e.target.id === "modal-rapido-contenido") camposSegun(e.target); });
})();

// F25 E5: panel lateral de un participante. Mientras llega el resumen se avisa «Cargando…» (no queda el de otra persona);
// al llegar, el foco pasa al nombre para que el lector de pantalla lo anuncie.
(function () {
  document.addEventListener("htmx:beforeRequest", function (e) {
    var t = e.detail && e.detail.target;
    if (t && t.id === "panel-persona-cuerpo") t.innerHTML = '<p class="text-muted small">Cargando…</p>';
  });
  document.addEventListener("htmx:afterSwap", function (e) {
    if (e.target.id !== "panel-persona-cuerpo") return;
    var nombre = e.target.querySelector("a");
    if (nombre) nombre.focus();
  });
})();

// «Más acciones» de la cabecera de las fichas (un <details>, funciona sin JavaScript): con JavaScript se cierra
// al hacer clic fuera o con Esc, y el foco vuelve al botón.
(function () {
  document.addEventListener("click", function (e) {
    var dentro = e.target.closest("details.fche-menu");
    Array.prototype.forEach.call(document.querySelectorAll("details.fche-menu[open]"), function (d) { if (d !== dentro) d.open = false; });
  });
  document.addEventListener("keydown", function (e) {
    if (e.key !== "Escape") return;
    var abierto = document.querySelector("details.fche-menu[open]");
    if (!abierto) return;
    abierto.open = false;
    abierto.querySelector("summary").focus();
  });
})();

// F26 P1a: «Pasar lista». Con JavaScript aparece «Marcar todos» (marca o desmarca las casillas sin enviar) y se oculta
// «Todos asistieron», que sin JavaScript envía la lista con todos marcados. La pestaña puede llegar por HTMX.
(function () {
  function preparar(raiz) {
    Array.prototype.forEach.call((raiz || document).querySelectorAll("[data-marcar-todos]"), function (btn) {
      btn.hidden = false;
      var sinJs = btn.form && btn.form.querySelector("[data-todos-sin-js]");
      if (sinJs) sinJs.hidden = true;
    });
  }
  document.addEventListener("DOMContentLoaded", function () { preparar(document); });
  document.addEventListener("htmx:afterSettle", function (e) { preparar(e.target); });
  document.addEventListener("click", function (e) {
    var btn = e.target.closest && e.target.closest("[data-marcar-todos]");
    if (!btn || !btn.form) return;
    var casillas = btn.form.querySelectorAll("input[type='checkbox'][name='asistio']");
    var todas = Array.prototype.every.call(casillas, function (c) { return c.checked; });
    Array.prototype.forEach.call(casillas, function (c) { c.checked = !todas; });
    btn.textContent = todas ? "Marcar todos" : "Desmarcar todos";
  });
})();

// F26 Ia: las áreas de texto parten en 3 filas y crecen al escribir (data-crecer, lo pone BootstrapMixin). Sin JavaScript
// quedan de 3 filas y se pueden agrandar a mano. También las que llegan por HTMX (ventanas «+ Crear»).
(function () {
  function ajustar(el) {
    el.style.height = "auto";
    el.style.height = (el.scrollHeight + el.offsetHeight - el.clientHeight) + "px";
  }
  function preparar(raiz) {
    Array.prototype.forEach.call((raiz || document).querySelectorAll("textarea[data-crecer]"), function (el) {
      if (el.value) ajustar(el);
    });
  }
  document.addEventListener("DOMContentLoaded", function () { preparar(document); });
  document.addEventListener("htmx:afterSettle", function (e) { preparar(e.target); });
  document.addEventListener("input", function (e) {
    if (e.target.matches && e.target.matches("textarea[data-crecer]")) ajustar(e.target);
  });
})();

// F26 Ib: en celular las pestañas van en una fila con desplazamiento horizontal; al cargar (o al cambiar de pestaña con
// HTMX) la activa queda a la vista. Equivale a scrollIntoView({inline: "nearest"}), pero solo mueve la fila de pestañas,
// nunca la página. Sin JavaScript, la fila igual se desplaza con el dedo.
(function () {
  function mostrarActiva(raiz) {
    Array.prototype.forEach.call((raiz || document).querySelectorAll(".nav-tabs"), function (nav) {
      if (nav.scrollWidth <= nav.clientWidth) return;
      var activa = nav.querySelector(".nav-link.active");
      if (!activa) return;
      var r = activa.getBoundingClientRect(), n = nav.getBoundingClientRect(), margen = 24;
      if (r.left < n.left) nav.scrollLeft += r.left - n.left - margen;
      else if (r.right > n.right) nav.scrollLeft += r.right - n.right + margen;
    });
  }
  document.addEventListener("DOMContentLoaded", function () { mostrarActiva(document); });
  document.addEventListener("htmx:afterSettle", function (e) { mostrarActiva(e.target); });
})();

// F26 P: buscador de tarjetas (catálogos). Escribir filtra las tarjetas por nombre, sin tildes ni mayúsculas, y oculta los
// grupos que quedan vacíos. Sin JavaScript el buscador no aparece y se ven todas.
(function () {
  function normalizar(t) { return (t || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase(); }
  function preparar(caja) {
    var cont = document.querySelector(caja.getAttribute("data-filtrar-tarjetas"));
    var entrada = caja.querySelector("input");
    var estado = caja.querySelector("[role=status]");
    if (!cont || !entrada) return;
    caja.hidden = false;
    entrada.addEventListener("input", function () {
      var palabras = normalizar(entrada.value).split(/\s+/).filter(Boolean), total = 0;
      Array.prototype.forEach.call(cont.querySelectorAll("[data-grupo-tarjetas]"), function (g) {
        var visibles = 0;
        Array.prototype.forEach.call(g.querySelectorAll("[data-tarjeta]"), function (t) {
          var texto = normalizar(t.getAttribute("data-tarjeta"));
          var ok = palabras.every(function (p) { return texto.indexOf(p) !== -1; });
          t.hidden = !ok;
          if (ok) visibles++;
        });
        g.hidden = visibles === 0;
        total += visibles;
      });
      if (estado) estado.textContent = !palabras.length ? "" : (total === 0 ? "Ningún catálogo coincide con lo escrito." : (total === 1 ? "1 catálogo" : total + " catálogos"));
    });
  }
  document.addEventListener("DOMContentLoaded", function () {
    Array.prototype.forEach.call(document.querySelectorAll("[data-filtrar-tarjetas]"), preparar);
  });
})();
