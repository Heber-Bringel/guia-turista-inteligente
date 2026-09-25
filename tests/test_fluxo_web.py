"""Testes de comportamento do fluxo web (rotas, sessão, idempotência e persistência JSON).

Rodam offline: as chamadas HTTP externas (geocoding, clima, OSRM) são simuladas e o Gemini fica
sem chave (aciona o guia de contingência). Uso: python -m unittest discover -s tests -v
"""

import json
import os
import shutil
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from typing import Any
from unittest import mock

import httpx

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
os.environ["GEMINI_API_KEY"] = ""  # sem chave -> guia de contingência imediato

import app as aplicacao

CIDADES = {
    "teresina": (-5.089, -42.801, "Piauí"),
    "fortaleza": (-3.717, -38.543, "Ceará"),
    "salvador": (-12.972, -38.501, "Bahia"),
    "recife": (-8.054, -34.881, "Pernambuco"),
}


def _resposta(url: str, params: dict | None) -> httpx.Response:
    """Simula Open-Meteo (geocoding e clima) e OSRM."""
    req = httpx.Request("GET", url)
    corpo: dict[str, Any]
    if "geocoding-api" in url:
        nome = str((params or {}).get("name", "")).split()[0].lower()
        if nome in CIDADES:
            lat, lon, estado = CIDADES[nome]
            corpo = {"results": [{"name": nome.title(), "latitude": lat, "longitude": lon, "admin1": estado}]}
        else:
            corpo = {}
        return httpx.Response(200, json=corpo, request=req)
    if "api.open-meteo.com" in url:
        corpo = {"current": {"temperature_2m": 28.5, "relative_humidity_2m": 40, "wind_speed_10m": 12.0}}
        return httpx.Response(200, json=corpo, request=req)
    corpo = {
        "code": "Ok",
        "routes": [{"distance": 592000.0, "duration": 30780.0}],
        "waypoints": [{"distance": 10.0}, {"distance": 20.0}],
    }
    return httpx.Response(200, json=corpo, request=req)


def _apontar_json(caminho: Path) -> None:
    """Redireciona VIAGENS_FILE em todos os módulos que o importaram."""
    for nome, modulo in list(sys.modules.items()):
        if modulo is not None and hasattr(modulo, "VIAGENS_FILE") and nome.split(".")[0] in ("app", "config", "models", "controllers"):
            setattr(modulo, "VIAGENS_FILE", caminho)  # noqa: B010


def _limpar_estado_memoria() -> None:
    for modulo in list(sys.modules.values()):
        if modulo is None:
            continue
        for atributo in ("viagens_visitante_memoria", "requisicoes_recentes"):
            estado = getattr(modulo, atributo, None)
            if isinstance(estado, dict) and getattr(modulo, "__name__", "").split(".")[0] in ("app", "models", "controllers"):
                estado.clear()


FORM = {"origem_cidade": "Teresina", "origem_uf": "PI", "destino_cidade": "Fortaleza", "destino_uf": "CE"}


