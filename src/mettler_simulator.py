#!/usr/bin/env python3
"""
Simulador de Chequeador de Pesos Mettler Toledo
Simula el comportamiento de una balanza tipo conveyor Mettler Toledo
"""

import serial
import time
import random
import threading
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MettlerToledoSimulator:
    """
    Simulador de balanza Mettler Toledo que envía datos de peso
    en el formato estándar de la marca
    """
    
    def __init__(self, port: str = 'COM1', baudrate: int = 9600, config_file: str = None):
        self.port = port
        self.baudrate = baudrate
        self.serial_connection = None
        self.is_running = False
        self.config = self._load_config(config_file)
        
        # Parámetros de simulación
        self.min_weight = self.config.get('min_weight', 0.0)
        self.max_weight = self.config.get('max_weight', 10000.0)
        self.weight_interval = self.config.get('weight_interval', 2.0)  # segundos
        self.weight_tolerance = self.config.get('tolerance', 50.0)
        
        # Estados de la balanza
        self.current_weight = 0.0
        self.is_stable = True
        self.in_tolerance = True
        
    def _load_config(self, config_file: str) -> Dict[str, Any]:
        """Carga configuración desde archivo JSON"""
        if config_file:
            try:
                with open(config_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"No se pudo cargar configuración: {e}")
        
        # Configuración por defecto
        return {
            "min_weight": 0.0,
            "max_weight": 10000.0,
            "weight_interval": 2.0,
            "tolerance": 50.0,
            "target_weight": 1000.0,
            "product_codes": ["PROD001", "PROD002", "PROD003"]
        }
    
    def connect(self) -> bool:
        """Establece conexión serial"""
        try:
            self.serial_connection = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=1
            )
            logger.info(f"Conectado a {self.port} a {self.baudrate} baudios")
            return True
        except Exception as e:
            logger.error(f"Error conectando al puerto {self.port}: {e}")
            return False
    
    def disconnect(self):
        """Cierra conexión serial"""
        if self.serial_connection and self.serial_connection.is_open:
            self.serial_connection.close()
            logger.info("Conexión serial cerrada")
    
    def _generate_weight_data(self) -> Dict[str, Any]:
        """Genera datos simulados de peso"""
        target_weight = self.config.get('target_weight', 1000.0)
        
        # Simular variación natural del peso
        variation = random.uniform(-100, 100)
        self.current_weight = target_weight + variation
        
        # Determinar si está en tolerancia
        self.in_tolerance = abs(variation) <= self.weight_tolerance
        
        # Simular estabilidad (95% del tiempo estable)
        self.is_stable = random.random() > 0.05
        
        return {
            'weight': self.current_weight,
            'unit': 'g',
            'stable': self.is_stable,
            'in_tolerance': self.in_tolerance,
            'timestamp': datetime.now().isoformat(),
            'product_code': random.choice(self.config.get('product_codes', ['PROD001']))
        }
    
    def _format_mettler_message(self, data: Dict[str, Any]) -> str:
        """
        Formatea mensaje en protocolo Mettler Toledo
        Formato típico: STX + Datos + ETX + Checksum
        """
        # Caracteres de control
        STX = '\x02'  # Start of Text
        ETX = '\x03'  # End of Text
        
        # Formatear peso con precisión
        weight_str = f"{data['weight']:08.1f}"
        
        # Status flags
        stable_flag = 'S' if data['stable'] else 'U'  # Stable/Unstable
        tolerance_flag = 'T' if data['in_tolerance'] else 'O'  # Tolerance/Out
        
        # Construir mensaje
        message_body = (
            f"WT,{weight_str},{data['unit']},"
            f"{stable_flag},{tolerance_flag},"
            f"{data['product_code']},"
            f"{data['timestamp']}"
        )
        
        # Calcular checksum simple (suma de bytes mod 256)
        checksum = sum(ord(c) for c in message_body) % 256
        
        # Mensaje completo
        full_message = f"{STX}{message_body}{ETX}{checksum:02X}\r\n"
        
        return full_message
    
    def send_weight_data(self):
        """Envía datos de peso por puerto serial"""
        if not self.serial_connection or not self.serial_connection.is_open:
            logger.error("Conexión serial no disponible")
            return
        
        data = self._generate_weight_data()
        message = self._format_mettler_message(data)
        
        try:
            self.serial_connection.write(message.encode('ascii'))
            logger.info(f"Enviado: Peso={data['weight']:.1f}g, "
                       f"Estable={data['stable']}, "
                       f"En tolerancia={data['in_tolerance']}")
        except Exception as e:
            logger.error(f"Error enviando datos: {e}")
    
    def start_simulation(self):
        """Inicia simulación continua"""
        if self.is_running:
            logger.warning("La simulación ya está en funcionamiento")
            return
        
        if not self.connect():
            return
        
        self.is_running = True
        
        def simulation_loop():
            while self.is_running:
                self.send_weight_data()
                time.sleep(self.weight_interval)
        
        self.simulation_thread = threading.Thread(target=simulation_loop)
        self.simulation_thread.start()
        logger.info("Simulación iniciada")
    
    def stop_simulation(self):
        """Detiene simulación"""
        self.is_running = False
        if hasattr(self, 'simulation_thread'):
            self.simulation_thread.join()
        self.disconnect()
        logger.info("Simulación detenida")
    
    def get_status(self) -> Dict[str, Any]:
        """Retorna estado actual del simulador"""
        return {
            'running': self.is_running,
            'connected': self.serial_connection.is_open if self.serial_connection else False,
            'current_weight': self.current_weight,
            'stable': self.is_stable,
            'in_tolerance': self.in_tolerance,
            'port': self.port,
            'baudrate': self.baudrate
        }

# Modo sin conexión serial (para pruebas)
class MettlerToledoSimulatorNoSerial(MettlerToledoSimulator):
    """Versión del simulador que no usa puerto serial real"""
    
    def connect(self) -> bool:
        logger.info("Simulador iniciado en modo sin conexión serial")
        return True
    
    def disconnect(self):
        logger.info("Simulador desconectado (modo sin serial)")
    
    def send_weight_data(self):
        data = self._generate_weight_data()
        message = self._format_mettler_message(data)
        
        # En lugar de enviar por serial, imprimir en consola
        print(f"📊 METTLER DATA: {message.strip()}")
        logger.info(f"Peso simulado: {data['weight']:.1f}g, "
                   f"Estable: {data['stable']}, "
                   f"En tolerancia: {data['in_tolerance']}")

def main():
    """Función principal para pruebas"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Simulador Mettler Toledo')
    parser.add_argument('--port', default='COM1', help='Puerto serial')
    parser.add_argument('--baudrate', type=int, default=9600, help='Velocidad baudios')
    parser.add_argument('--config', help='Archivo de configuración JSON')
    parser.add_argument('--no-serial', action='store_true', help='Modo sin puerto serial')
    
    args = parser.parse_args()
    
    # Crear simulador
    if args.no_serial:
        simulator = MettlerToledoSimulatorNoSerial(
            port=args.port, 
            baudrate=args.baudrate, 
            config_file=args.config
        )
    else:
        simulator = MettlerToledoSimulator(
            port=args.port, 
            baudrate=args.baudrate, 
            config_file=args.config
        )
    
    try:
        simulator.start_simulation()
        print("Simulador ejecutándose. Presiona Ctrl+C para detener...")
        
        # Mantener vivo hasta Ctrl+C
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nDeteniendo simulador...")
        simulator.stop_simulation()

if __name__ == "__main__":
    main()
