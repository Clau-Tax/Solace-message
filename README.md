# Proyecto Global Dispatch — NewCron

Sistema que conecta transportistas de car haulers con predios de automóviles,
usando **Solace PubSub+ Cloud** como bróker de mensajería y **Python** para
la lógica de validación y las interfaces web.

El proyecto contiene 4 programas independientes escritos en Python que se
comunican **únicamente a través de Solace** (nunca se llaman entre sí
directamente):

🐍 `publish_request.py` — simula al **cliente** publicando una solicitud de carga.
🐍 `validator.py` — valida la solicitud y decide si se acepta o se cancela.
🐍 `carrier_dashboard.py` — app web donde los **transportistas** ven y aceptan cargas.
🐍 `client_status_panel.py` — app web donde los **clientes** ven el estado de sus solicitudes.
📨 **Solace PubSub+ Cloud** — recibe, enruta y entrega todos los mensajes entre ellos.

## 🔄 ¿Cómo funciona este proyecto?

El flujo completo, de principio a fin, es:

```
┌───────────────────┐
│                   │
│   CLIENTE         │   publish_request.py
│   (predio de      │
│    autos)         │
└─────────┬─────────┘
          │
          │ 1. Publica solicitud de carga
          │    topic: dispatch/request/new
          ▼
┌─────────────────────────┐
│                         │
│   Solace PubSub+ Cloud   │
│   (Event Broker)        │
│                         │
└────────────┬────────────┘
             │
             │ 2. Entrega el mensaje
             ▼
┌───────────────────┐
│                   │
│   VALIDADOR       │   validator.py
│                   │
│  - ¿pickup ya     │
│    pasó?          │
│  - ¿pickup es hoy │
│    y ya son +3pm? │
│  - ¿delivery ≥    │
│    pickup +1 día? │
└─────────┬─────────┘
          │
          │ 3. Publica el resultado (dos posibles caminos)
          │
   ┌──────┴───────────────────────────┐
   │                                   │
   ▼ Si es VÁLIDA                      ▼ Siempre (válida o no)
topic: dispatch/carrier/available   topic: dispatch/client/status
   │                                   │
   ▼                                   ▼
┌───────────────────┐        ┌───────────────────┐
│                   │        │                   │
│  TRANSPORTISTA    │        │   CLIENTE         │
│  (dashboard web)  │        │   (panel web)     │
│                   │        │                   │
│ carrier_dashboard │        │ client_status_    │
│      .py          │        │    panel.py       │
│  puerto 5001      │        │  puerto 5002      │
└─────────┬─────────┘        └───────────────────┘
          │                        ve "Accepted" ✅
          │ 4. Transportista le da                o "Cancelled" ❌
          │    clic a "Aceptar"                    con el motivo
          ▼
   topic: dispatch/carrier/accepted
   (evento de aviso; aquí en el futuro
    se conectaría, por ejemplo, un
    servicio que le manda el email
    al cliente)
```

En palabras simples:
1. El **cliente** manda su solicitud (fechas, vehículo, ruta).
2. El **validador** la revisa contra las reglas de negocio y decide si sigue o se cancela.
3. Si sigue, aparece automáticamente en el **dashboard de transportistas**; en cualquier caso, el **cliente** ve el resultado en su propio panel.
4. Cuando un transportista la acepta, se avisa a Solace (para que, en un sistema real, dispare el correo de confirmación).

Ningún programa conoce a los demás directamente — todos hablan **solo con
Solace**, publicando en un tópico o escuchando una cola. Eso es lo que hace
que el sistema esté desacoplado: se puede apagar, reiniciar o reemplazar
cualquiera de las 4 piezas sin tocar las otras.

## Arquitectura

```
┌────────────────┐   topic: dispatch/request/new    ┌──────────────┐
│ publish_request │ ───────────────────────────────► │Q.validator.  │
│ (simula cliente)│                                   │  incoming    │
└────────────────┘                                   └──────┬───────┘
                                                              │
                                                              ▼
                                                       ┌──────────────┐
                                                       │  validator.py │
                                                       │ (valida       │
                                                       │  fechas/hora) │
                                                       └───┬───────┬──┘
                            topic: dispatch/carrier/available   topic: dispatch/client/status
                                       │                                   │
                                       ▼                                   ▼
                          ┌──────────────────────┐         ┌────────────────────────┐
                          │Q.carrier.available.  │         │  Q.client.status        │
                          │  loads               │         │                         │
                          └──────────┬───────────┘         └───────────┬────────────┘
                                     │                                  │
                                     ▼                                  ▼
                       ┌────────────────────────┐        ┌─────────────────────────┐
                       │ carrier_dashboard.py    │        │ client_status_panel.py  │
                       │ (Flask, puerto 5001)    │        │ (Flask, puerto 5002)    │
                       │ Dashboard transportistas│        │ Panel de clientes       │
                       └───────────┬─────────────┘        └─────────────────────────┘
                                   │ al aceptar, publica:
                                   ▼
                       topic: dispatch/carrier/accepted
```

## Colas y tópicos en Solace

| Cola | Suscrita a tópico | Consumida por |
|---|---|---|
| `Q.validator.incoming` | `dispatch/request/new` | `validator.py` |
| `Q.carrier.available.loads` | `dispatch/carrier/available` | `carrier_dashboard.py` |
| `Q.client.status` | `dispatch/client/status` | `client_status_panel.py` |

