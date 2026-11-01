"""Banco de consultas de referencia: uv run pytest

Cada caso fija qué debe devolver el catálogo ante una consulta típica. No llama al modelo.
"""

import os

os.environ.setdefault("GEMINI_API_KEY_LOCAL", "clave-de-prueba")  # para importar sin .env
os.environ.setdefault("DEEPSEEK_API_KEY", "clave-de-prueba")  # igual, por si el .env usa MODO=deepseek

import pytest  # noqa: E402

import capacidades  # noqa: E402


@pytest.mark.parametrize(
    ("tramite", "condiciones", "esperado"),
    [
        ("diploma_academico", {}, "sobre plástico con broches"),
        ("diploma_academico", {}, "Certificado de Calificaciones de Grado"),
        ("titulo_profesional", {}, "legalizada por la UMSA"),
        ("titulo_profesional", {"nacionalidad": "extranjera"}, "consulado boliviano"),
        ("titulo_profesional", {"carrera": "medicina"}, "Salud Rural Obligatorio"),
        ("titulo_profesional", {"carrera": "odontologia"}, "Salud Rural Obligatorio"),
        ("titulo_profesional", {"carrera": "enfermeria"}, "Salud Rural Obligatorio"),
        ("titulo_profesional", {"carrera": "informatica"}, "Bs 15"),
        ("titulo_profesional", {"carrera": "derecho"}, "igualación"),
        ("titulo_profesional", {"excelencia_academica": True}, "Record Académico"),
        ("titulo_profesional", {}, "20 de noviembre de 2026"),
    ],
)
def test_consultas_de_referencia(tramite, condiciones, esperado):
    """La respuesta esperada aparece en los requisitos, la entrega o las notas."""
    ficha = capacidades.consultar_tramite(tramite, **condiciones)
    texto = " ".join(
        ficha["requisitos_obligatorios"] + ficha["requisitos_condicionales"] + ficha["entrega"] + ficha["notas"]
    )
    assert esperado in texto


def test_diploma_academico_sin_condiciones():
    ficha = capacidades.consultar_tramite("diploma_academico")
    assert ficha["por_confirmar"] == []
    assert len(ficha["requisitos_obligatorios"]) == 9
    assert {"concepto": "Nacionales, Licenciatura", "monto_bs": 1343} in ficha["costos_bs"]


def test_titulo_nacional_sin_condiciones():
    ficha = capacidades.consultar_tramite("titulo_profesional", nacionalidad="boliviana", carrera="otra", excelencia_academica=False)
    assert ficha["por_confirmar"] == []
    assert ficha["requisitos_condicionales"] == []
    assert len(ficha["requisitos_obligatorios"]) == 5
    assert ficha["codigo"].startswith("R-271")


def test_titulo_extranjero_paga_otra_tarifa():
    ficha = capacidades.consultar_tramite("titulo_profesional", nacionalidad="extranjera")
    assert {"concepto": "Extranjeros, Licenciatura", "monto_bs": 4846} in ficha["costos_bs"]


def test_titulo_excelencia_academica_es_gratuito():
    ficha = capacidades.consultar_tramite("titulo_profesional", excelencia_academica=True)
    assert {"concepto": "Excelencia Académica", "monto_bs": 0, "detalle": "Liberado; exige la liberación formal en la Caja Recaudadora"} in ficha["costos_bs"]


def test_sin_datos_pide_confirmar_las_condiciones():
    ficha = capacidades.consultar_tramite("titulo_profesional")
    assert ficha["por_confirmar"] == ["carrera", "excelencia_academica", "nacionalidad"]


def test_consulta_fuera_del_catalogo():
    assert "error" in capacidades.consultar_tramite("otro")  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("tramite", "tengo", "condiciones", "bucket", "esperado"),
    [
        ("diploma_academico", ["certificado de biblioteca"], {}, "cumplidos", "Biblioteca Central"),
        ("diploma_academico", ["fotocopia de la cedula"], {}, "cumplidos", "Cédula de Identidad"),
        ("diploma_academico", ["fotos para el diploma"], {}, "cumplidos", "fotografías"),
        ("titulo_profesional", ["diploma academico legalizado"], {}, "cumplidos", "Diploma Académico"),
        ("titulo_profesional", ["record academico"], {"excelencia_academica": True}, "cumplidos", "Record Académico"),
        ("titulo_profesional", ["servicio social"], {"carrera": "medicina"}, "cumplidos", "Salud Rural"),
        ("titulo_profesional", ["adelanto de sueldo"], {}, "no_reconocidos", "adelanto de sueldo"),
    ],
)
def test_lista_de_verificacion_de_referencia(tramite, tengo, condiciones, bucket, esperado):
    """Un documento declarado cae en el grupo que corresponde, o se devuelve como no reconocido."""
    ficha = capacidades.revisar_requisitos(tramite, tengo, **condiciones)
    assert any(esperado in texto for texto in ficha[bucket])


def test_lo_declarado_no_se_repite_en_cumplidos_y_pendientes():
    ficha = capacidades.revisar_requisitos("diploma_academico", ["biblioteca", "dos fotos"])
    assert set(ficha["cumplidos"]).isdisjoint(ficha["pendientes"])


def test_toda_ficha_cita_su_fuente_y_fecha():
    for tramite in capacidades.TRAMITES:
        ficha = capacidades.consultar_tramite(tramite)
        assert ficha["fuente"].startswith("https://titulos.umsa.bo/")
        assert ficha["vigencia"]["revisado"] == "2026-10-31"
