"""
Servicio de integración con Google Drive.
"""
import os
import io
import re
import datetime
import streamlit as st
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from src.config import ESTRUCTURA_CARPETAS

def obtener_siguiente_consecutivo(service, id_carpeta_padre):
    try:
        año_actual_corto = str(datetime.datetime.now().year)[-2:]
        query = f"'{id_carpeta_padre}' in parents and mimeType='application/vnd.google-apps.folder'"
        results = service.files().list(
            q=query, pageSize=1000, fields="files(name)",
            supportsAllDrives=True, includeItemsFromAllDrives=True
        ).execute()
        items = results.get('files', [])
        max_num = 0
        patron = re.compile(f"FV{año_actual_corto}(\\d{{3}})")
        if items:
            for item in items:
                match = patron.search(item['name'])
                if match:
                    numero = int(match.group(1))
                    if numero > max_num: max_num = numero
        return max_num + 1
    except Exception as e:
        st.error(f"Error al buscar consecutivo en Drive: {e}")
        return 1

def crear_subcarpetas(service, id_carpeta_padre, estructura):
    for nombre_carpeta, sub_estructura in estructura.items():
        file_metadata = {'name': nombre_carpeta, 'mimeType': 'application/vnd.google-apps.folder', 'parents': [id_carpeta_padre]}
        subfolder = service.files().create(body=file_metadata, fields='id', supportsAllDrives=True).execute()
        if sub_estructura:
            crear_subcarpetas(service, subfolder.get('id'), sub_estructura)

def subir_pdf_a_drive(service, id_carpeta_destino, nombre_archivo, pdf_bytes):
    try:
        file_metadata = {'name': nombre_archivo, 'parents': [id_carpeta_destino]}
        media = MediaIoBaseUpload(io.BytesIO(pdf_bytes), mimetype='application/pdf')
        file = service.files().create(
            body=file_metadata, media_body=media, fields='id, webViewLink', supportsAllDrives=True
        ).execute()
        st.info(f"📄 PDF guardado en la carpeta 'Propuesta y Contratación'.")
        return file.get('webViewLink')
    except Exception as e:
        st.error(f"Error al subir el PDF a Google Drive: {e}")
        return None

def subir_csv_a_drive(service, id_carpeta_destino, nombre_archivo, csv_content):
    """Sube un archivo CSV a Google Drive"""
    try:
        file_metadata = {'name': nombre_archivo, 'parents': [id_carpeta_destino]}
        media = MediaIoBaseUpload(io.BytesIO(csv_content.encode('utf-8')), mimetype='text/csv')
        file = service.files().create(
            body=file_metadata, media_body=media, fields='id, webViewLink', supportsAllDrives=True
        ).execute()
        st.info(f"📊 CSV guardado en la carpeta 'Administrativo y Financiero'.")
        return file.get('webViewLink')
    except Exception as e:
        st.error(f"Error al subir el CSV a Google Drive: {e}")
        return None
    
def subir_docx_a_drive(service, id_carpeta_destino, nombre_archivo, docx_bytes):
    try:
        file_metadata = {'name': nombre_archivo, 'parents': [id_carpeta_destino]}
        media = MediaIoBaseUpload(io.BytesIO(docx_bytes), mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
        service.files().create(body=file_metadata, media_body=media, fields='id', supportsAllDrives=True).execute()
        st.info(f"📄 Contrato guardado en la carpeta 'Permisos y Legal'.")
    except Exception as e:
        st.error(f"Error al subir el contrato a Google Drive: {e}")

def gestionar_creacion_drive(service, parent_folder_id, nombre_proyecto, pdf_bytes, nombre_pdf, contrato_bytes, nombre_contrato):
    try:
        folder_metadata = {'name': nombre_proyecto, 'mimeType': 'application/vnd.google-apps.folder', 'parents': [parent_folder_id]}
        folder = service.files().create(body=folder_metadata, fields='id, webViewLink', supportsAllDrives=True).execute()
        id_carpeta_principal_nueva = folder.get('id')
        
        if id_carpeta_principal_nueva:
            with st.spinner("Creando estructura de subcarpetas..."):
                crear_subcarpetas(service, id_carpeta_principal_nueva, ESTRUCTURA_CARPETAS)
            st.success("✅ Estructura de carpetas creada.")

            with st.spinner("Buscando carpeta de destino para el PDF..."):
                query = f"'{id_carpeta_principal_nueva}' in parents and name='01_Propuesta_y_Contratacion'"
                results = service.files().list(q=query, fields="files(id)", supportsAllDrives=True, includeItemsFromAllDrives=True).execute()
                items = results.get('files', [])
            
                if items:
                    id_carpeta_propuesta = items[0].get('id')
                    subir_pdf_a_drive(service, id_carpeta_propuesta, nombre_pdf, pdf_bytes)
                else:
                    st.warning("No se encontró la subcarpeta '01_Propuesta_y_Contratacion' para guardar el PDF.")
            with st.spinner("Buscando carpeta de destino para el contrato..."):
             query_contrato = f"'{id_carpeta_principal_nueva}' in parents and name='04_Permisos_y_Legal'"
             results_contrato = service.files().list(q=query_contrato, fields="files(id)", supportsAllDrives=True, includeItemsFromAllDrives=True).execute()
             items_contrato = results_contrato.get('files', [])
             if items_contrato:
                id_carpeta_contrato = items_contrato[0].get('id')
                subir_docx_a_drive(service, id_carpeta_contrato, nombre_contrato, contrato_bytes)
             else:
                st.warning("No se encontró la subcarpeta '04_Permisos_y_Legal'.")
        return folder.get('webViewLink')
    except Exception as e:
        st.error(f"Error en el proceso de Google Drive: {e}")
        return None

