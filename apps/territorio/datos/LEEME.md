# División político-administrativa de Chile (`cut_chile.csv`)

Lista oficial de **16 regiones, 56 provincias y 346 comunas**, con sus Códigos Únicos Territoriales (CUT). La carga en la base el comando `python manage.py cargar_territorio`, que sin argumentos usa este archivo.

## Fuentes (descargadas y comparadas el 14-10-2026)

| | Fuente | Para qué se usó |
|---|---|---|
| 1 | SUBDERE, «Códigos Únicos Territoriales - Actualizado al 2018», planilla `CUT_2018_v04.xls` (https://www.subdere.gov.cl/sites/default/files/documentos/CUT_2018_v04.xls). Codificación del Decreto Exento N° 1.115 de 2018 del Ministerio del Interior, publicado en el Diario Oficial el 21-09-2018; incluye la Región de Ñuble. SHA-256 del .xls: `d1b7fc3abb93cea3d115861579297d8bbdc9a7c762c958e646cd01b804df1ea0`. | Códigos de región, provincia y comuna; nombres de región y provincia |
| 2 | INE, «Diccionario de variables microdatos Censo 2024», hoja `codigos_territoriales` (https://censo2024.ine.gob.cl/wp-content/uploads/2025/12/diccionario_variables_censo2024.xlsx). SHA-256: `9cad2764f64e3a4d5dcc157dbfe21e8634cce97c95a4a7be3c8f60f3f66a02d8`. | Nombres de comuna (escritura más reciente) y verificación independiente |

## Cómo se comparó

- Coinciden los 346 códigos de comuna en ambas fuentes, y también la región y la provincia de cada uno.
- Hay 6 diferencias de escritura. Se usó la del INE, la más reciente:
  - «Los Álamos» y «Los Ángeles»: la SUBDERE los escribe sin tilde;
  - «Ránquil»: la SUBDERE escribe «Ranquil»;
  - «Paihuano»: la SUBDERE escribe «Paiguano»;
  - «Trehuaco»: la SUBDERE escribe «Treguaco».
- La provincia 014 queda como «Tamarugal» (SUBDERE); el INE la escribe «Del Tamarugal».
- El nombre largo de cada región sigue el formato oficial: «Región del Biobío», «Región Metropolitana de Santiago», «Región de Ñuble», etc.

## Formato

- UTF-8, separado por comas, con encabezado.
- Columnas: `region_codigo, region_nombre, provincia_codigo, provincia_nombre, comuna_codigo, comuna_nombre`.
- Los códigos son texto con ceros a la izquierda: región de 2 dígitos, provincia de 3 y comuna de 5. Ejemplo: Hualpén es `08112`, de la provincia `081` Concepción, en la región `08` del Biobío.

**Los sectores** (villas, poblaciones, etapas, barrios) no vienen en este archivo. No existe una lista oficial de ellos: los crea Claudio dentro de cada comuna.

Si el Estado cambia la división, se reemplaza este archivo y se vuelve a ejecutar el comando. Actualiza los nombres y agrega lo nuevo, sin duplicar ni borrar.
