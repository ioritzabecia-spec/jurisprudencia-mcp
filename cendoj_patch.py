# Arreglo de la descarga de sentencias del CENDOJ
# Problema: el PDF llegaba cortado y pypdf fallaba con "Stream has ended unexpectedly".
# Solución: (1) descarga completa con la sesión del navegador, comprobando que el PDF
# está entero y reintentando; (2) lectura con PyMuPDF, que tolera PDF dañados.
import asyncio, logging
import pymupdf
from app.scraper import CendojScraper

log = logging.getLogger("cendoj_patch")
_original_download = CendojScraper.download_pdf_bytes


def _pdf_completo(b: bytes) -> bool:
    return bool(b) and b[:5] == b"%PDF-" and b"%%EOF" in b[-2048:]


async def _url_real(self, pdf_url: str) -> str:
    """El enlace del CENDOJ es una página contenedora; se busca dentro el PDF de verdad."""
    try:
        page = await self.context.new_page()
        await page.goto(pdf_url, timeout=60000)
        await page.wait_for_load_state("networkidle", timeout=60000)
        el = page.locator('object[data*="accessToPDF"], a[href*="accessToPDF"], iframe[src*="accessToPDF"], embed[src*="accessToPDF"]')
        url = None
        if await el.count() > 0:
            e = el.first
            for attr in ("data", "href", "src"):
                url = await e.get_attribute(attr)
                if url:
                    break
        await page.close()
        if url:
            if not url.startswith("http"):
                url = f"https://www.poderjudicial.es{url}" if url.startswith("/") else f"https://www.poderjudicial.es/search/{url}"
            return url
    except Exception as e:
        log.warning(f"No se pudo resolver la URL real del PDF: {e}")
    return pdf_url


async def download_pdf_bytes(self, pdf_url: str) -> bytes:
    mejor = b""
    url = await _url_real(self, pdf_url)
    for intento in range(1, 4):
        try:
            resp = await self.context.request.get(url, timeout=120000)
            cuerpo = await resp.body()
            log.info(f"Intento {intento}: HTTP {resp.status}, {len(cuerpo)} bytes, completo={_pdf_completo(cuerpo)}")
            if len(cuerpo) > len(mejor) and cuerpo[:5] == b"%PDF-":
                mejor = cuerpo
            if _pdf_completo(cuerpo):
                return cuerpo
        except Exception as e:
            log.warning(f"Intento {intento} fallido: {e}")
        await asyncio.sleep(2 * intento)
    # Último recurso: el método original del servidor
    try:
        cuerpo = await _original_download(self, pdf_url)
        if _pdf_completo(cuerpo) or len(cuerpo) > len(mejor):
            mejor = cuerpo
    except Exception as e:
        log.warning(f"Método original fallido: {e}")
    if not mejor:
        raise Exception("No se pudo descargar la sentencia del CENDOJ.")
    return mejor


async def download_pdf_text(self, pdf_url: str) -> str:
    cached = self._get_cached_text(pdf_url)
    if cached:
        return cached
    datos = await self.download_pdf_bytes(pdf_url)
    completo = _pdf_completo(datos)
    doc = pymupdf.open(stream=datos, filetype="pdf")
    partes = []
    for i, pagina in enumerate(doc):
        try:
            partes.append(pagina.get_text())
        except Exception as e:
            log.warning(f"Página {i + 1} ilegible: {e}")
    texto = "\n".join(p for p in partes if p).strip()
    if not texto:
        raise Exception("El PDF se descargó pero no contiene texto legible.")
    if completo:
        self._set_cached_text(pdf_url, texto)
    else:
        texto += ("\n\n[AVISO: el CENDOJ entregó el PDF incompleto tras varios intentos; "
                  "puede faltar el final de la resolución. Contrástalo en poderjudicial.es.]")
    return texto


CendojScraper.download_pdf_bytes = download_pdf_bytes
CendojScraper.download_pdf_text = download_pdf_text
