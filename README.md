# ⚡ Motor de Facturación Electrónica SRI — Ecuador

**Microservicio REST** para la emisión, firma y envío de comprobantes electrónicos (facturas) ante el **Servicio de Rentas Internas (SRI)** del Ecuador, modalidad offline.

Construido con **FastAPI** + **SQLAlchemy** + **lxml** + **zeep**. Listo para conectarse a cualquier frontend, punto de venta o ERP.

---

## 🎯 ¿Qué hace esta API?

| Paso | Descripción | Automático |
|------|-------------|:----------:|
| 1 | Recibe un JSON con datos del cliente y productos | — |
| 2 | Calcula impuestos (IVA 0%, 5%, 12%, 14%, 15%) | ✅ |
| 3 | Genera la **clave de acceso** de 49 dígitos (Módulo 11) | ✅ |
| 4 | Construye el **XML** conforme al esquema del SRI v1.1.0 | ✅ |
| 5 | Firma el XML con **XAdES-BES** (certificado .p12) | ✅ |
| 6 | Envía al WS **RecepcionComprobantesOffline** del SRI | ✅ |
| 7 | Consulta el WS **AutorizacionComprobantesOffline** | ✅ |
| 8 | Guarda la factura en **SQLite** (historial local) | ✅ |
| 9 | Genera el **RIDE en PDF** con código QR | ✅ |

---

## 📁 Estructura del Proyecto

```
API REST/
├── app/
│   ├── __init__.py
│   ├── config.py              ← Lee todas las variables desde .env
│   ├── database.py            ← SQLAlchemy + SQLite
│   ├── main.py                ← Punto de entrada FastAPI
│   ├── models/
│   │   ├── db_models.py       ← Modelo Factura (SQLAlchemy)
│   │   ├── enums.py           ← Enumeraciones SRI (IVA, formas de pago)
│   │   └── schemas.py         ← Esquemas Pydantic (validación)
│   ├── routers/
│   │   ├── facturar.py        ← POST /facturar (flujo simplificado)
│   │   └── facturas.py        ← POST/GET /facturas + PDF RIDE
│   └── services/
│       ├── clave_acceso.py    ← Generador clave de acceso (Módulo 11)
│       ├── pdf_generator.py   ← Generador RIDE PDF + QR
│       ├── sri_client.py      ← Cliente SOAP (zeep)
│       ├── xml_generator.py   ← Constructor XML (lxml)
│       └── xml_signer.py      ← Firma XAdES-BES (mock/real)
├── certificados/
│   └── firma.p12              ← Tu firma electrónica (NO se sube al repo)
├── .env                       ← Tus variables de entorno (NO se sube al repo)
├── .env.example               ← Plantilla de referencia
├── .gitignore
├── requirements.txt
└── README.md
```

---

## 🚀 Guía de Configuración Rápida (Plug & Play)

Para poner en marcha la API en un **nuevo negocio**, solo necesitas hacer **2 cosas**:

### Paso 1 — Colocar la firma electrónica

Copia tu archivo `.p12` (firma electrónica del SRI) dentro de la carpeta `certificados/`:

```
certificados/
└── firma.p12    ← Tu archivo real aquí
```

