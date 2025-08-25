# Ejemplos Node-RED para Mettler-Zebra

## 🔄 Flujo Node-RED

El archivo `node_red_flow.json` contiene un flujo completo para Node-RED que replica la funcionalidad del sistema Python.

### Componentes del Flujo

1. **Serial Input** - Lee datos del puerto serie Mettler Toledo
2. **Parse Function** - Parsea mensajes formato MT-SICS 
3. **ZPL Generator** - Genera etiquetas ZPL desde datos Mettler
4. **TCP Output** - Envía ZPL a impresora Zebra
5. **Debug Node** - Monitoreo y debugging

### Configuración

#### Puerto Serie (Mettler Toledo)
- Puerto: COM3 (ajustar según sistema)
- Velocidad: 9600 baud
- Bits de datos: 8
- Paridad: None
- Bits de parada: 1

#### TCP Zebra
- Host: 192.168.1.100 (IP de impresora)
- Puerto: 9100
- Tipo: Cliente TCP

### Instalación en Node-RED

1. **Copiar el flujo**:
   ```bash
   # Copiar contenido de node_red_flow.json
   ```

2. **Importar en Node-RED**:
   - Abrir Node-RED
   - Menu → Import → Clipboard
   - Pegar JSON y Deploy

3. **Configurar nodos**:
   - Serial: Ajustar puerto COM
   - TCP: Configurar IP de impresora Zebra

### Nodos Requeridos

Instalar dependencias en Node-RED:
```bash
# En el administrador de paletas de Node-RED
node-red-node-serialport
node-red-node-tcp
```

### Función de Parsing

El nodo función parsea mensajes Mettler Toledo:

```javascript
// Formato esperado: STX + WT,peso,unidad,estado,target,producto,timestamp + ETX
var input = msg.payload.toString();
var startIdx = input.indexOf('\x02');
var endIdx = input.indexOf('\x03');

if (startIdx >= 0 && endIdx > startIdx) {
    var data = input.substring(startIdx + 1, endIdx);
    var parts = data.split(',');
    
    if (parts.length >= 7 && parts[0] === 'WT') {
        msg.mettler_data = {
            weight: parseFloat(parts[1]),
            unit: parts[2], 
            status: parts[3],
            target: parts[4],
            product: parts[5],
            timestamp: parts[6]
        };
        return msg;
    }
}
return null;
```

### Generación ZPL

El nodo ZPL genera etiquetas estándar:

```javascript
var data = msg.mettler_data;
var zpl = `^XA
^LH0,0
^FO50,50^A0N,50,50^FDPeso:^FS
^FO200,50^A0N,60,60^FD${data.weight} ${data.unit}^FS
^FO50,120^A0N,30,30^FDProducto: ${data.product}^FS
^FO50,160^A0N,25,25^FDFecha: ${data.timestamp.split('T')[0]}^FS`;

// Estado visual
switch(data.status) {
    case 'S': zpl += '^FO300,120^A0N,40,40^FDOK^FS\\n'; break;
    case 'U': zpl += '^FO300,120^A0N,30,30^FDBAJO^FS\\n'; break;
    case 'O': zpl += '^FO300,120^A0N,30,30^FDEXCESO^FS\\n'; break;
}

zpl += `^FO50,220^BY2,3,50^BCN,50,Y,N,N^FD${data.product}^FS
^XZ`;

msg.payload = zpl;
return msg;
```

## 🧪 Testing

### Datos de Prueba

El flujo incluye un nodo inject con datos de prueba:

```
\x02WT,01250.5,g,S,T,PROD001,2024-08-25T10:30:15\x0341\r\n
```

### Monitoreo

- **Debug Node**: Muestra ZPL generado
- **Serial Monitor**: Datos raw del Mettler
- **TCP Status**: Estado de conexión Zebra

## 🔧 Configuración Avanzada

### Múltiples Plantillas ZPL

Modificar función ZPL para diferentes tipos:

```javascript
// Seleccionar plantilla por producto
var template = 'standard';
if (data.product.startsWith('SPEC')) template = 'detailed';
if (data.weight < 100) template = 'compact';

switch(template) {
    case 'standard':
        // Template estándar
        break;
    case 'detailed': 
        // Template con más información
        break;
    case 'compact':
        // Template reducido
        break;
}
```

### Filtros de Estado

Agregar nodo switch para filtrar por estado:

```javascript
// Solo imprimir si está dentro de rango
if (msg.mettler_data.status === 'S' || msg.mettler_data.status === 'T') {
    return msg;
}
return null;
```

### Cola de Impresión

Usar nodo delay para manejar cola:

```javascript
// En las propiedades del nodo delay:
// Action: Rate Limit
// Rate: 1 msg per 2 seconds
// Drop intermediate messages: false
```

## 📊 Ventajas Node-RED vs Python

### Node-RED Ventajas ✅
- **Interfaz visual**: Flujo fácil de entender
- **Deploy rápido**: Cambios sin reiniciar
- **Dashboard integrado**: UI web nativa
- **Menor código**: Lógica en nodos visuales

### Python Ventajas ✅  
- **Control completo**: Lógica de programación completa
- **Librerías**: Ecosistema más amplio
- **Testing**: Frameworks de prueba robustos
- **Escalabilidad**: Mejor para sistemas grandes

## 🚀 Siguientes Pasos

1. **Dashboard Node-RED**: Crear interfaz web de monitoreo
2. **Base de datos**: Almacenar registros de pesaje
3. **Alertas**: Notificaciones por email/SMS
4. **Reportes**: Generar estadísticas automáticas

---

💡 **Tip**: Node-RED es ideal para prototipos rápidos y sistemas de integración visual, mientras Python es mejor para lógica compleja y aplicaciones empresariales.