Adicionalmente, `carrier_dashboard.py` publica al tópico `dispatch/carrier/accepted`
cuando un transportista acepta una carga (evento libre, sin cola consumidora
todavía; pensado para un futuro servicio de notificaciones por correo).

## Reglas de validación

1. `pickupDate` no puede ser anterior a la fecha actual.
2. Si `pickupDate` es hoy, la solicitud debe haber llegado **antes de las 3:00 p.m.**
3. `deliveryDate` debe ser al menos 1 día posterior a `pickupDate`.

Si alguna regla falla, se publica `status: "Cancelled"` con el motivo. Si todas
pasan, se publica `status: "Accepted"` y la carga queda disponible para
transportistas.

## Estructura del proyecto

```
global_dispatch/
├── requirements.txt
├── .env.example          # plantilla de credenciales (copiar a .env)
├── .gitignore
└── src/
    ├── config.py          # credenciales + nombres de tópicos/colas
    ├── solace_utils.py    # conexión reutilizable a Solace
    ├── validation.py      # reglas de negocio (fechas/hora), testeable
    ├── validator.py       # consumidor + publicador del validador
    ├── carrier_dashboard.py   # Flask: dashboard de transportistas (5001)
    ├── client_status_panel.py # Flask: panel de clientes (5002)
    ├── publish_request.py     # simula una solicitud de cliente
    ├── test_connection.py     # prueba simple de conexión a Solace
    └── templates/
        ├── carrier_dashboard.html
        └── client_status_panel.html
```

## Instalación

### 1. Requisitos previos
- Python 3.10+
- Una cuenta y un servicio ("Messaging Service") en [Solace Cloud](https://console.solace.cloud) (plan Developer, gratis)
- Las 3 colas creadas y suscritas a sus tópicos (ver tabla arriba)

### 2. Clonar y preparar el entorno

```bash
git clone <URL-de-este-repo>
cd global_dispatch
python -m venv venv
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

pip install -r requirements.txt
```

### 3. Configurar credenciales

Copia `.env.example` a `.env` y llena los valores con los datos de tu servicio
de Solace Cloud (pestaña **Connect → Connect with Python → Solace Python**):

```
SOLACE_HOST=tcps://tu-host.messaging.solace.cloud:55443
SOLACE_VPN=tu-vpn-name
SOLACE_USERNAME=solace-cloud-client
SOLACE_PASSWORD=tu-password-real
```

### 4. Certificados TLS

Descarga **"Root CA PEM"** y **"Root G2 PEM"** desde la misma pantalla de
Solace Cloud, y colócalos en una carpeta `certs/` en la raíz del proyecto.

### 5. Probar la conexión

```bash
python src/test_connection.py
```

Debe imprimir `✅ ¡Conexión exitosa al broker de Solace Cloud!`.

## Cómo correr el sistema completo

Abre 4 terminales (todas con el entorno virtual activado):

```bash
# Terminal 1 — el validador
python src/validator.py

# Terminal 2 — dashboard de transportistas
python src/carrier_dashboard.py
# abrir http://127.0.0.1:5001

# Terminal 3 — simular una solicitud de cliente
python src/publish_request.py

# Terminal 4 — panel de clientes
python src/client_status_panel.py
# abrir http://127.0.0.1:5002
```

Flujo esperado:
1. `publish_request.py` publica una solicitud.
2. `validator.py` la recibe, valida las fechas/hora, y publica el resultado.
3. Si es válida: aparece en `http://127.0.0.1:5001` (dashboard) y también
   como "Accepted" en `http://127.0.0.1:5002` (panel de cliente).
4. Al darle clic a "Aceptar" en el dashboard, la carga desaparece de la lista
   y se publica un evento a `dispatch/carrier/accepted`.
5. Si la solicitud es inválida (ej. `pickupDate` en el pasado), aparece como
   "Cancelled" en el panel de cliente con el motivo.

Para probar un caso inválido, edita `pickupDate` en `publish_request.py`
a una fecha pasada y vuelve a correrlo.

## 🧪 Probando el ejemplo

Para comprobar que todo funciona, primero deja corriendo el validador y las
dos apps web (dashboard y panel), en espera:

```
validator.py           carrier_dashboard.py       client_status_panel.py
     │                         │                           │
     │ esperando...            │ esperando...               │ esperando...
     ▼                         ▼                           ▼
        Solace PubSub+ Cloud (conectados, escuchando sus colas)
```

Después ejecuta el publicador de prueba:

```
publish_request.py
     │
     │ "Solicitud 6600111: Milford, MA → Shippensburg, PA"
     ▼
Solace PubSub+ Cloud
```

El broker entrega el mensaje al validador, que decide y reparte el resultado:

```
Solace PubSub+ Cloud
     │
     │ "Solicitud válida"
     ├──────────────────────────────┬───────────────────────────┐
     ▼                              ▼                           
carrier_dashboard.py          client_status_panel.py
(la carga aparece en           (aparece "Accepted" ✅
 la tabla, puerto 5001)         en la tabla, puerto 5002)
```

Así se puede observar el flujo completo, de punta a punta, usando solo
Solace como intermediario entre los 4 programas.

## Notas de diseño

- Las apps web usan **polling cada 3 segundos** (fetch a un endpoint JSON)
  en vez de WebSockets, para mantener el proyecto simple.
- El estado de cargas/solicitudes se guarda **en memoria** (no en base de
  datos), suficiente para el alcance de este proyecto.
- Las credenciales viven en `.env` (nunca se suben a git, ver `.gitignore`).
