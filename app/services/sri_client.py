"""
Cliente SOAP para los web services offline del SRI (celcer / cel).

Servicios consumidos (zeep):
  ┌─────────────────────────────────────────────────────────────────────┐
  │ RecepcionComprobantesOffline                                        │
  │   Operación: validarComprobante(xml: base64)                        │
  │   WSDL pruebas: celcer.sri.gob.ec/…/RecepcionComprobantesOffline    │
  │   WSDL producción: cel.sri.gob.ec/…/RecepcionComprobantesOffline    │
  ├─────────────────────────────────────────────────────────────────────┤
  │ AutorizacionComprobantesOffline                                     │
  │   Operación: autorizacionComprobante(claveAccesoComprobante: str)   │
  │   WSDL pruebas: celcer.sri.gob.ec/…/AutorizacionComprobantesOffline│
  │   WSDL producción: cel.sri.gob.ec/…/AutorizacionComprobantesOffline│
  └─────────────────────────────────────────────────────────────────────┘

Notas de implementación:
  - Se usa un caché por URL de WSDL para evitar descargarlo en cada llamada.
  - El XML firmado se envía codificado en Base64 (string UTF-8, no bytes).
  - La consulta de autorización reintenta con back-off porque el SRI
    puede demorar entre 1-5 s en procesar el comprobante.
  - Todos los timeouts son configurables desde settings.
"""

import base64
import logging
import time
from functools import lru_cache

from requests import Session
from zeep import Client
from zeep.exceptions import Fault, TransportError
from zeep.transports import Transport

from ..config import settings
from ..models.schemas import AutorizacionResponse, MensajeSRI, RecepcionResponse

logger = logging.getLogger(__name__)

# ── Parámetros de conexión ───────────────────────────────
SOAP_TIMEOUT = 30          # segundos para connect + read
MAX_INTENTOS_AUTORIZACION = 3
ESPERA_ENTRE_INTENTOS = 2  # segundos (back-off lineal)


# ── Factoría de clientes SOAP con caché ──────────────────


@lru_cache(maxsize=4)
def _crear_cliente(wsdl_url: str) -> Client:
    """Crea y cachea un cliente zeep para la URL WSDL dada.

    El caché evita descargar y parsear el WSDL en cada petición.
    Se limpia automáticamente si la URL cambia (ej: cambio de ambiente).
    """
    session = Session()
    transport = Transport(session=session, timeout=SOAP_TIMEOUT)
    client = Client(wsdl=wsdl_url, transport=transport)
    logger.info("Cliente SOAP creado para: %s", wsdl_url)
    return client


# ── Utilidades de parseo ─────────────────────────────────


def _extraer_mensajes(nodo_mensajes) -> list[MensajeSRI]:
    """Extrae la lista de mensajes SRI de un nodo de respuesta SOAP.

    El SRI retorna mensajes en estructuras como:
      <mensajes><mensaje><identificador>70<tipo>ERROR<mensaje>…</mensajes>

    zeep los mapea a objetos con atributos; esta función los normaliza
    a nuestro modelo Pydantic MensajeSRI.
    """
    if nodo_mensajes is None:
        return []

    lista_raw = getattr(nodo_mensajes, "mensaje", [])
    if not isinstance(lista_raw, list):
        lista_raw = [lista_raw]

    mensajes: list[MensajeSRI] = []
    for m in lista_raw:
        mensajes.append(
            MensajeSRI(
                identificador=str(getattr(m, "identificador", "")),
                mensaje=str(getattr(m, "mensaje", "")),
                tipo=str(getattr(m, "tipo", "")),
                informacion_adicional=_safe_str(
                    getattr(m, "informacionAdicional", None)
                ),
            )
        )
    return mensajes


def _safe_str(valor) -> str | None:
    """Convierte a string o retorna None si el valor es nulo."""
    if valor is None:
        return None
    return str(valor)


# ═══════════════════════════════════════════════════════════
# a) RecepcionComprobantesOffline — validarComprobante
# ═══════════════════════════════════════════════════════════


