"""
Servicio de integración con Notion para CRM.
"""
import os
try:
    from notion_client import Client as NotionClient
except ImportError:
    NotionClient = None

def _build_notion_properties(nombre: str, estado: str, documento: str, direccion: str, proyecto: str, fecha):
    """Crea el diccionario de propiedades para la página de Notion según nombres configurables."""
    # Nombres de propiedades configurables por env
    prop_name = os.environ.get("NOTION_PROP_NAME", "Name")
    prop_status = os.environ.get("NOTION_PROP_STATUS", "Estado")
    prop_doc = os.environ.get("NOTION_PROP_DOCUMENTO", "Documento")
    prop_dir = os.environ.get("NOTION_PROP_DIRECCION", "Direccion")
    prop_project = os.environ.get("NOTION_PROP_PROYECTO", "Proyecto")
    prop_date = os.environ.get("NOTION_PROP_FECHA", "Fecha")

    # Fecha a ISO
    fecha_iso = None
    try:
        if hasattr(fecha, 'isoformat'):
            fecha_iso = fecha.isoformat()
        elif isinstance(fecha, str):
            fecha_iso = fecha
    except Exception:
        fecha_iso = None

    properties = {
        prop_name: {"title": [{"text": {"content": nombre or ""}}]},
        prop_doc: {"rich_text": [{"text": {"content": documento or ""}}]},
        prop_dir: {"rich_text": [{"text": {"content": direccion or ""}}]},
        prop_project: {"rich_text": [{"text": {"content": proyecto or ""}}]},
    }
    if fecha_iso:
        properties[prop_date] = {"date": {"start": fecha_iso}}

    # Intento 1: status
    properties_status = properties.copy()
    properties_status[prop_status] = {"status": {"name": estado}}

    # Intento 2: select
    properties_select = properties.copy()
    properties_select[prop_status] = {"select": {"name": estado}}

    return properties_status, properties_select


def agregar_cliente_a_notion_crm(nombre: str, documento: str, direccion: str, proyecto: str, fecha, estado: str = "En conversaciones"):
    """Agrega un registro en la base de datos de Notion CRM si las credenciales están disponibles.
    Usa el nombre de estado 'En conversaciones' por defecto.
    """
    token = os.environ.get("NOTION_API_TOKEN")
    database_id = os.environ.get("NOTION_CRM_DATABASE_ID")
    if not token or not database_id or NotionClient is None:
        # Integración deshabilitada
        return False, "Integración Notion no configurada"

    try:
        notion = NotionClient(auth=token)
        props_status, props_select = _build_notion_properties(nombre, estado, documento, direccion, proyecto, fecha)

        # Intentar crear con "status" primero
        try:
            notion.pages.create(parent={"database_id": database_id}, properties=props_status)
            return True, "Cliente agregado a Notion (status)"
        except Exception:
            # Reintentar con select
            notion.pages.create(parent={"database_id": database_id}, properties=props_select)
            return True, "Cliente agregado a Notion (select)"

    except Exception as e:
        return False, f"Error Notion: {e}"

