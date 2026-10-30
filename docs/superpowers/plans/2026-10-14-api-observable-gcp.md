# API observable en GCP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Entregar la API, simulador, infraestructura y guía operativa del laboratorio.

**Architecture:** `backend` procesa pedidos y escribe logs JSON; `simulator` genera carga asíncrona y CSV; Terraform empaqueta y despliega la función y la observabilidad se configura desde la consola.

**Tech Stack:** Python 3.13, Flask/Functions Framework, httpx, numpy, Terraform, Google Cloud.

**Spec:** `docs/superpowers/specs/2026-10-14-api-observable-gcp-design.md`

## Global Constraints

- La entrada es `handle`; runtime `python313`; región predeterminada `us-central1`.
- No guardar identificadores de proyecto ni credenciales.
- Crear métricas basadas en logs antes de ejecutar el simulador.

## Review Focus

- Payloads JSON ausentes o malformados devuelven 400.
- Pedidos inexistentes devuelven 404 y cancelación repetida devuelve 409.
- Fallas inyectadas tienen `outcome=server_error` y log completo.
- El simulador conserva `request_id` y todas las columnas del CSV.
- Terraform restringe el acceso al mínimo indicado por el enunciado.

### Task 1: API de pedidos y logs

**Files:** Create `backend/main.py`, `backend/requirements.txt`, `tests/test_backend.py`.

- [ ] Escribir pruebas para crear, consultar, cancelar, errores y logging.
- [ ] Ejecutar `pytest tests/test_backend.py -v` y comprobar RED.
- [ ] Implementar `handle(request)` y ejecutar la prueba en verde.

### Task 2: Simulador

**Files:** Create `simulator/simulator.py`, `simulator/config.json`, `tests/test_simulator.py`.

- [ ] Probar programación truncada y filas CSV.
- [ ] Ejecutar las pruebas en RED, implementar y comprobar verde.

### Task 3: Infraestructura y documentación

**Files:** Create `infra/*.tf`, `infra/terraform.tfvars.example`, `README.md`.

- [ ] Declarar el despliegue gen2 y permisos del enunciado.
- [ ] Documentar autenticación, apply, métricas, dashboard, simulación y destroy.