def enviar_comprobante(xml_firmado: bytes) -> RecepcionResponse:
    """Envía el comprobante firmado al WS de recepción del SRI (celcer/cel).

    Operación SOAP: ``validarComprobante(xml)``

    El SRI espera el XML firmado codificado en Base64 como string UTF-8.
    La respuesta contiene un ``estado`` ('RECIBIDA' o 'DEVUELTA') y
    opcionalmente una lista de mensajes con errores/advertencias.

    Args:
        xml_firmado: XML firmado (bytes) generado por xml_signer.

    Returns:
        RecepcionResponse con estado, clave de acceso y mensajes.

    Raises:
        ConnectionError: Si no se puede conectar al WS del SRI.
        zeep.exceptions.Fault: Si el SRI responde con un SOAP Fault.
    """
    # El SRI espera un string Base64, NO bytes crudos
    xml_b64 = base64.b64encode(xml_firmado).decode("utf-8")

    url = settings.url_recepcion
    logger.info("Enviando comprobante a RecepcionComprobantesOffline: %s", url)

    try:
        client = _crear_cliente(url)
        respuesta = client.service.validarComprobante(xml_b64)
    except TransportError as e:
        logger.error("Error de transporte SOAP (recepción): %s", e)
        raise ConnectionError(
            f"No se pudo conectar al WS de recepción del SRI: {e}"
        ) from e
    except Fault as e:
        logger.error("SOAP Fault (recepción): %s", e)
        return RecepcionResponse(
            estado="DEVUELTA",
            clave_acceso="",
            mensajes=[
                MensajeSRI(
                    identificador="SOAP_FAULT",
                    mensaje=str(e.message),
                    tipo="ERROR",
                    informacion_adicional=_safe_str(e.detail),
                )
            ],
        )

    # ── Parsear respuesta ────────────────────────────────
    estado = str(getattr(respuesta, "estado", "DESCONOCIDO"))
    mensajes: list[MensajeSRI] = []

    # Estructura SRI: respuesta.comprobantes.comprobante[].mensajes.mensaje[]
    comprobantes = getattr(respuesta, "comprobantes", None)
    if comprobantes:
        lista_comp = getattr(comprobantes, "comprobante", [])
        if not isinstance(lista_comp, list):
            lista_comp = [lista_comp]
        for comp in lista_comp:
            mensajes.extend(
                _extraer_mensajes(getattr(comp, "mensajes", None))
            )

    logger.info(
        "Recepción SRI → estado=%s, mensajes=%d", estado, len(mensajes)
    )

    return RecepcionResponse(
        estado=estado,
        clave_acceso="",  # Se asigna en el router con la clave generada
        mensajes=mensajes,
    )


# ═══════════════════════════════════════════════════════════
# b) AutorizacionComprobantesOffline — autorizacionComprobante
# ═══════════════════════════════════════════════════════════


