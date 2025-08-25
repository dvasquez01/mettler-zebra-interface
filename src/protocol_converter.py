#!/usr/bin/env python3
"""
Convertidor de Protocolo Mettler Toledo a Zebra ZPL
Convierte los datos del chequeador de pesos al formato ZPL para impresión
"""

import re
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class WeightData:
    """Estructura de datos de peso procesados"""
    weight: float
    unit: str
    stable: bool
    in_tolerance: bool
    product_code: str
    timestamp: str
    original_message: str

@dataclass
class LabelData:
    """Estructura de datos para la etiqueta"""
    weight: float
    unit: str
    product_code: str
    timestamp: str
    status: str
    batch_number: str = ""
    line_number: str = "LINE01"

class ProtocolConverter:
    """
    Convertidor de protocolo Mettler Toledo a Zebra ZPL
    """
    
    def __init__(self, config_file: str = None):
        self.config = self._load_config(config_file)
        self.label_templates = self._load_label_templates()
        
        # Expresión regular para parsear mensajes Mettler Toledo
        self.mettler_pattern = re.compile(
            r'\x02WT,([0-9.+-]+),(\w+),([SU]),([TO]),([^,]+),([^,]+)\x03([0-9A-F]{2})'
        )
    
    def _load_config(self, config_file: str) -> Dict[str, Any]:
        """Carga configuración desde archivo JSON"""
        if config_file:
            try:
                with open(config_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"No se pudo cargar configuración: {e}")
        
        return {
            "weight_threshold": 50.0,
            "print_on_out_of_tolerance": True,
            "print_on_stable_only": False,
            "label_width": 4,  # pulgadas
            "label_height": 3,  # pulgadas
            "dpi": 203  # dots per inch
        }
    
    def _load_label_templates(self) -> Dict[str, str]:
        """Carga plantillas de etiquetas ZPL"""
        return {
            "standard": """
^XA
^CF0,30
^FO50,50^FDProducto: {product_code}^FS
^CF0,25
^FO50,100^FDPeso: {weight} {unit}^FS
^FO50,140^FDEstado: {status}^FS
^FO50,180^FDFecha: {timestamp}^FS
^FO50,220^FDLínea: {line_number}^FS
^BY2,3,50
^FO50,260^BC^FD{product_code}-{batch_number}^FS
^XZ
""",
            "simple": """
^XA
^CF0,40
^FO30,30^FD{weight} {unit}^FS
^CF0,20
^FO30,80^FD{product_code}^FS
^FO30,110^FD{timestamp}^FS
^XZ
""",
            "detailed": """
^XA
^CF0,25
^FO20,20^FDMettler Toledo Check Weigher^FS
^FO20,50^GB760,2,2^FS
^CF0,30
^FO30,70^FDProducto: {product_code}^FS
^CF0,50
^FO30,120^FDPeso: {weight} {unit}^FS
^CF0,25
^FO30,180^FDEstado: {status}^FS
^FO30,210^FDTolerancia: {'OK' if status == 'APROBADO' else 'FUERA'}^FS
^FO30,240^FDFecha: {timestamp}^FS
^FO30,270^FDLínea: {line_number}^FS
^FO30,300^FDLote: {batch_number}^FS
^BY3,3,80
^FO30,340^BC^FD{product_code}-{batch_number}^FS
^XZ
"""
        }
    
    def parse_mettler_message(self, message: str) -> Optional[WeightData]:
        """
        Parsea mensaje de Mettler Toledo y extrae datos de peso
        
        Formato esperado: STX + WT,peso,unidad,estable,tolerancia,código,timestamp + ETX + checksum
        """
        try:
            # Limpiar mensaje
            clean_message = message.strip()
            
            # Buscar patrón
            match = self.mettler_pattern.search(clean_message)
            if not match:
                logger.warning(f"Mensaje no reconocido: {clean_message}")
                return None
            
            weight_str, unit, stable_flag, tolerance_flag, product_code, timestamp, checksum = match.groups()
            
            # Validar checksum (opcional)
            # TODO: Implementar validación de checksum si es necesario
            
            # Convertir datos
            weight = float(weight_str)
            stable = stable_flag == 'S'
            in_tolerance = tolerance_flag == 'T'
            
            return WeightData(
                weight=weight,
                unit=unit,
                stable=stable,
                in_tolerance=in_tolerance,
                product_code=product_code,
                timestamp=timestamp,
                original_message=clean_message
            )
            
        except Exception as e:
            logger.error(f"Error parseando mensaje Mettler: {e}")
            return None
    
    def should_print_label(self, weight_data: WeightData) -> bool:
        """
        Determina si se debe imprimir etiqueta basado en configuración
        """
        # Verificar si solo imprimir cuando está estable
        if self.config.get("print_on_stable_only", False) and not weight_data.stable:
            return False
        
        # Verificar si imprimir cuando está fuera de tolerancia
        if self.config.get("print_on_out_of_tolerance", True) and not weight_data.in_tolerance:
            return True
        
        # Verificar umbral de peso
        weight_threshold = self.config.get("weight_threshold", 0.0)
        if weight_data.weight < weight_threshold:
            return False
        
        return True
    
    def create_label_data(self, weight_data: WeightData) -> LabelData:
        """
        Convierte datos de peso a estructura de etiqueta
        """
        # Determinar estado
        if weight_data.in_tolerance and weight_data.stable:
            status = "APROBADO"
        elif not weight_data.in_tolerance:
            status = "RECHAZADO"
        else:
            status = "INESTABLE"
        
        # Generar número de lote (ejemplo)
        batch_number = f"B{datetime.now().strftime('%Y%m%d%H%M')}"
        
        # Formatear timestamp
        try:
            dt = datetime.fromisoformat(weight_data.timestamp.replace('Z', '+00:00'))
            formatted_time = dt.strftime('%d/%m/%Y %H:%M:%S')
        except:
            formatted_time = weight_data.timestamp
        
        return LabelData(
            weight=weight_data.weight,
            unit=weight_data.unit,
            product_code=weight_data.product_code,
            timestamp=formatted_time,
            status=status,
            batch_number=batch_number,
            line_number=self.config.get("line_number", "LINE01")
        )
    
    def generate_zpl(self, label_data: LabelData, template: str = "standard") -> str:
        """
        Genera código ZPL para la etiqueta
        """
        if template not in self.label_templates:
            logger.warning(f"Plantilla '{template}' no encontrada, usando 'standard'")
            template = "standard"
        
        zpl_template = self.label_templates[template]
        
        try:
            zpl_code = zpl_template.format(
                weight=f"{label_data.weight:.1f}",
                unit=label_data.unit,
                product_code=label_data.product_code,
                timestamp=label_data.timestamp,
                status=label_data.status,
                batch_number=label_data.batch_number,
                line_number=label_data.line_number
            )
            
            return zpl_code.strip()
            
        except Exception as e:
            logger.error(f"Error generando ZPL: {e}")
            return ""
    
    def convert_message(self, mettler_message: str, template: str = "standard") -> Optional[str]:
        """
        Función principal: convierte mensaje Mettler Toledo a ZPL
        """
        # Parsear mensaje Mettler
        weight_data = self.parse_mettler_message(mettler_message)
        if not weight_data:
            return None
        
        # Verificar si debe imprimir
        if not self.should_print_label(weight_data):
            logger.info(f"No se imprime etiqueta para peso {weight_data.weight:.1f} {weight_data.unit}")
            return None
        
        # Crear datos de etiqueta
        label_data = self.create_label_data(weight_data)
        
        # Generar ZPL
        zpl_code = self.generate_zpl(label_data, template)
        
        if zpl_code:
            logger.info(f"ZPL generado para {weight_data.product_code}: "
                       f"{weight_data.weight:.1f} {weight_data.unit} - {label_data.status}")
        
        return zpl_code
    
    def get_available_templates(self) -> List[str]:
        """Retorna lista de plantillas disponibles"""
        return list(self.label_templates.keys())
    
    def add_custom_template(self, name: str, zpl_template: str):
        """Añade plantilla personalizada"""
        self.label_templates[name] = zpl_template
        logger.info(f"Plantilla '{name}' añadida")

