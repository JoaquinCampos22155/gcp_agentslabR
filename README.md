# API serverless observable en GCP

## Preparación de GCP

1. En [Google Cloud Console](https://console.cloud.google.com/), crea o selecciona un proyecto y asocia una cuenta de facturación si la organización lo exige. Copia su **Project ID** (no el nombre visible).
2. En esta máquina inicia credenciales de aplicación: `gcloud auth application-default login`. Esta operación abre el navegador y puede reemplazar credenciales ADC existentes.
3. Copia `infra/terraform.tfvars.example` a `infra/terraform.tfvars` y reemplaza el valor de `project_id`. Ese archivo está ignorado para no publicar datos locales.

## Despliegue

Desde `infra/`, ejecuta `terraform init`, revisa el plan con `terraform plan`, y solo después confirma `terraform apply`. Si el primer build de la función falla, espera un minuto y repite el apply. Copia el output `function_url` en `simulator/config.json`.

## Observabilidad y tráfico

Antes de ejecutar el simulador, crea métricas basadas en logs para `request_completed`, errores 4xx/5xx y latencia. En Cloud Monitoring crea un único dashboard con métricas nativas de la función, las métricas basadas en logs, paneles SQL de Log Analytics y un panel de logs. Después ejecuta `python simulator/simulator.py`; producirá `simulator/requests.csv`.

## Validación local

Con un entorno que contenga las dependencias de `backend/requirements.txt` y `simulator/requirements.txt`, ejecuta `pytest tests -v`. Para el entorno actual se usa `C:\Users\jjcam\AppData\Local\Programs\Python\Python312\python.exe -m pytest tests -v --basetemp .pytest-tmp`.

## Limpieza

Tras guardar evidencias del dashboard, ejecuta `terraform destroy`. El upgrade de Log Analytics en `_Default` y las APIs habilitadas no se revierten automáticamente.
