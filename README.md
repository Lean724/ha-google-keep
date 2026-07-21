# Google Keep para Home Assistant

Integración custom para Home Assistant que conecta con **Google Keep** usando la
librería no oficial [`gkeepapi`](https://github.com/kiwiz/gkeepapi), permitiendo
leer y editar notas y checklists desde Home Assistant sin depender de servicios
externos como IFTTT o Google Tasks.

> ⚠️ `gkeepapi` es una librería **no oficial**. Google puede cambiar su API
> interna en cualquier momento y romper la sincronización. Ver la sección
> [Limitaciones](#limitaciones-de-gkeepapi) más abajo.

## Instalación mediante HACS

1. En HACS, andá a **Integraciones** → menú (⋮) → **Repositorios personalizados**.
2. Agregá la URL de este repositorio con la categoría **Integration**.
3. Buscá "Google Keep" en HACS e instalalo.
4. Reiniciá Home Assistant.
5. Andá a **Ajustes → Dispositivos y servicios → Agregar integración** y buscá
   "Google Keep".

## Configuración

Durante el Config Flow se te va a pedir:

| Campo | Descripción |
|---|---|
| Email de Google | Tu cuenta de Google. |
| Contraseña | Se usa solo para el login inicial; **no se guarda**. |
| Master token (opcional) | Si ya tenés uno de una sesión anterior de `gkeepapi`. |
| ID de dispositivo (opcional) | Se genera automáticamente si no lo indicás. |

Una vez configurada la cuenta, desde **Opciones** podés ajustar:

- Intervalo de actualización (1 / 5 / 10 / 30 minutos, o manual).
- Sincronización automática on/off.
- Lista por defecto para usar en automatizaciones/servicios.
- Mostrar notas/listas archivadas o eliminadas.
- Filtrar por etiqueta o por color.

## Entidades

- **`sensor.<nombre_de_la_lista>`** — un sensor por cada nota/lista de Keep.
  Estado: cantidad de elementos pendientes. Atributos: `title`, `id`,
  `item_count`, `checked_items`, `unchecked_items`, `last_updated`, `color`,
  `archived`.
- **`todo.<nombre_de_la_lista>`** — cada checklist de Keep aparece como una
  Todo List nativa de Home Assistant (agregar, completar, reabrir y borrar
  elementos).
- **`binary_sensor.has_pending_items`** — `on` si alguna lista tiene elementos
  sin completar.

## Servicios

| Servicio | Descripción |
|---|---|
| `google_keep.sync` | Fuerza una sincronización inmediata. |
| `google_keep.create_note` | Crea una nota de texto simple. |
| `google_keep.create_checklist` | Crea un checklist con una lista de elementos. |
| `google_keep.add_item` | Agrega un elemento a una lista existente. |
| `google_keep.remove_item` | Elimina un elemento de una lista. |
| `google_keep.complete_item` / `uncomplete_item` | Marca/desmarca un elemento. |
| `google_keep.archive` / `unarchive` | Archiva/desarchiva una nota o lista. |
| `google_keep.delete_note` / `restore_note` | Mueve a papelera / restaura. |

## Ejemplos de automatización

**Cuando la lavadora termina, agregar "Comprar jabón" a la lista de compras:**

```yaml
automation:
  - alias: "Lavadora terminó -> agregar jabón"
    trigger:
      - platform: state
        entity_id: sensor.lavadora
        to: "Finished"
    action:
      - service: google_keep.add_item
        data:
          list_id: "abc123"
          text: "Comprar jabón"
```

**Botón Zigbee agrega "Pilas AA":**

```yaml
automation:
  - alias: "Botón -> agregar pilas"
    trigger:
      - platform: device
        domain: zha
        device_id: "..."
        type: remote_button_short_press
    action:
      - service: google_keep.add_item
        data:
          list_id: "abc123"
          text: "Pilas AA"
```

**Comando de voz "Agregar leche":**

Se puede exponer `google_keep.add_item` como una acción de asistente conversacional,
o usar directamente la entidad `todo.*` con la integración nativa de listas de
tareas del asistente de Home Assistant.

## Eventos

- `google_keep_note_created`
- `google_keep_note_updated`
- `google_keep_note_deleted`
- `google_keep_sync_finished`

## Solución de problemas

- **"invalid_auth" al configurar**: revisá el email/contraseña. Si tenés
  verificación en 2 pasos, puede que necesites una contraseña de aplicación o
  un master token obtenido por fuera de Home Assistant.
- **Se piden credenciales de nuevo (reauth)**: el master token expiró o Google
  cerró la sesión; volvé a autenticarte desde la notificación de reauth.
- **Los cambios no se reflejan en Google Keep**: revisá el intervalo de
  sincronización, o llamá a `google_keep.sync` manualmente.
- **Errores repetidos de conexión**: comprobá la conectividad a internet del
  servidor de Home Assistant.

## Limitaciones de gkeepapi

- Es una librería no oficial basada en ingeniería inversa del cliente web de
  Google Keep; puede dejar de funcionar sin aviso si Google cambia su API.
- Toda la interacción con `gkeepapi` está encapsulada en `api.py`, para poder
  migrar de librería más fácilmente si hiciera falta.
- Las cuentas de Google Workspace con políticas de seguridad estrictas pueden
  bloquear este tipo de acceso.

## Licencia

MIT