# Utilidades adicionales
class BatchConverter:
    """Procesador por lotes para múltiples mensajes"""
    
    def __init__(self, converter: ProtocolConverter):
        self.converter = converter
        self.processed_count = 0
        self.error_count = 0
    
    def process_batch(self, messages: List[str], template: str = "standard") -> List[str]:
        """Procesa múltiples mensajes"""
        results = []
        
        for message in messages:
            try:
                zpl = self.converter.convert_message(message, template)
                if zpl:
                    results.append(zpl)
                    self.processed_count += 1
                else:
                    self.error_count += 1
            except Exception as e:
                logger.error(f"Error procesando mensaje: {e}")
                self.error_count += 1
        
        return results
    
    def get_stats(self) -> Dict[str, int]:
        """Retorna estadísticas de procesamiento"""
        return {
            "processed": self.processed_count,
            "errors": self.error_count,
            "total": self.processed_count + self.error_count
        }

def main():
    """Función principal para pruebas"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Convertidor Mettler Toledo a ZPL')
    parser.add_argument('--config', help='Archivo de configuración JSON')
    parser.add_argument('--template', default='standard', help='Plantilla ZPL a usar')
    parser.add_argument('--test', action='store_true', help='Ejecutar con datos de prueba')
    
    args = parser.parse_args()
    
    # Crear convertidor
    converter = ProtocolConverter(config_file=args.config)
    
    if args.test:
        # Datos de prueba
        test_messages = [
            "\x02WT,01250.5,g,S,T,PROD001,2024-08-25T10:30:15\x0341\r\n",
            "\x02WT,00950.2,g,S,O,PROD002,2024-08-25T10:31:20\x0342\r\n",
            "\x02WT,01100.8,g,U,T,PROD003,2024-08-25T10:32:25\x0343\r\n"
        ]
        
        print(f"🔄 Convertidor iniciado con plantilla '{args.template}'")
        print("📋 Plantillas disponibles:", converter.get_available_templates())
        print()
        
        for i, message in enumerate(test_messages, 1):
            print(f"📨 Mensaje {i}: {message.strip()}")
            zpl = converter.convert_message(message, args.template)
            
            if zpl:
                print(f"✅ ZPL generado:")
                print(zpl)
            else:
                print("❌ No se generó ZPL")
            print("-" * 60)
    
    else:
        print("Convertidor listo. Ingrese mensajes Mettler Toledo (Ctrl+C para salir):")
        
        try:
            while True:
                message = input("Mensaje: ")
                if message.strip():
                    zpl = converter.convert_message(message, args.template)
                    if zpl:
                        print("ZPL generado:")
                        print(zpl)
                        print()
                    else:
                        print("No se generó ZPL para este mensaje")
                        
        except KeyboardInterrupt:
            print("\nSaliendo...")

if __name__ == "__main__":
    main()
