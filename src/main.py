#!/usr/bin/env python3
"""
Aplicación principal que integra todos los componentes
Simulador Mettler Toledo -> Convertidor -> Simulador Zebra
"""

import sys
import time
import threading
import logging
import argparse
import json
from datetime import datetime
from typing import Dict, Any

# Importar componentes locales
from mettler_simulator import MettlerToledoSimulatorNoSerial, MettlerToledoSimulator
from protocol_converter import ProtocolConverter
from zebra_simulator import ZebraSimulator

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MettlerZebraInterface:
    """
    Interfaz principal que conecta la balanza Mettler Toledo con la impresora Zebra
    """
    
    def __init__(self, config_file: str = None):
        self.config = self._load_config(config_file)
        
        # Componentes
        self.mettler_simulator = None
        self.zebra_simulator = None
        self.converter = None
        
        # Estado
        self.is_running = False
        self.stats = {
            'messages_received': 0,
            'labels_printed': 0,
            'errors': 0,
            'start_time': None
        }
    
    def _load_config(self, config_file: str) -> Dict[str, Any]:
        """Carga configuración principal"""
        if config_file:
            try:
                with open(config_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"No se pudo cargar configuración: {e}")
        
        return {
            "mettler": {
                "port": "COM1",
                "baudrate": 9600,
                "simulation_mode": True,
                "weight_interval": 3.0
            },
            "zebra": {
                "ip": "127.0.0.1",
                "port": 9100,
                "simulation_mode": True
            },
            "converter": {
                "template": "standard",
                "print_on_out_of_tolerance": True,
                "print_on_stable_only": False
            },
            "logging": {
                "level": "INFO",
                "log_to_file": False,
                "log_file": "interface.log"
            }
        }
    
    def initialize_components(self):
        """Inicializa todos los componentes"""
        try:
            # Inicializar convertidor
            logger.info("🔄 Inicializando convertidor de protocolo...")
            self.converter = ProtocolConverter()
            
            # Inicializar simulador Zebra
            zebra_config = self.config['zebra']
            logger.info(f"🖨️  Inicializando simulador Zebra en {zebra_config['ip']}:{zebra_config['port']}")
            self.zebra_simulator = ZebraSimulator(
                ip=zebra_config['ip'],
                port=zebra_config['port']
            )
            
            if not self.zebra_simulator.start_server():
                raise Exception("No se pudo iniciar simulador Zebra")
            
            # Inicializar simulador Mettler Toledo
            mettler_config = self.config['mettler']
            logger.info(f"⚖️  Inicializando simulador Mettler Toledo...")
            
            if mettler_config.get('simulation_mode', True):
                self.mettler_simulator = MettlerToledoSimulatorNoSerial(
                    port=mettler_config['port'],
                    baudrate=mettler_config['baudrate']
                )
            else:
                self.mettler_simulator = MettlerToledoSimulator(
                    port=mettler_config['port'],
                    baudrate=mettler_config['baudrate']
                )
            
            # Configurar intervalo de peso
            self.mettler_simulator.weight_interval = mettler_config.get('weight_interval', 3.0)
            
            logger.info("✅ Todos los componentes inicializados correctamente")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error inicializando componentes: {e}")
            return False
    
    def start_interface(self):
        """Inicia la interfaz completa"""
        if not self.initialize_components():
            return False
        
        self.is_running = True
        self.stats['start_time'] = datetime.now()
        
        # Iniciar simulador Mettler Toledo con callback personalizado
        self._start_mettler_with_callback()
        
        logger.info("🚀 Interfaz Mettler-Zebra iniciada correctamente")
        logger.info("📊 Estadísticas disponibles con 'stats' en modo interactivo")
        
        return True
    
    def _start_mettler_with_callback(self):
        """Inicia simulador Mettler con callback personalizado para procesar mensajes"""
        
        # Sobrescribir método send_weight_data para interceptar mensajes
        original_send_weight_data = self.mettler_simulator.send_weight_data
        
        def custom_send_weight_data():
            # Generar datos como siempre
            data = self.mettler_simulator._generate_weight_data()
            message = self.mettler_simulator._format_mettler_message(data)
            
            # Procesar mensaje con nuestro convertidor
            self._process_mettler_message(message)
            
            # Mostrar mensaje original también
            print(f"📊 METTLER: {message.strip()}")
        
        # Reemplazar método
        self.mettler_simulator.send_weight_data = custom_send_weight_data
        
        # Iniciar simulación
        self.mettler_simulator.start_simulation()
    
    def _process_mettler_message(self, message: str):
        """Procesa mensaje de Mettler Toledo y lo envía a Zebra"""
        try:
            self.stats['messages_received'] += 1
            
            # Convertir mensaje a ZPL
            template = self.config['converter'].get('template', 'standard')
            zpl_code = self.converter.convert_message(message, template)
            
            if zpl_code:
                # Enviar a impresora Zebra
                self._send_to_zebra(zpl_code)
                self.stats['labels_printed'] += 1
                logger.info(f"✅ Etiqueta enviada a impresora Zebra")
            else:
                logger.debug("ℹ️  No se generó etiqueta (filtros aplicados)")
                
        except Exception as e:
            self.stats['errors'] += 1
            logger.error(f"❌ Error procesando mensaje Mettler: {e}")
    
    def _send_to_zebra(self, zpl_code: str):
        """Envía código ZPL a la impresora Zebra"""
        try:
            import socket
            
            # Crear conexión TCP con la impresora simulada
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5.0)
            
            zebra_config = self.config['zebra']
            sock.connect((zebra_config['ip'], zebra_config['port']))
            
            # Enviar ZPL
            sock.send(zpl_code.encode('utf-8'))
            
            # Leer respuesta si está disponible
            try:
                response = sock.recv(1024).decode('utf-8')
                if response:
                    logger.debug(f"Respuesta Zebra: {response.strip()}")
            except:
                pass
            
            sock.close()
            logger.debug("📤 ZPL enviado a impresora Zebra")
            
        except Exception as e:
            logger.error(f"❌ Error enviando ZPL a Zebra: {e}")
            raise
    
    def stop_interface(self):
        """Detiene la interfaz"""
        self.is_running = False
        
        if self.mettler_simulator:
            self.mettler_simulator.stop_simulation()
        
        if self.zebra_simulator:
            self.zebra_simulator.stop_server()
        
        logger.info("🛑 Interfaz detenida")
    
    def get_status(self) -> Dict[str, Any]:
        """Retorna estado completo del sistema"""
        status = {
            'interface': {
                'running': self.is_running,
                'uptime': str(datetime.now() - self.stats['start_time']) if self.stats['start_time'] else None
            },
            'stats': self.stats.copy(),
            'mettler': self.mettler_simulator.get_status() if self.mettler_simulator else None,
            'zebra': self.zebra_simulator.get_status() if self.zebra_simulator else None
        }
        
        return status
    
    def print_status(self):
        """Imprime estado en formato legible"""
        status = self.get_status()
        
        print("\n" + "="*60)
        print("📊 ESTADO DEL SISTEMA METTLER-ZEBRA")
        print("="*60)
        
        # Estado general
        interface = status['interface']
        print(f"🔄 Estado: {'🟢 Funcionando' if interface['running'] else '🔴 Detenido'}")
        if interface['uptime']:
            print(f"⏱️  Tiempo funcionando: {interface['uptime']}")
        
        # Estadísticas
        stats = status['stats']
        print(f"📨 Mensajes recibidos: {stats['messages_received']}")
        print(f"🏷️  Etiquetas impresas: {stats['labels_printed']}")
        print(f"❌ Errores: {stats['errors']}")
        
        # Estado Mettler
        if status['mettler']:
            mettler = status['mettler']
            print(f"⚖️  Mettler: {'🟢' if mettler['running'] else '🔴'} "
                  f"Peso: {mettler['current_weight']:.1f}g")
        
        # Estado Zebra
        if status['zebra']:
            zebra = status['zebra']
            print(f"🖨️  Zebra: {'🟢' if zebra['online'] else '🔴'} "
                  f"Cola: {zebra['queue_length']} trabajos")
        
        print("="*60)

