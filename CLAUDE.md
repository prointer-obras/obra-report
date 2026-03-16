# CLAUDE.md — obra-report (PROINTER Informes de Obra)

## Descripción

PWA móvil para que encargados de obra generen y compartan informes semanales en PDF. Permite gestionar obras (proyectos), crear informes paso a paso (trabajos, operarios, fotos, planificación), generar un PDF y compartirlo por email u otras apps.

Idioma de la app: **español**.

---

## Arquitectura: dos pistas en el mismo repo

El repo contiene **dos implementaciones paralelas**. La activa es la pista `static/`.

| | Standalone PWA (activa) | React + Express (alternativa) |
|---|---|---|
| Carpeta | `static/` | `src/` + `server/` |
| Entry point | `static/index.html` | `index.html` (raíz) + `src/main.jsx` |
| Build | Ninguno — se sirve tal cual | `npm run build` (Vite 5) |
| Backend | Ninguno | `server/index.js` (Express, puerto 3001) |
| Email | Web Share API (PDF directo) | Nodemailer vía `/api/send-report` |
| Estado | **En producción** | No desplegada |

> **Toda la edición activa ocurre en `static/index.html` y `static/sw.js`.**
> La carpeta `src/` existe pero no está desplegada.

---

## Ficheros clave

```
obra-report/
├── static/
│   ├── index.html        ← App completa (HTML + CSS + JS en un solo fichero)
│   ├── sw.js             ← Service Worker (caché offline)
│   ├── manifest.json     ← PWA manifest (nombre, iconos, colores)
│   ├── icon-192.png
│   ├── icon-512.png
│   └── prointer-logo.jpg ← Logo por defecto (se puede sobreescribir por ajustes)
├── src/                  ← Pista React (no activa)
├── server/               ← Backend Express (no activo)
├── package.json          ← Scripts npm (para pista React/Express)
├── render.yaml           ← Config Render.com (Python/Flask, legado)
└── Procfile              ← Config Heroku (legado)
```

---

## Modelos de datos

Todo se persiste en **localStorage** (sin backend en la pista activa).

### Project
```js
{
  id: string,           // uid generado
  name: string,         // Nombre de la obra
  code: string,         // Código (mayúsculas, ej: "CLM-2024-001")
  managerName: string,  // Nombre jefe de obra
  managerEmail: string, // Email del jefe de obra
  createdAt: string     // ISO8601
}
```

### Report
```js
{
  id: string,
  projectId: string,
  weekNumber: number,      // Semana ISO (1-53)
  year: number,
  status: 'draft'|'sent',
  createdAt: string,       // ISO8601
  updatedAt: string,
  sentAt: string,          // ISO8601, solo si status==='sent'

  // Contenido del informe
  prevPlan: string,        // Planificación semana anterior (nextWeekWorks del informe previo)
  worksCompleted: string,  // Descripción trabajos realizados
  workItems: string[],     // Items individuales (lista) de worksCompleted
  workers: Worker[],       // Operarios asignados
  photos: Photo[],         // Fotos (dataUrl solo en memoria; en localStorage solo id+caption)
  observations: string,    // Observaciones (campo adicional)
  materialsNeeded: string, // Materiales para próxima semana
  materialItems: string[], // Items individuales de materialsNeeded
  nextWeekWorks: string,   // Planificación próxima semana
  nextWorkItems: string[]  // Items individuales de nextWeekWorks
}
```

### Worker
```js
{ id: string, name: string, role: string, rating?: string, company?: string }
```

### Photo
```js
{ id: string, caption: string, dataUrl: string }
// dataUrl solo en memoria/IndexedDB; localStorage guarda solo {id, caption}
```

### Settings
```js
{
  companyName: string,  // Aparece en PDF y cabecera
  logoBase64: string    // Logo en base64 (opcional)
}
```

---

## Almacenamiento

- **localStorage** — proyectos (`obra_projects`), informes (`obra_reports`), ajustes (`obra_settings`)
- **IndexedDB** (PhotoStore) — fotos en full resolution; las fotos solo se guardan como `{id, caption}` en localStorage para no saturarlo

Utilidades de acceso (en `static/index.html`):
```js
DB.get(key)       // Lee de localStorage con JSON.parse
DB.set(key, val)  // Escribe en localStorage con JSON.stringify
PhotoStore.save(id, dataUrl, cb)
PhotoStore.getAll(ids[], cb)   // cb recibe objeto {id: dataUrl}
PhotoStore.delete(id, cb)
```

---

## Funciones principales (`static/index.html`)

