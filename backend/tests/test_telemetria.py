"""Testes de observabilidade: health checks, readiness probe, Prometheus e telemetria."""

from fastapi.testclient import TestClient


def test_healthz_liveness_probe_retorna_200(client: TestClient) -> None:
    """Verifica se o probe de liveness responde 200 com informações da aplicação."""
    response = client.get("/healthz")
    assert response.status_code == 200
    dados = response.json()
    assert dados["status"] == "ok"
    assert "app" in dados
    assert "version" in dados


def test_readyz_readiness_probe_retorna_200(client: TestClient) -> None:
    """Verifica se o probe de readiness valida o cliente HTTP e diretório gravável."""
    response = client.get("/readyz")
    assert response.status_code == 200
    dados = response.json()
    assert dados["status"] == "ready"
    assert dados["http_client"] is True
    assert dados["storage_writable"] is True


def test_docs_e_redoc_disponiveis(client: TestClient) -> None:
    """Garante que a documentação interativa Swagger e Redoc estejam ativas."""
    res_docs = client.get("/docs")
    assert res_docs.status_code == 200
    assert "swagger" in res_docs.text.lower() or "html" in res_docs.text.lower()

    res_redoc = client.get("/redoc")
    assert res_redoc.status_code == 200
    assert "redoc" in res_redoc.text.lower() or "html" in res_redoc.text.lower()


def test_metricas_prometheus_exportador_em_texto_plano(client: TestClient) -> None:
    """Garante que o endpoint /metrics responde no formato compatível com scrape do Prometheus."""
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "text/plain" in response.headers["Content-Type"]

    conteudo = response.text
    assert "guia_turista_roteiros_total" in conteudo
    assert "guia_turista_requisicoes_ativas" in conteudo
    assert "guia_turista_circuit_breaker_status" in conteudo


def test_middleware_injeta_correlation_id_e_process_time(client: TestClient) -> None:
    """Verifica se todas as respostas contêm X-Request-ID e X-Process-Time."""
    response = client.get("/healthz")
    assert response.status_code == 200
    assert "X-Request-ID" in response.headers
    assert "X-Process-Time" in response.headers

    # Garante que X-Process-Time é numérico legível pelo frontend
    tempo_str = response.headers["X-Process-Time"]
    assert float(tempo_str) >= 0.0


def test_telemetria_json_operacional(client: TestClient) -> None:
    """Verifica endpoint consolidado de telemetria operacional com estado dos Circuit Breakers."""
    response = client.get("/api/v1/telemetria")
    assert response.status_code == 200
    dados = response.json()

    assert dados["status"] == "online"
    assert "total_roteiros_calculados" in dados
    assert "circuit_breakers" in dados
    assert "geocoding" in dados["circuit_breakers"]
    assert "clima" in dados["circuit_breakers"]
    assert "gemini" in dados["circuit_breakers"]