class FluxoWebTest(unittest.TestCase):
    def setUp(self) -> None:
        self.pasta = Path(tempfile.mkdtemp())
        self.json = self.pasta / "viagens.json"
        _apontar_json(self.json)
        _limpar_estado_memoria()
        patcher = mock.patch.object(httpx.Client, "get", lambda self, url, **kw: _resposta(str(url), kw.get("params")))
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(shutil.rmtree, self.pasta, True)

    def dados(self) -> dict:
        return json.loads(self.json.read_text(encoding="utf-8"))

    def cliente_logado(self, user_id: str = "user1"):
        c = aplicacao.app.test_client()
        with c.session_transaction() as s:
            s["usuario"] = {"id": user_id, "nome": "Teste", "email": "t@t", "foto": "http://x/f.png", "visitante": False}
        return c

    # --- 404 / 405 ---------------------------------------------------------------------------
    def test_rotas_invalidas_redirecionam_para_home(self):
        c = self.cliente_logado()
        for url in ("/rota-inexistente", "/viagens/criar", "/viagens/deletar/abc"):
            r = c.get(url)
            self.assertEqual(r.status_code, 302, url)
            self.assertTrue(r.location.endswith("/"), url)

    # --- páginas -----------------------------------------------------------------------------
    def test_home_e_json_respondem_200(self):
        self.assertEqual(aplicacao.app.test_client().get("/").status_code, 200)
        r = self.cliente_logado().get("/viagens/json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.mimetype, "application/json")
        self.assertEqual(self.cliente_logado().get("/api/viagens").status_code, 200)

    # --- criar / listar / deletar ------------------------------------------------------------
    def test_criar_viagem_persiste_schema_e_aparece_na_home(self):
        c = self.cliente_logado()
        r = c.post("/viagens/criar", data=FORM)
        self.assertEqual(r.status_code, 302)
        usuario = self.dados()["usuarios"]["user1"]
        roteiro = usuario["roteiros"][-1]
        for chave in ("id", "origem", "destino", "geolocalizacao", "telemetria", "clima", "percurso", "dicas_destino", "diagnostico_ia", "metadados"):
            self.assertIn(chave, roteiro)
        self.assertEqual(roteiro["percurso"]["distancia"], "592.0 km")
        self.assertEqual(roteiro["percurso"]["tempo"], "8h 33min de carro")
        self.assertEqual(self.dados()["total_roteiros"], 1)
        html = c.get("/").get_data(as_text=True)
        self.assertEqual(html.count('class="viagem-card"'), 1)
        self.assertIn("Modo Contingência", html)

    def test_deletar_viagem_por_post(self):
        c = self.cliente_logado()
        c.post("/viagens/criar", data=FORM)
        roteiro_id = self.dados()["usuarios"]["user1"]["roteiros"][-1]["id"]
        self.assertEqual(c.get(f"/viagens/deletar/{roteiro_id}").status_code, 302)  # GET não apaga
        self.assertEqual(len(self.dados()["usuarios"]["user1"]["roteiros"]), 1)
        c.post(f"/viagens/deletar/{roteiro_id}")
        self.assertEqual(self.dados()["usuarios"]["user1"]["roteiros"], [])
        self.assertEqual(self.dados()["total_roteiros"], 0)

    def test_entrada_invalida_nao_cria_roteiro(self):
        c = self.cliente_logado()
        c.post("/viagens/criar", data={**FORM, "origem_uf": "XX"})
        c.post("/viagens/criar", data={**FORM, "destino_cidade": ""})
        self.assertFalse(self.json.exists())

    def test_sanitizacao_remove_html(self):
        c = self.cliente_logado()
        c.post("/viagens/criar", data={**FORM, "destino_cidade": "<b>Salvador</b>", "destino_uf": "BA"})
        self.assertNotIn("<", self.dados()["usuarios"]["user1"]["roteiros"][-1]["destino"])

    # --- idempotência e concorrência ---------------------------------------------------------
    def test_cliques_duplos_criam_um_unico_roteiro(self):
        status = []
        ts = [threading.Thread(target=lambda: status.append(self.cliente_logado().post("/viagens/criar", data=FORM).status_code)) for _ in range(5)]
        [t.start() for t in ts]
        [t.join() for t in ts]
        self.assertEqual(status, [302] * 5)
        self.assertEqual(len(self.dados()["usuarios"]["user1"]["roteiros"]), 1)

    def test_gravacoes_simultaneas_nao_perdem_roteiros(self):
        def criar(i: int) -> None:
            self.cliente_logado(f"user{i}").post("/viagens/criar", data=FORM)

        ts = [threading.Thread(target=criar, args=(i,)) for i in range(10)]
        [t.start() for t in ts]
        [t.join() for t in ts]
        self.assertEqual(self.dados()["total_roteiros"], 10)
        self.assertEqual(self.dados()["total_usuarios"], 10)

    # --- visitante ---------------------------------------------------------------------------
    def test_visitante_fica_so_em_memoria(self):
        c = aplicacao.app.test_client()
        c.get("/auth/demo")
        with c.session_transaction() as s:
            uid = s["usuario"]["id"]
        self.assertTrue(uid.startswith("visitante"))
        c.post("/viagens/criar", data=FORM)
        self.assertFalse(self.json.exists() and any(k.startswith("visitante") for k in self.dados()["usuarios"]))
        self.assertEqual(c.get("/").get_data(as_text=True).count('class="viagem-card"'), 1)
        merged = c.get("/viagens/json").get_json()
        self.assertIn(uid, merged["usuarios"])
        c.get("/auth/logout")
        self.assertEqual(c.get("/").get_data(as_text=True).count('class="viagem-card"'), 0)

    def test_visitante_com_memoria_zerada_nao_grava_no_json(self):
        c = aplicacao.app.test_client()
        c.get("/auth/demo")
        _limpar_estado_memoria()  # simula reinício do servidor com o cookie ainda válido
        c.post("/viagens/criar", data=FORM)
        self.assertFalse(self.json.exists() and any(k.startswith("visitante") for k in self.dados()["usuarios"]))

    # --- login Google ------------------------------------------------------------------------
    def test_callback_google_sem_token_volta_para_home(self):
        r = aplicacao.app.test_client().post("/auth/google/callback", data={})
        self.assertEqual(r.status_code, 302)

    def test_logout_limpa_sessao(self):
        c = self.cliente_logado()
        c.get("/auth/logout")
        with c.session_transaction() as s:
            self.assertNotIn("usuario", s)


if __name__ == "__main__":
    unittest.main(verbosity=2)
