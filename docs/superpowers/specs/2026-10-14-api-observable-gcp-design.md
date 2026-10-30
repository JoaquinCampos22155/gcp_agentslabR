# API observable en GCP - Diseño

## Objetivo

Construir una API HTTP de pedidos desplegable como Cloud Run Functions gen2 y observable desde un único dashboard de Cloud Monitoring.

## Decisiones

- Dominio: pedidos; estado en memoria apropiado para la práctica.
- Operaciones: crear, consultar y cancelar pedidos.
- Python 3.13, Functions Framework, Terraform >= 1.5 y proveedores Google >= 6.0.
- El simulador usa `httpx` asíncrono y `numpy` para programar 6,000 envíos durante una hora.

## Restricciones

- `handle` es el punto de entrada.
- Cada respuesta emite un evento JSON `request_completed` con los campos requeridos por el laboratorio.
- Las solicitudes inválidas producen 400, 404 o 409; las fallas inyectadas producen 500.
- La infraestructura habilita las APIs, Log Analytics y los permisos mínimos descritos en el enunciado.
- El `project_id` no se guarda: se proporciona en `terraform.tfvars` al desplegar.