def main():
    """Función principal"""
    parser = argparse.ArgumentParser(description='Interfaz Mettler Toledo - Zebra')
    parser.add_argument('--config', help='Archivo de configuración JSON')
    parser.add_argument('--interactive', action='store_true', help='Modo interactivo')
    parser.add_argument('--duration', type=int, help='Duración en segundos (0 = infinito)')
    
    args = parser.parse_args()
    
    # Crear interfaz
    interface = MettlerZebraInterface(config_file=args.config)
    
    try:
        # Iniciar interfaz
        if not interface.start_interface():
            logger.error("❌ No se pudo iniciar la interfaz")
            return 1
        
        if args.interactive:
            # Modo interactivo
            print("\n🎛️  MODO INTERACTIVO")
            print("Comandos disponibles:")
            print("  status - Mostrar estado del sistema")
            print("  stats  - Mostrar estadísticas")
            print("  quit   - Salir")
            print()
            
            while interface.is_running:
                try:
                    cmd = input("Interface> ").strip().lower()
                    
                    if cmd == "quit":
                        break
                    elif cmd == "status":
                        interface.print_status()
                    elif cmd == "stats":
                        stats = interface.get_status()['stats']
                        print(json.dumps(stats, indent=2))
                    elif cmd == "":
                        continue
                    else:
                        print("Comando no reconocido")
                        
                except KeyboardInterrupt:
                    break
                except EOFError:
                    break
        
        else:
            # Modo automático
            duration = args.duration or 0
            start_time = time.time()
            
            print(f"🤖 Modo automático iniciado")
            if duration:
                print(f"⏱️  Duración: {duration} segundos")
            else:
                print("⏱️  Duración: Indefinida (Ctrl+C para detener)")
            
            try:
                while interface.is_running:
                    time.sleep(1)
                    
                    # Verificar duración
                    if duration and (time.time() - start_time) >= duration:
                        break
                    
                    # Mostrar estado cada 30 segundos
                    if int(time.time() - start_time) % 30 == 0:
                        interface.print_status()
                        
            except KeyboardInterrupt:
                print("\n🛑 Deteniendo por solicitud del usuario...")
    
    finally:
        interface.stop_interface()
        print("👋 Interfaz Mettler-Zebra finalizada")
        
    return 0

if __name__ == "__main__":
    sys.exit(main())