> 📌 **¿No tienes firma electrónica?** Puedes obtenerla en:
> - [Security Data](https://www.securitydata.net.ec)
> - [ANF AC Ecuador](https://www.anfac.com.ec)
>
> Mientras tanto, la API funciona en **modo simulación** (no firma realmente, pero el flujo completo se ejecuta sin errores).

### Paso 2 — Configurar las variables de entorno

```bash
# Duplicar la plantilla
cp .env.example .env

# Abrir y editar con tus datos reales
code .env
```

¡Listo! No necesitas tocar **ningún archivo de código fuente**.

---

## 📋 Diccionario de Variables de Entorno (.env)

### Entorno SRI

| Variable | Descripción | Formato | Ejemplo |
|----------|-------------|---------|---------|
| `SRI_AMBIENTE` | Ambiente del SRI | `1` = Pruebas, `2` = Producción | `1` |
| `SRI_TIPO_EMISION` | Tipo de emisión | `1` = Normal (siempre 1) | `1` |

### Datos del Emisor

| Variable | Descripción | Formato | Ejemplo |
|----------|-------------|---------|---------|
| `EMISOR_RUC` | RUC del emisor | 13 dígitos numéricos | `0912345678001` |
| `EMISOR_RAZON_SOCIAL` | Razón social registrada en el SRI | Texto (hasta 300 caracteres) | `ACME SOLUCIONES S.A.` |
| `EMISOR_NOMBRE_COMERCIAL` | Nombre comercial del negocio | Texto | `ACME` |
| `EMISOR_DIR_MATRIZ` | Dirección de la matriz | Texto | `Av. 9 de Octubre - Guayaquil` |
| `EMISOR_DIR_ESTABLECIMIENTO` | Dirección del establecimiento | Texto | `Av. 9 de Octubre - Guayaquil` |
| `EMISOR_OBLIGADO_CONTABILIDAD` | ¿Obligado a llevar contabilidad? | `SI` o `NO` | `NO` |
| `EMISOR_CONTRIBUYENTE_ESPECIAL` | Número de resolución (si aplica) | Número o vacío | `` |
| `EMISOR_ESTABLECIMIENTO` | Código del establecimiento | 3 dígitos | `001` |
| `EMISOR_PUNTO_EMISION` | Código del punto de emisión | 3 dígitos | `001` |

### Firma Electrónica

| Variable | Descripción | Formato | Ejemplo |
|----------|-------------|---------|---------|
| `FIRMA_ELECTRONICA_ARCHIVO` | Nombre del archivo `.p12` | Nombre de archivo | `firma.p12` |
| `FIRMA_ELECTRONICA_PASSWORD` | Contraseña de la firma | Texto | `MiClave2026` |

> ⚠️ **Seguridad**: Nunca subas el archivo `.env` ni el `.p12` a un repositorio público. Ambos están incluidos en `.gitignore`.

---

## 🛠️ Cómo Arrancar el Servidor

### 1. Crear el entorno virtual (solo la primera vez)

```bash
python -m venv venv
```

### 2. Activar el entorno virtual

```bash
# Windows (PowerShell)
.\venv\Scripts\Activate.ps1

# Windows (CMD)
venv\Scripts\activate.bat

# Linux / macOS
source venv/bin/activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Levantar el servidor

```bash
uvicorn app.main:app --reload
```

El servidor arrancará en `http://localhost:8000`.

| URL | Descripción |
|-----|-------------|
| `http://localhost:8000/` | Health check |
| `http://localhost:8000/docs` | **Swagger UI** (documentación interactiva) |
| `http://localhost:8000/redoc` | ReDoc (documentación alternativa) |

---

## 📡 Endpoints Disponibles

| Método | Ruta | Descripción |
|--------|------|-------------|
| `POST` | `/api/v1/facturar` | **Facturar (simplificado)** — Envía datos del cliente + productos. La API calcula impuestos automáticamente. |
| `POST` | `/api/v1/facturas` | Facturar (estructura SRI completa) — Para integraciones avanzadas. |
| `GET` | `/api/v1/facturas` | Historial de facturas emitidas (SQLite). Filtros: `?limite=50&estado=AUTORIZADO` |
| `GET` | `/api/v1/facturas/{id}/pdf` | Descargar RIDE en PDF (con QR). Ideal para WhatsApp. |
| `GET` | `/api/v1/facturas/autorizacion/{clave}` | Consultar estado de autorización en el SRI. |
| `GET` | `/` | Health check del servicio. |

---

## 📦 Cómo Usar la API — Ejemplo Completo

### Emitir una factura

**`POST /api/v1/facturar`**

Envía este JSON desde tu frontend, punto de venta o sistema externo:

```json
{
  "secuencial": "000000001",
  "fecha_emision": "28/03/2026",
  "cliente": {
    "tipo_identificacion": "05",
    "identificacion": "0102030405",
    "razon_social": "Juan Pérez",
    "direccion": "Cuenca - Ecuador",
    "email": "juan@correo.com",
    "telefono": "0991234567"
  },
  "productos": [
    {
      "codigo": "SERV-001",
      "descripcion": "Servicio Profesional Mensual",
      "cantidad": 1,
      "precio_unitario": "100.00",
      "codigo_porcentaje_iva": "4"
    },
    {
      "codigo": "PROD-010",
      "descripcion": "Material de oficina",
      "cantidad": 2,
      "precio_unitario": "25.00",
      "descuento": "5.00",
      "codigo_porcentaje_iva": "4"
    }
  ],
  "forma_pago": "01",
  "info_adicional": {
    "email": "juan@correo.com",
    "telefono": "0991234567"
  }
}
```

### Campos del cliente

| Campo | Tipo | Requerido | Descripción |
|-------|------|:---------:|-------------|
| `tipo_identificacion` | string | ✅ | `"04"` = RUC, `"05"` = Cédula, `"06"` = Pasaporte, `"07"` = Consumidor Final |
| `identificacion` | string | ✅ | Número de documento (RUC: 13 dígitos, Cédula: 10 dígitos) |
| `razon_social` | string | ✅ | Nombre completo o razón social |
| `direccion` | string | — | Dirección del comprador |
| `email` | string | — | Correo electrónico |
| `telefono` | string | — | Teléfono de contacto |

### Campos de cada producto

| Campo | Tipo | Requerido | Descripción |
|-------|------|:---------:|-------------|
| `codigo` | string | ✅ | Código interno del producto/servicio |
| `descripcion` | string | ✅ | Nombre o descripción |
| `cantidad` | decimal | ✅ | Cantidad vendida |
| `precio_unitario` | decimal | ✅ | Precio unitario sin impuestos |
| `descuento` | decimal | — | Descuento monetario (default: `0.00`) |
| `codigo_porcentaje_iva` | string | — | Código IVA (default: `"4"` = 15%). Ver tabla abajo. |

### Códigos de porcentaje IVA

| Código | Tarifa | Descripción |
|:------:|:------:|-------------|
| `0` | 0% | IVA 0% |
| `2` | 12% | IVA 12% |
| `3` | 14% | IVA 14% |
| `4` | 15% | IVA 15% (vigente 2024+) |
| `5` | 5% | IVA 5% |
| `6` | — | No objeto de impuesto |
| `7` | — | Exento de IVA |

### Formas de pago

| Código | Descripción |
|:------:|-------------|
| `01` | Sin utilización del sistema financiero (efectivo) |
| `15` | Compensación de deudas |
| `16` | Tarjeta de débito |
| `17` | Dinero electrónico |
| `18` | Tarjeta prepago |
| `19` | Tarjeta de crédito |
| `20` | Otros con utilización del sistema financiero |
| `21` | Endoso de títulos |

### Respuesta exitosa

```json
{
  "clave_acceso": "2803202601091234567800110010010000000011234567895",
  "secuencial": "000000001",
  "fecha_emision": "28/03/2026",
  "recepcion": {
    "estado": "RECIBIDA",
    "clave_acceso": "2803202601091234567800110010010000000011234567895",
    "mensajes": []
  },
  "autorizacion": {
    "estado": "AUTORIZADO",
    "numero_autorizacion": "2803202601091234567800110010010000000011234567895",
    "fecha_autorizacion": "2026-03-28T06:15:00-05:00",
    "clave_acceso": "2803202601091234567800110010010000000011234567895",
    "comprobante": "<factura>...</factura>",
    "mensajes": []
  },
  "xml_firmado": null
}
```

> 💡 Para incluir el XML firmado en base64 en la respuesta, agrega `?incluir_xml=true` al URL.

### Descargar el RIDE (PDF)

Una vez emitida la factura, descarga el comprobante en PDF:

```
GET /api/v1/facturas/1/pdf
```

El PDF se abre directamente en el navegador o se puede descargar para enviar por **WhatsApp**.

### Consultar historial

```
GET /api/v1/facturas?limite=50&estado=AUTORIZADO
```

---

## 🔧 Modo Simulación vs. Producción

| Aspecto | Simulación (actual) | Producción |
|---------|:-------------------:|:----------:|
| Firma XML | Mock (no firma realmente) | XAdES-BES real con .p12 |
| Archivo .p12 | No requerido | **Obligatorio** |
| `SRI_AMBIENTE` | `1` (pruebas) | `2` (producción) |
| Estado SRI | `DEVUELTA` (RUC ficticio) | `AUTORIZADO` |

Para pasar a producción:
1. Obtener firma electrónica real (.p12)
2. Reemplazar `xml_signer.py` con la implementación criptográfica
3. Cambiar `SRI_AMBIENTE=2` en `.env`
4. Usar un RUC real y autorizado para facturación electrónica

---

## 📄 Licencia

Proyecto desarrollado para uso interno. Adapte según sus necesidades.
