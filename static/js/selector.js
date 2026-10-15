/* Buscador para elegir un registro (persona, organización, actividad…) dentro de los formularios.
   Convierte cada <select data-selector> en un cuadro con lista (patrón «combobox» accesible):
   - al hacer clic o enfocar muestra ya las primeras opciones; al escribir filtra (espera 250 ms; gana la última búsqueda);
   - se maneja con el teclado: ↑ y ↓ recorren, Enter elige (no envía el formulario), Esc cierra;
   - el <select> real queda oculto y es lo que se envía. Sin JavaScript se usa el <select> tal cual;
   - «+ Crear…» abre la ventana de creación rápida (fuera del formulario) y deja elegido lo creado.
   La lista la arma el servidor y llega ya escapada (format_html).
   Más abajo, la selección múltiple desplegable (generico/_selector_multiple.html): misma lista flotante,
   un cuadro para filtrar y lo elegido como etiquetas con ×. */
(function () {
  "use strict";
  var contador = 0;
  var ICONO_QUITAR = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true" focusable="false"><path d="M6 6l12 12M18 6L6 18"/></svg>';

  function textoDe(opcion) {
    return opcion ? (opcion.getAttribute("data-texto") || opcion.textContent || "").trim() : "";
  }

  function boton(clase, etiqueta, contenido) {
    var b = document.createElement("button");
    b.type = "button";
    b.className = clase;
    b.setAttribute("aria-label", etiqueta);
    b.innerHTML = contenido; // texto fijo de este archivo, nunca datos
    return b;
  }

  // La lista se abre hacia arriba si abajo no cabe y arriba hay más espacio.
  function ubicarPanel(ancla, panel) {
    var r = ancla.getBoundingClientRect(), abajo = window.innerHeight - r.bottom;
    panel.classList.toggle("fche-selector__panel--arriba", abajo < 260 && r.top > abajo);
  }

  function crear(select) {
    select.dataset.selectorListo = "1";
    contador += 1;
    if (!select.id) select.id = "selector-" + contador;
    var id = select.id;
    var caja = select.closest(".fche-selector");
    if (!caja) {
      caja = document.createElement("div");
      caja.className = "fche-selector";
      select.parentNode.insertBefore(caja, select);
      caja.appendChild(select);
    }
    var icono = caja.querySelector(".fche-selector__icono");
    if (icono) icono.hidden = false;
    var etiqueta = document.querySelector('label[for="' + id + '"]');
    var nombreCampo = etiqueta ? etiqueta.textContent.replace("*", "").replace("(obligatorio)", "").trim() : "";

    var input = document.createElement("input");
    input.type = "text";
    input.id = id + "-buscar";
    input.className = "form-control fche-selector__entrada";
    input.autocomplete = "off";
    input.spellcheck = false;
    input.placeholder = select.getAttribute("data-placeholder") || "Escribe para buscar…";
    input.setAttribute("role", "combobox");
    input.setAttribute("aria-autocomplete", "list");
    input.setAttribute("aria-expanded", "false");
    input.setAttribute("aria-controls", id + "-panel");
    if (select.disabled) input.disabled = true;
    if (select.getAttribute("aria-describedby")) input.setAttribute("aria-describedby", select.getAttribute("aria-describedby")); // la ayuda del campo
    if (select.required) { // la validación del navegador se hace sobre el cuadro visible; el servidor valida siempre
      select.required = false;
      input.required = true;
      input.setAttribute("aria-required", "true");
    }
    if (caja.closest(".fche-campo--error")) { input.classList.add("is-invalid"); input.setAttribute("aria-invalid", "true"); }
    if (etiqueta) {
      etiqueta.htmlFor = input.id;
      if (!etiqueta.id) etiqueta.id = id + "-etiqueta";
    }

    var abrirBtn = boton("fche-selector__abrir", "Mostrar opciones" + (nombreCampo ? " de " + nombreCampo : ""),
      '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true" focusable="false"><path d="M6 9l6 6 6-6"/></svg>');
    abrirBtn.tabIndex = -1;
    var quitar = select.hasAttribute("data-opcional") || !input.required
      ? boton("fche-selector__quitar", "Quitar lo elegido" + (nombreCampo ? " en " + nombreCampo : ""), ICONO_QUITAR)
      : null;
    var panel = document.createElement("div");
    panel.className = "fche-selector__panel";
    panel.id = id + "-panel";
    panel.hidden = true;
    var vivo = document.createElement("div");
    vivo.className = "visually-hidden";
    vivo.setAttribute("aria-live", "polite");
    var aviso = document.createElement("div");
    aviso.className = "form-text fche-selector__aviso";
    aviso.setAttribute("role", "status");

    select.hidden = true;
    select.tabIndex = -1;
    select.setAttribute("aria-hidden", "true");
    caja.appendChild(input);
    if (quitar) caja.appendChild(quitar);
    caja.appendChild(abrirBtn);
    caja.appendChild(panel);
    caja.appendChild(vivo);
    caja.parentNode.insertBefore(aviso, caja.nextSibling);

    var abierto = false, activa = -1, controlador = null, temporizador = null, sinAbrir = false;

    function sincronizar() {
      var o = select.options[select.selectedIndex];
      input.value = select.value ? textoDe(o) : "";
      if (quitar) quitar.hidden = !select.value || input.disabled;
    }

    function opciones() { return panel.querySelectorAll('[role="option"]'); }

    function marcar(i) {
      var ops = opciones();
      Array.prototype.forEach.call(ops, function (o) { o.classList.remove("is-activa"); });
      activa = i;
      if (i < 0 || !ops[i]) { input.removeAttribute("aria-activedescendant"); return; }
      ops[i].classList.add("is-activa");
      input.setAttribute("aria-activedescendant", ops[i].id);
      ops[i].scrollIntoView({ block: "nearest" });
    }

    function ubicar() { ubicarPanel(input, panel); }

    function direccion(q) {
      var base = select.getAttribute("data-opciones-url");
      return base + (base.indexOf("?") === -1 ? "?" : "&") + "q=" + encodeURIComponent(q) + "&actual=" + encodeURIComponent(select.value || "");
    }

    function cargar(q) {
      if (controlador) controlador.abort();
      controlador = window.AbortController ? new window.AbortController() : null;
      panel.setAttribute("aria-busy", "true");
      if (!panel.querySelector('[role="listbox"]')) panel.innerHTML = '<div class="fche-selector__estado">Cargando…</div>';
      window.fetch(direccion(q), { credentials: "same-origin", headers: { "HX-Request": "true" }, signal: controlador ? controlador.signal : undefined })
        .then(function (r) { if (!r.ok) throw new Error(String(r.status)); return r.text(); })
        .then(function (html) {
          panel.innerHTML = html; // armado y escapado por el servidor
          var lista = panel.querySelector('[role="listbox"]');
          if (lista) {
            lista.id = id + "-lista";
            if (etiqueta) lista.setAttribute("aria-labelledby", etiqueta.id);
            input.setAttribute("aria-controls", lista.id);
          }
          Array.prototype.forEach.call(opciones(), function (o, i) { o.id = id + "-op-" + i; });
          var pie = panel.querySelector(".fche-selector__pie");
          vivo.textContent = pie ? pie.textContent : "";
          panel.removeAttribute("aria-busy");
          activa = -1;
          input.removeAttribute("aria-activedescendant");
          ubicar();
        })
        .catch(function (e) {
          if (e && e.name === "AbortError") return;
          panel.removeAttribute("aria-busy");
          panel.innerHTML = '<div class="fche-selector__estado" role="alert">No se pudieron cargar las opciones. '
            + '<button type="button" class="btn btn-link btn-sm p-0 align-baseline" data-reintentar>Reintentar</button></div>';
        });
    }

    function abrir(sinCargar) {
      if (abierto || input.disabled) return;
      abierto = true;
      panel.hidden = false;
      input.setAttribute("aria-expanded", "true");
      ubicar();
      if (!sinCargar) cargar("");
    }

    function cerrar(restaurar) {
      abierto = false;
      panel.hidden = true;
      input.setAttribute("aria-expanded", "false");
      input.removeAttribute("aria-activedescendant");
      activa = -1;
      window.clearTimeout(temporizador);
      if (controlador) controlador.abort();
      if (restaurar) sincronizar();
    }

    function fijar(valor, texto) {
      valor = String(valor);
      var o = Array.prototype.find.call(select.options, function (x) { return x.value === valor; });
      if (!o) {
        o = new Option(texto, valor);
        o.setAttribute("data-texto", texto);
        select.appendChild(o);
      }
      select.value = valor;
      sincronizar();
      select.dispatchEvent(new Event("change", { bubbles: true })); // aviso de cambios y borrador
    }

    function abrirCrear(url) {
      var modal = document.getElementById("modal-rapido");
      if (!modal || !window.htmx || !window.bootstrap) return;
      var destino = url + (url.indexOf("?") === -1 ? "?" : "&") + "campo=" + encodeURIComponent(id);
      window.htmx.ajax("GET", destino, { target: "#modal-rapido-contenido", swap: "innerHTML" }).then(function () {
        window.bootstrap.Modal.getOrCreateInstance(modal).show();
      });
    }

    function elegir(op) {
      if (op.hasAttribute("data-crear")) { cerrar(true); abrirCrear(op.getAttribute("data-crear")); return; }
      fijar(op.getAttribute("data-valor"), op.getAttribute("data-texto"));
      cerrar(false);
    }

    input.addEventListener("focus", function () {
      if (sinAbrir) { sinAbrir = false; return; }
      abrir();
    });
    input.addEventListener("click", function () { abrir(); });
    input.addEventListener("input", function () {
      abrir(true);
      window.clearTimeout(temporizador);
      temporizador = window.setTimeout(function () { cargar(input.value.trim()); }, 250);
    });
    input.addEventListener("keydown", function (e) {
      var ops = opciones();
      if (e.key === "ArrowDown") {
        e.preventDefault();
        if (!abierto) { abrir(); return; }
        marcar(Math.min(activa + 1, ops.length - 1));
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        if (abierto) marcar(Math.max(activa - 1, 0));
      } else if (e.key === "Enter") {
        e.preventDefault(); // Enter elige; nunca envía el formulario
        if (abierto && activa >= 0 && ops[activa]) elegir(ops[activa]);
        else if (!abierto) abrir();
      } else if (e.key === "Escape") {
        if (abierto) { e.preventDefault(); cerrar(true); }
      } else if (e.key === "Tab") {
        if (abierto) cerrar(true);
      }
    });
    input.addEventListener("blur", function () {
      window.setTimeout(function () { if (abierto && !caja.contains(document.activeElement)) cerrar(true); }, 150);
    });
    panel.addEventListener("mousedown", function (e) { e.preventDefault(); }); // el foco se queda en el cuadro
    panel.addEventListener("click", function (e) {
      if (e.target.closest("[data-reintentar]")) { cargar(""); return; }
      var op = e.target.closest('[role="option"]');
      if (op) elegir(op);
    });
    abrirBtn.addEventListener("mousedown", function (e) { e.preventDefault(); });
    abrirBtn.addEventListener("click", function () {
      if (abierto) { cerrar(true); return; }
      sinAbrir = document.activeElement !== input;
      input.focus();
      abrir();
    });
    if (quitar) {
      quitar.addEventListener("click", function () {
        select.value = "";
        sincronizar();
        select.dispatchEvent(new Event("change", { bubbles: true }));
        sinAbrir = true;
        input.focus();
      });
    }
    select.addEventListener("change", sincronizar);
    select.addEventListener("fche:restaurado", sincronizar); // borrador recuperado por fche.js
    select.addEventListener("fche:fijar", function (e) { // creado o elegido en la ventana «+ Crear…»
      var d = e.detail || {};
      if (!d.valor) return;
      fijar(d.valor, d.texto || "");
      aviso.textContent = d.aviso || "";
      sinAbrir = true;
      input.focus();
    });
    sincronizar();
  }

  /* ---------- Selección múltiple desplegable ----------
     Mejora el bloque de generico/_selector_multiple.html (un <details> con casillas nativas):
     - el botón despliega la lista sobre el formulario, con un cuadro para filtrar (sin distinguir tildes ni mayúsculas);
     - lo elegido se muestra como etiquetas con × para quitarlo;
     - teclado: ↑ y ↓ recorren, Enter marca o desmarca (nunca envía el formulario), Esc cierra.
     Lo que se envía siguen siendo las casillas. */
  function plano(t) { return (t || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase(); }

  function crearMultiple(caja) {
    caja.dataset.multiListo = "1";
    var desplegable = caja.querySelector(".fche-multi__desplegable");
    var resumenBtn = desplegable ? desplegable.querySelector("summary") : null;
    var panel = caja.querySelector(".fche-multi__panel");
    if (!resumenBtn || !panel) return;
    var resumen = caja.querySelector("[data-multi-resumen]");
    var buscar = caja.querySelector("[data-multi-filtro]");
    var filtro = buscar ? buscar.querySelector("input") : null;
    var vacio = caja.querySelector("[data-multi-vacio]");
    var casillas = Array.prototype.slice.call(panel.querySelectorAll('input[type="checkbox"]'));
    var nombreCampo = caja.getAttribute("data-etiqueta") || "";

    var etiquetas = document.createElement("ul");
    etiquetas.className = "fche-multi__etiquetas";
    etiquetas.setAttribute("aria-label", "Lo elegido" + (nombreCampo ? " en " + nombreCampo : ""));
    caja.appendChild(etiquetas);
    caja.classList.add("is-listo");
    panel.classList.add("fche-selector__panel"); // la misma lista flotante del buscador
    if (buscar) buscar.hidden = false;

    function nombre(c) { var l = c.closest("label"); return l ? l.textContent.trim() : c.value; }
    function visibles() { return casillas.filter(function (c) { return !c.closest("li").hidden; }); }

    function pintar() {
      var elegidas = casillas.filter(function (c) { return c.checked; }), n = elegidas.length;
      etiquetas.textContent = "";
      elegidas.forEach(function (c) {
        var li = document.createElement("li"), texto = document.createElement("span");
        li.className = "fche-multi__etiqueta";
        texto.textContent = nombre(c);
        var quitar = boton("fche-multi__quitar", "Quitar " + nombre(c), ICONO_QUITAR);
        quitar.setAttribute("data-quitar", c.id);
        li.appendChild(texto);
        li.appendChild(quitar);
        etiquetas.appendChild(li);
      });
      etiquetas.hidden = !n;
      if (resumen) {
        resumen.textContent = n === 0 ? "Elegir…" : (n === 1 ? "1 opción elegida" : n + " opciones elegidas");
        resumen.classList.toggle("is-vacio", n === 0);
      }
    }

    function filtrar() {
      var escrito = filtro ? filtro.value.trim() : "", q = plano(escrito), hay = 0;
      casillas.forEach(function (c) {
        var ve = !q || plano(nombre(c)).indexOf(q) !== -1;
        c.closest("li").hidden = !ve;
        if (ve) hay++;
      });
      if (vacio) vacio.textContent = hay || !casillas.length ? "" : "Sin resultados para «" + escrito + "».";
    }

    function cerrar(enfocar) {
      if (desplegable.open) desplegable.open = false;
      if (enfocar) resumenBtn.focus();
    }

    function moverFoco(desde, paso) {
      var lista = visibles(), i = lista.indexOf(desde);
      if (i === -1) { if (lista.length) lista[paso > 0 ? 0 : lista.length - 1].focus(); return; }
      if (i + paso < 0) { if (filtro) filtro.focus(); return; }
      if (i + paso < lista.length) lista[i + paso].focus();
    }

    desplegable.addEventListener("toggle", function () {
      if (desplegable.open) {
        ubicarPanel(resumenBtn, panel);
        if (filtro) filtro.focus();
      } else if (filtro && filtro.value) {
        filtro.value = "";
        filtrar();
      }
    });
    resumenBtn.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && desplegable.open) { e.preventDefault(); cerrar(true); }
    });
    if (filtro) filtro.addEventListener("input", filtrar);
    // Un clic en la lista deja el foco en el cuadro para filtrar (así el teclado sigue donde estaba).
    panel.addEventListener("mousedown", function (e) { if (e.target !== filtro) e.preventDefault(); });
    panel.addEventListener("keydown", function (e) {
      var t = e.target;
      if (e.key === "Escape") { e.preventDefault(); cerrar(true); return; }
      if (e.key === "ArrowDown" || e.key === "ArrowUp") {
        e.preventDefault();
        moverFoco(t === filtro ? null : t, e.key === "ArrowDown" ? 1 : -1);
      } else if (e.key === "Enter") {
        e.preventDefault(); // Enter marca o desmarca; nunca envía el formulario
        if (t === filtro) { var v = visibles(); if (v.length) v[0].click(); }
        else if (t.type === "checkbox") t.click();
      }
    });
    caja.addEventListener("change", function (e) { if (e.target.type === "checkbox") pintar(); });
    caja.addEventListener("focusout", function (e) { // con Tab fuera del bloque se cierra
      if (desplegable.open && e.relatedTarget && !caja.contains(e.relatedTarget)) cerrar(false);
    });
    etiquetas.addEventListener("click", function (e) {
      var b = e.target.closest("[data-quitar]");
      var c = b ? document.getElementById(b.getAttribute("data-quitar")) : null;
      if (!c) return;
      var i = Array.prototype.indexOf.call(etiquetas.querySelectorAll("[data-quitar]"), b);
      c.checked = false;
      c.dispatchEvent(new Event("change", { bubbles: true })); // vuelve a dibujar las etiquetas; aviso de cambios y borrador
      var resto = etiquetas.querySelectorAll("[data-quitar]");
      (resto[Math.min(i, resto.length - 1)] || resumenBtn).focus();
    });
    pintar();
  }

  // Un clic fuera de una selección múltiple abierta la cierra.
  document.addEventListener("click", function (e) {
    Array.prototype.forEach.call(document.querySelectorAll(".fche-multi.is-listo .fche-multi__desplegable[open]"), function (d) {
      if (!d.closest(".fche-multi").contains(e.target)) d.open = false;
    });
  });

  function iniciarEn(raiz) {
    if (!raiz || !raiz.querySelectorAll) return;
    var lista = raiz.matches && raiz.matches("select[data-selector]") ? [raiz] : raiz.querySelectorAll("select[data-selector]");
    Array.prototype.forEach.call(lista, function (s) { if (!s.dataset.selectorListo) crear(s); });
    var multiples = raiz.matches && raiz.matches("[data-multi]") ? [raiz] : raiz.querySelectorAll("[data-multi]");
    Array.prototype.forEach.call(multiples, function (m) { if (!m.dataset.multiListo) crearMultiple(m); });
  }

  function cerrarVentana() {
    var modal = document.getElementById("modal-rapido");
    if (modal && window.bootstrap) window.bootstrap.Modal.getOrCreateInstance(modal).hide();
  }

  function entregar(campo, detalle) {
    var select = campo ? document.getElementById(campo) : null;
    cerrarVentana();
    if (select) window.setTimeout(function () { select.dispatchEvent(new CustomEvent("fche:fijar", { detail: detalle })); }, 0);
  }

  // Respuesta del servidor al crear (encabezado HX-Trigger «fche:elegido»).
  document.addEventListener("fche:elegido", function (e) {
    var d = e.detail || {};
    entregar(d.campo, d);
  });

  // «Usar esta persona / organización» en el aviso de parecidos.
  document.addEventListener("click", function (e) {
    var b = e.target.closest("[data-usar-existente]");
    if (!b) return;
    entregar(b.getAttribute("data-campo"), { valor: b.getAttribute("data-valor"), texto: b.getAttribute("data-texto"), aviso: "Se eligió la ficha que ya existía." });
  });

  // fche.js bloquea los botones al enviar: en la ventana se vuelven a habilitar tras cada respuesta.
  document.addEventListener("htmx:afterRequest", function (e) {
    var form = e.target && e.target.closest ? e.target.closest("#modal-rapido form") : null;
    if (!form) return;
    delete form.dataset.enviando;
    Array.prototype.forEach.call(form.querySelectorAll("button"), function (b) { b.disabled = false; });
  });

  // Al abrir la ventana o al mostrar el aviso de parecidos, el foco va al primer dato por revisar.
  function enfocarVentana() {
    var cont = document.getElementById("modal-rapido-contenido");
    if (!cont) return;
    var destino = cont.querySelector(".is-invalid, #rapida-nota, .fche-campo--error input") || cont.querySelector("input:not([type=hidden]), select, textarea");
    if (destino) destino.focus();
  }
  document.addEventListener("shown.bs.modal", function (e) { if (e.target.id === "modal-rapido") enfocarVentana(); });
  document.addEventListener("htmx:afterSwap", function (e) {
    var modal = document.getElementById("modal-rapido");
    if (e.target.id === "modal-rapido-contenido" && modal && modal.classList.contains("show")) enfocarVentana();
  });

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", function () { iniciarEn(document); });
  else iniciarEn(document);
  document.addEventListener("htmx:load", function (e) { iniciarEn(e.target); }); // contenido que llega por HTMX
})();