| Función | Propósito |
|---|---|
| `startReport(projectId, reportId?)` | Inicia o retoma un informe; carga fotos de IndexedDB |
| `getProjectReports(pid)` | Devuelve informes de un proyecto ordenados por año/semana DESC |
| `getLastReport(pid)` | Devuelve el informe más reciente del proyecto (cualquier estado) |
| `autoSaveDraft()` | Guarda el borrador actual en localStorage (sin fotos en base64) |
| `renderStep()` | Renderiza el paso actual del formulario (0–4) |
| `generatePDF()` | Genera el PDF con jsPDF y almacena el blob en `rfPdfBlob` |
| `handleSharePDF()` | Comparte el PDF vía Web Share API (o descarga si no disponible) |
| `saveReports()` / `saveProjects()` | Persisten arrays en localStorage |
| `showPage(id)` | Navega entre páginas (home, projects, settings, report) |
| `uid()` | Genera un ID único (timestamp + random) |
| `getWeek()` | Devuelve `[weekNumber, year]` de la semana ISO actual |
| `weekRange(w, y)` | Devuelve el rango de fechas formateado de una semana |
| `esc(str)` | Escapa HTML para prevenir XSS |

### Flujo `prevPlan` (planificación semana anterior)
- Al crear un informe nuevo: `prevPlan = getLastReport(pid).nextWeekWorks`
- Al reabrir un borrador existente: si `existing.prevPlan` está vacío, se busca el informe inmediatamente anterior en el array ordenado y se usa su `nextWeekWorks` (IIFE en línea ~624)

---

## Service Worker (`static/sw.js`)

- **Versión actual de caché:** `obra-report-v15`
- Estrategia: **cache-first**, red como fallback
- Las rutas `/api/*` siempre van a la red (sin caché)
- Al desplegar cambios en `static/`: **incrementar el número de versión** (`obra-report-vN`) para forzar que los clientes descarguen los nuevos assets

```js
// sw.js línea 1 — actualizar al desplegar
const CACHE = 'obra-report-v16'; // ← incrementar
```

---

## PDF generado

El PDF se genera en cliente con **jsPDF** (CDN: `cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/`).

Secciones del PDF (A4):
1. Cabecera azul (logo empresa + datos obra + semana)
2. Comparativa: planificación semana anterior vs. trabajos realizados
3. Tabla de operarios (nombre + rol + empresa)
4. Valoraciones de subcontratas (si hay ratings)
5. Galería de fotos (3 columnas, con pies de foto)
6. Planificación próxima semana (materiales + trabajos)
7. Pie de página en todas las páginas (empresa, código, semana, número de página)

---

## Compartir PDF

Función `handleSharePDF()` (línea ~1093 de `static/index.html`):

1. Si `navigator.canShare({files:[file]})` → usa **Web Share API** con el PDF adjunto y texto prefijado:
   > "Un saludo [managerEmail]. Adjunto envío informe de avances de la obra "[nombre (código)]" para la Semana X/YYYY."
2. Si no soportado → descarga el PDF directamente (`<a download>`)
3. Al compartir con éxito → el informe pasa a `status: 'sent'`

---

## Flujo de trabajo de desarrollo

La app standalone no necesita build. Para probar cambios:

1. Editar `static/index.html` o `static/sw.js`
2. Si hay cambios en assets cacheados → incrementar versión en `sw.js`
3. Servir la carpeta `static/` con cualquier servidor HTTP estático, por ejemplo:
   ```bash
   npx serve static/
   # o
   python -m http.server 8080 --directory static/
   ```
4. En el navegador: abrir DevTools → Application → Service Workers → "Update on reload"

Para la pista React/Express (no activa):
```bash
npm install
npm run dev    # Vite en :5173 + Express en :3001
npm run build  # Build de producción en dist/
```

---

## Despliegue

La pista activa (`static/`) se despliega como sitio estático (ningún servidor backend necesario).

- El `render.yaml` apunta a Python/Flask (legado, no usar)
- Para nuevo despliegue: apuntar el hosting a la carpeta `static/` y servir `index.html` para todas las rutas
- Variables de entorno: ninguna (la pista standalone no usa backend)

---

## Notas de diseño

- Mobile-first: max-width 480px, navegación inferior fija
- Safe area insets para dispositivos con notch (`env(safe-area-inset-bottom)`)
- Sin frameworks CSS externos — todo CSS inline en `<style>` dentro de `index.html`
- Sin dependencias npm en la pista activa (excepto jsPDF via CDN)
- Los colores de marca son azul (`#2563eb`) y variantes de slate
