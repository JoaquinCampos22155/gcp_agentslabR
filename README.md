# API serverless observable en GCP

## Preparación de GCP

1. En [Google Cloud Console](https://console.cloud.google.com/), crea o selecciona un proyecto y asocia una cuenta de facturación si la organización lo exige. Copia su **Project ID** (no el nombre visible).
2. En esta máquina inicia credenciales de aplicación: `gcloud auth application-default login`. Esta operación abre el navegador y puede reemplazar credenciales ADC existentes.
3. Copia `infra/terraform.tfvars.example` a `infra/terraform.tfvars` y reemplaza el valor de `project_id`. Ese archivo está ignorado para no publicar datos locales.

## Despliegue

Desde `infra/`, ejecuta `terraform init`, revisa el plan con `terraform plan`, y solo después confirma `terraform apply`. Si el primer build de la función falla, espera un minuto y repite el apply. Copia el output `function_url` en `simulator/config.json`.

## Observabilidad y tráfico

Terraform crea antes del tráfico las métricas basadas en logs `orders_request_completed`, `orders_client_errors`, `orders_server_errors` y `orders_latency_ms`, además del dashboard `Observable Orders API`. El dashboard combina tasa nativa de Cloud Run, las métricas de logs y un panel con los logs estructurados. Abre el output `log_analytics_console` para ejecutar y graficar consultas SQL sobre la tabla indicada en `log_analytics_view`.

La consulta reproducible para la gráfica de negocio está en `docs/log-analytics.sql`: agrupa solicitudes y latencia promedio por minuto, categoría y resultado. Después de ejecutarla en Log Analytics, usa **Chart** y agrégala al dashboard `Observable Orders API`.

Actualiza `target_url` en `simulator/config.json` con el output `function_url` y ejecuta `python simulator/simulator.py`; producirá `simulator/requests.csv`.

## Validación local

Con un entorno que contenga las dependencias de `backend/requirements.txt` y `simulator/requirements.txt`, ejecuta `pytest tests -v`. Para el entorno actual se usa `C:\Users\jjcam\AppData\Local\Programs\Python\Python312\python.exe -m pytest tests -v --basetemp .pytest-tmp`.

## Limpieza

Tras guardar evidencias del dashboard, ejecuta `terraform destroy`. El upgrade de Log Analytics en `_Default` y las APIs habilitadas no se revierten automáticamente.