def consultar_autorizacion(clave_acceso: str) -> AutorizacionResponse:
    """Consulta la autorización de un comprobante en el SRI (celcer/cel).

    Operación SOAP: ``autorizacionComprobante(claveAccesoComprobante)``

    El SRI puede tardar entre 1 y 5 segundos en procesar un comprobante
    recién recibido. Por eso se implementa un mecanismo de reintentos
    con espera lineal (MAX_INTENTOS_AUTORIZACION × ESPERA_ENTRE_INTENTOS).

    La respuesta contiene:
      - estado: 'AUTORIZADO', 'NO AUTORIZADO', 'EN PROCESAMIENTO'
      - numeroAutorizacion: número de autorización (si fue autorizado)
      - fechaAutorizacion: fecha/hora de autorización
      - comprobante: XML del comprobante autorizado
      - mensajes: lista de errores/advertencias del SRI

    Args:
        clave_acceso: Clave de acceso de 49 dígitos del comprobante.

    Returns:
        AutorizacionResponse con datos de autorización o mensajes de error.

    Raises:
        ConnectionError: Si se agotan los reintentos sin conectar al SRI.
    """
    url = settings.url_autorizacion
    logger.info(
        "Consultando autorización en AutorizacionComprobantesOffline: %s "
        "| claveAcceso=%s",
        url,
        clave_acceso,
    )

    try:
        client = _crear_cliente(url)
    except TransportError as e:
        logger.error("Error al crear cliente SOAP (autorización): %s", e)
        raise ConnectionError(
            f"No se pudo conectar al WS de autorización del SRI: {e}"
        ) from e

    ultimo_error: str = ""

    for intento in range(1, MAX_INTENTOS_AUTORIZACION + 1):
        logger.debug("Intento de autorización %d/%d", intento, MAX_INTENTOS_AUTORIZACION)

        # ── Llamada SOAP ─────────────────────────────────
        try:
            respuesta = client.service.autorizacionComprobante(clave_acceso)
        except Fault as e:
            ultimo_error = str(e.message)
            logger.warning(
                "SOAP Fault (autorización) intento %d/%d: %s",
                intento,
                MAX_INTENTOS_AUTORIZACION,
                e,
            )
            if intento < MAX_INTENTOS_AUTORIZACION:
                time.sleep(ESPERA_ENTRE_INTENTOS)
                continue
            return AutorizacionResponse(
                estado="ERROR",
                clave_acceso=clave_acceso,
                mensajes=[
                    MensajeSRI(
                        identificador="SOAP_FAULT",
                        mensaje=ultimo_error,
                        tipo="ERROR",
                    )
                ],
            )
        except TransportError as e:
            ultimo_error = str(e)
            logger.warning(
                "Error de transporte (autorización) intento %d/%d: %s",
                intento,
                MAX_INTENTOS_AUTORIZACION,
                e,
            )
            if intento < MAX_INTENTOS_AUTORIZACION:
                time.sleep(ESPERA_ENTRE_INTENTOS)
                continue
            raise ConnectionError(
                f"No se pudo conectar al WS de autorización del SRI "
                f"tras {MAX_INTENTOS_AUTORIZACION} intentos: {e}"
            ) from e

        # ── Parsear respuesta ────────────────────────────
        # Estructura SRI:
        #   respuesta.autorizaciones.autorizacion[] →
        #     .estado, .numeroAutorizacion, .fechaAutorizacion,
        #     .comprobante, .mensajes.mensaje[]

        autorizaciones = getattr(respuesta, "autorizaciones", None)
        if not autorizaciones:
            logger.info("Sin nodo autorizaciones — intento %d", intento)
            if intento < MAX_INTENTOS_AUTORIZACION:
                time.sleep(ESPERA_ENTRE_INTENTOS)
                continue
            return AutorizacionResponse(
                estado="EN PROCESAMIENTO",
                clave_acceso=clave_acceso,
            )

        lista_aut = getattr(autorizaciones, "autorizacion", [])
        if not isinstance(lista_aut, list):
            lista_aut = [lista_aut]

        if not lista_aut:
            logger.info("Lista de autorizaciones vacía — intento %d", intento)
            if intento < MAX_INTENTOS_AUTORIZACION:
                time.sleep(ESPERA_ENTRE_INTENTOS)
                continue
            return AutorizacionResponse(
                estado="EN PROCESAMIENTO",
                clave_acceso=clave_acceso,
            )

        # Tomar la primera (y normalmente única) autorización
        aut = lista_aut[0]
        estado = str(getattr(aut, "estado", "DESCONOCIDO"))
        mensajes = _extraer_mensajes(getattr(aut, "mensajes", None))

        # Si aún está en procesamiento, reintentar
        if estado == "EN PROCESAMIENTO" and intento < MAX_INTENTOS_AUTORIZACION:
            logger.info("Comprobante en procesamiento — reintentando…")
            time.sleep(ESPERA_ENTRE_INTENTOS)
            continue

        fecha_aut = getattr(aut, "fechaAutorizacion", None)
        resultado = AutorizacionResponse(
            estado=estado,
            numero_autorizacion=_safe_str(
                getattr(aut, "numeroAutorizacion", None)
            ),
            fecha_autorizacion=str(fecha_aut) if fecha_aut else None,
            clave_acceso=clave_acceso,
            comprobante=_safe_str(getattr(aut, "comprobante", None)),
            mensajes=mensajes,
        )

        logger.info(
            "Autorización SRI → estado=%s, n.º autorización=%s",
            resultado.estado,
            resultado.numero_autorizacion or "(ninguno)",
        )
        return resultado

    # Si se agotan los intentos sin retornar (no debería llegar aquí)
    return AutorizacionResponse(
        estado="EN PROCESAMIENTO",
        clave_acceso=clave_acceso,
        mensajes=[
            MensajeSRI(
                identificador="MAX_REINTENTOS",
                mensaje=(
                    f"Se agotaron los {MAX_INTENTOS_AUTORIZACION} intentos "
                    "de consulta de autorización"
                ),
                tipo="ADVERTENCIA",
            )
        ],
    )
