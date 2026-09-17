# Integración con linuxserver/calibre-web

Esta guía explica cómo ejecutar el servidor MCP de Calibre **dentro** del contenedor
`lscr.io/linuxserver/calibre-web`, usando los hooks de linuxserver (`custom-cont-init.d`
y `custom-services.d`), sin necesidad de un contenedor aparte.

## Requisitos

- Contenedor `linuxserver/calibre-web` (basado en Ubuntu Noble, s6-overlay).
- Mod de Calibre activado para disponer de `calibredb` y `ebook-convert`:
  ```yaml
  environment:
    - DOCKER_MODS=linuxserver/mods:universal-calibre
  ```
- Este repositorio accesible desde el host, **fuera** del directorio que montas como
  `/config` (limitación documentada de linuxserver).
- Puerto `8084` libre (o el que elijas vía `MCP_PORT`).

## Cómo funciona

El arranque lo gestiona s6-overlay en dos fases:

1. **`custom-cont-init.d/01-install-mcp`** (una vez, como root, antes de los servicios):
   crea un virtualenv dedicado en `/config/mcp-venv` e instala las dependencias.
   Es idempotente: compara el hash de `requirements.txt` con un stamp y solo
   reinstala si cambió. El venv está aislado del venv de calibre-web (`/lsiopy`).
   El código se lee de `MCP_CODE_DIR` (por defecto `/opt/calibre_mcp`).

2. **`custom-services.d/calibre-mcp`** (servicio supervisado):
   arranca el servidor MCP en transporte SSE. Se ejecuta como el usuario `abc`
   (`s6-setuidgid`) para que los archivos que calibredb escriba en `/books` tengan
   el mismo propietario que usa calibre-web.

## Configuración

Añade estos mounts y puertos a tu compose de calibre-web:

```yaml
services:
  calibre-web:
    image: lscr.io/linuxserver/calibre-web:latest
    container_name: calibre-web
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=Etc/UTC
      - DOCKER_MODS=linuxserver/mods:universal-calibre
      # Opcionales:
      # - CALIBRE_LIBRARY_PATH=/books   # por defecto /books
      # - MCP_CODE_DIR=/opt/calibre_mcp # ruta del código, por defecto /opt/calibre_mcp
      # - MCP_HOST=0.0.0.0              # por defecto 0.0.0.0
      # - MCP_PORT=8084                 # por defecto 8084
    volumes:
      - /ruta/host/calibre-web/config:/config
      - /ruta/host/calibre/library:/books
      - /ruta/host/calibre_mcp:/opt/calibre_mcp:ro
      - /ruta/host/calibre_mcp/custom-cont-init.d:/custom-cont-init.d:ro
      - /ruta/host/calibre_mcp/custom-services.d:/custom-services.d:ro
    ports:
      - 8083:8083
      - 8084:8084
    restart: unless-stopped
```

> **Importante**: los scripts de `custom-cont-init.d/` y `custom-services.d/` deben
> ser ejecutables (`chmod +x`) y pertenecer a root. Al montarlos `:ro` desde el host,
> asegúrate de que el bit de ejecución esté activo.

## Conexión del cliente MCP

El servidor expone transporte SSE en:

```
http://<host-ip>:8084/sse
```

Ejemplo de configuración en un cliente MCP:

```json
{
  "mcpServers": {
    "calibre": {
      "url": "http://<host-ip>:8084/sse"
    }
  }
}
```

## Actualizar dependencias

Cuando cambies `requirements.txt`, basta con reiniciar el contenedor:
el script de init detecta el cambio de hash y reinstala automáticamente.

```bash
docker restart calibre-web
```

## Verificación y troubleshooting

- **Ver logs del arranque** (init + servicio):
  ```bash
  docker logs calibre-web | grep -i mcp
  ```
- **Comprobar el venv**:
  ```bash
  docker exec calibre-web /config/mcp-venv/bin/python -c "import fastmcp; print(fastmcp.__version__)"
  ```
- **Comprobar calibredb** (requiere el mod):
  ```bash
  docker exec calibre-web calibredb --version
  ```
- **Probar el endpoint SSE**:
  ```bash
  curl -N http://localhost:8084/sse
  ```

### Problemas comunes

| Síntoma | Causa / Solución |
|---|---|
| El servicio no arranca, log: `venv missing` | Falló el init. Revisa `docker logs calibre-web` para ver el error de `pip`/`venv`. |
| `calibredb executable not found` | Falta `DOCKER_MODS=linuxserver/mods:universal-calibre`. |
| Los scripts no se ejecutan | Deben estar en `/custom-cont-init.d` y `/custom-services.d` (raíz, no dentro de `/config`), ser `chmod +x` y propiedad de root. |
| Puerto 8084 inaccesible | Publica el puerto (`8084:8084`) y verifica el firewall del host. |
| Conflictos de dependencias en calibre-web | No debería ocurrir: el MCP usa su propio venv (`/config/mcp-venv`), nunca `/lsiopy`. |
