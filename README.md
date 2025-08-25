# Interfaz Mettler Toledo - Zebra

Sistema completo de simulación e integración entre chequeadores de peso Mettler Toledo y impresoras Zebra ZPL.

## 🚀 Instalación Rápida

```bash
git clone <este-repositorio>
cd mettler_zebra_interface
pip install -r requirements.txt
```

## 🎯 Programas Principales

### 1. Simulador Mettler Toledo (`mettler_simulator.py`)
Simula el comportamiento de un chequeador de pesos Mettler Toledo:
- ✅ Generación de datos de peso realistas
- ✅ Protocolo de comunicación serie (STX/ETX)
- ✅ Códigos de producto configurables
- ✅ Estados de pesaje (OK, Under, Over)

### 2. Convertidor de Protocolo (`protocol_converter.py`) 
Convierte mensajes Mettler Toledo a comandos ZPL Zebra:
- ✅ Parsing de mensajes Mettler Toledo
- ✅ Generación de etiquetas ZPL
- ✅ Múltiples plantillas (estándar, compacta, detallada)
- ✅ Configuración flexible

### 3. Simulador Zebra (`zebra_simulator.py`)
Simula una impresora Zebra ZPL:
- ✅ Servidor TCP puerto 9100
- ✅ Procesamiento de comandos ZPL
- ✅ Cola de impresión
- ✅ Respuestas de estado

## 🔧 Uso Básico

### Ejemplo Simple
```python
from src.mettler_simulator import MettlerToledoSimulator
from src.protocol_converter import ProtocolConverter
from src.zebra_simulator import ZebraSimulator

# Crear componentes
mettler = MettlerToledoSimulator('COM3')
converter = ProtocolConverter()
zebra = ZebraSimulator()

# Usar...
```

### Ejecutar Ejemplos
```bash
# Ejemplo básico
python examples/basic_usage.py

# Ejemplo continuo
python examples/basic_usage.py --continuo

# Aplicación completa
python src/main.py
```

## 📊 Características del Sistema

### Protocolo Mettler Toledo
- **Formato**: `STX + datos + ETX + checksum + CRLF`
- **Datos**: `WT,peso,unidad,estado,target,producto,timestamp`
- **Estados**: S=Stable, U=Unstable, O=Over, T=Under

### Protocolo Zebra ZPL
- **Puerto**: TCP 9100
- **Comandos**: ^XA...^XZ (inicio/fin etiqueta)
- **Campos**: ^FD (datos), ^FO (posición), ^A (fuente)

### Plantillas ZPL Incluidas

#### Estándar
- Peso prominente centro
- Producto y fecha
- Estado visual

#### Compacta  
- Diseño reducido
- Información esencial
- Ahorro de papel

#### Detallada
- Información completa
- Códigos de barras
- Logo empresa

## ⚙️ Configuración

### Mettler Config (`config/mettler_config.json`)
```json
{
  "serial_port": "COM3",
  "baud_rate": 9600,
  "weight_range": [800, 1500],
  "products": ["PROD001", "PROD002", "PROD003"]
}
```

### Zebra Config (`config/zebra_config.json`)
```json
{
  "tcp_host": "127.0.0.1",
  "tcp_port": 9100,
  "label_width": 4,
  "label_height": 3,
  "dpi": 203
}
```

## 🖥️ Aplicación de Integración

La aplicación principal (`main.py`) proporciona:

- **Monitoreo en tiempo real**
- **Estadísticas de conversión**
- **Modo interactivo**
- **Logs detallados**
- **Gestión de errores**

### Comandos Interactivos
- `status` - Ver estado de componentes
- `stats` - Estadísticas de operación  
- `test` - Enviar datos de prueba
- `config` - Mostrar configuración
- `help` - Ayuda de comandos
- `quit` - Salir

## 🧪 Testing

### Sin Hardware Real
```python
# Usar simuladores sin puertos serie
from src.mettler_simulator import MettlerToledoSimulatorNoSerial

mettler = MettlerToledoSimulatorNoSerial()
# Resto igual...
```

### Con Hardware Real
```python
# Configurar puertos reales
mettler = MettlerToledoSimulator('COM3')  # Puerto Mettler
# Zebra real en IP:9100
```

## 📁 Estructura del Proyecto

```
mettler_zebra_interface/
├── src/
│   ├── mettler_simulator.py      # Simulador Mettler Toledo
│   ├── protocol_converter.py     # Convertidor de protocolo
│   ├── zebra_simulator.py        # Simulador Zebra
│   └── main.py                   # Aplicación integrada
├── config/
│   ├── mettler_config.json       # Configuración Mettler
│   └── zebra_config.json         # Configuración Zebra
├── examples/
│   └── basic_usage.py            # Ejemplos de uso
├── requirements.txt              # Dependencias Python
└── README.md                     # Esta documentación
```

## 🔍 Alternativas Evaluadas

### Librerías GitHub Investigadas
- **py-zebra-zpl**: Generación ZPL básica
- **zebra_day**: Comunicación TCP Zebra
- **easyzebra**: Templates ZPL predefinidos

### Tecnologías Consideradas
- **Python**: ✅ Elegido - Ecosistema robusto
- **Node-RED**: ⚡ Alternativa visual (ejemplos disponibles)
- **C#**: 🏭 Para entornos Windows industriales

## 🚀 Próximos Pasos

1. **Testing con hardware real**
2. **Optimización de rendimiento** 
3. **Interfaz web de monitoreo**
4. **Integración con sistemas ERP**
5. **Soporte para más modelos Mettler**

## 🤝 Contribución

El código está estructurado para fácil extensión:
- Nuevas plantillas ZPL en `protocol_converter.py`
- Configuraciones adicionales en `/config`
- Protocolos alternativos como nuevos simuladores

## 📞 Soporte

Para dudas sobre implementación, consultar:
- Documentación Mettler Toledo MT-SICS
- Manual ZPL Programming Guide
- Ejemplos en `/examples`

---

✨ **¡Sistema completo listo para usar!** ✨
