#!/usr/bin/env python3
"""
Simulador de Impresora Zebra
Simula el comportamiento de una impresora Zebra que recibe comandos ZPL
"""

import socket
import threading
import time
import logging
import json
import re
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from io import StringIO

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class PrintJob:
    """Estructura para trabajos de impresión"""
    job_id: str
    zpl_code: str
    timestamp: str
    status: str = "pending"  # pending, printing, completed, error
    copies: int = 1

class ZebraSimulator:
    """
    Simulador de impresora Zebra que procesa comandos ZPL
    """
    
    def __init__(self, ip: str = "127.0.0.1", port: int = 9100, config_file: str = None):
        self.ip = ip
        self.port = port
        self.config = self._load_config(config_file)
        
        # Estado de la impresora
        self.is_running = False
        self.is_online = True
        self.paper_status = "loaded"  # loaded, empty, jam
        self.ribbon_status = "ok"     # ok, low, empty
        self.temperature = 25         # grados Celsius
        
        # Cola de impresión
        self.print_queue: List[PrintJob] = []
        self.job_counter = 0
        
        # Socket servidor
        self.server_socket = None
        self.client_threads = []
        
        # Estadísticas
        self.total_jobs = 0
        self.successful_jobs = 0
        self.failed_jobs = 0
    
    def _load_config(self, config_file: str) -> Dict[str, Any]:
        """Carga configuración desde archivo JSON"""
        if config_file:
            try:
                with open(config_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"No se pudo cargar configuración: {e}")
        
        return {
            "printer_model": "ZT230",
            "dpi": 203,
            "max_width": 4.0,  # pulgadas
            "max_height": 6.0, # pulgadas
            "print_speed": 4,  # pulgadas por segundo
            "darkness": 10,    # 0-30
            "simulation_delay": 2.0,  # segundos por etiqueta
            "enable_status_response": True,
            "auto_print": True
        }
    
    def start_server(self) -> bool:
        """Inicia servidor TCP para recibir comandos ZPL"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.ip, self.port))
            self.server_socket.listen(5)
            
            self.is_running = True
            
            # Hilo para aceptar conexiones
            accept_thread = threading.Thread(target=self._accept_connections)
            accept_thread.daemon = True
            accept_thread.start()
            
            # Hilo para procesar cola de impresión
            print_thread = threading.Thread(target=self._process_print_queue)
            print_thread.daemon = True
            print_thread.start()
            
            logger.info(f"🖨️  Simulador Zebra iniciado en {self.ip}:{self.port}")
            logger.info(f"📋 Modelo: {self.config['printer_model']}")
            return True
            
        except Exception as e:
            logger.error(f"Error iniciando servidor: {e}")
            return False
    
    def stop_server(self):
        """Detiene el servidor"""
        self.is_running = False
        
        if self.server_socket:
            self.server_socket.close()
        
        # Cerrar conexiones de clientes
        for thread in self.client_threads:
            thread.join(timeout=1)
        
        logger.info("🛑 Simulador Zebra detenido")
    
    def _accept_connections(self):
        """Acepta conexiones TCP entrantes"""
        while self.is_running:
            try:
                client_socket, address = self.server_socket.accept()
                logger.info(f"📡 Nueva conexión desde {address}")
                
                # Crear hilo para manejar cliente
                client_thread = threading.Thread(
                    target=self._handle_client,
                    args=(client_socket, address)
                )
                client_thread.daemon = True
                client_thread.start()
                
                self.client_threads.append(client_thread)
                
            except Exception as e:
                if self.is_running:
                    logger.error(f"Error aceptando conexión: {e}")
    
    def _handle_client(self, client_socket: socket.socket, address):
        """Maneja comunicación con un cliente"""
        try:
            buffer = ""
            
            while self.is_running:
                data = client_socket.recv(1024)
                if not data:
                    break
                
                # Decodificar datos
                received = data.decode('utf-8', errors='ignore')
                buffer += received
                
                # Procesar comandos ZPL completos
                while '^XA' in buffer and '^XZ' in buffer:
                    start = buffer.find('^XA')
                    end = buffer.find('^XZ', start) + 3
                    
                    if end > start:
                        zpl_command = buffer[start:end]
                        buffer = buffer[end:]
                        
                        # Procesar comando ZPL
                        self._process_zpl_command(zpl_command, client_socket)
                
                # Procesar otros comandos (status, configuración, etc.)
                lines = buffer.split('\n')
                for line in lines[:-1]:  # Procesar todas las líneas completas
                    if line.strip():
                        self._process_other_command(line.strip(), client_socket)
                
                buffer = lines[-1]  # Mantener línea incompleta
                
        except Exception as e:
            logger.error(f"Error manejando cliente {address}: {e}")
        finally:
            client_socket.close()
            logger.info(f"🔌 Conexión cerrada con {address}")
    
    def _process_zpl_command(self, zpl_code: str, client_socket: socket.socket):
        """Procesa comando ZPL para impresión"""
        logger.info(f"📄 ZPL recibido ({len(zpl_code)} caracteres)")
        
        # Crear trabajo de impresión
        self.job_counter += 1
        job = PrintJob(
            job_id=f"JOB{self.job_counter:06d}",
            zpl_code=zpl_code,
            timestamp=datetime.now().isoformat(),
            copies=self._extract_copies_from_zpl(zpl_code)
        )
        
        # Agregar a cola
        self.print_queue.append(job)
        self.total_jobs += 1
        
        logger.info(f"🆔 Trabajo {job.job_id} agregado a la cola")
        
        # Enviar respuesta si está habilitada
        if self.config.get("enable_status_response", True):
            response = f"JOB {job.job_id} QUEUED\n"
            try:
                client_socket.send(response.encode('utf-8'))
            except:
                pass
    
    def _process_other_command(self, command: str, client_socket: socket.socket):
        """Procesa otros comandos (status, configuración)"""
        command_upper = command.upper()
        
        if command_upper.startswith('~HS'):
            # Host Status Request
            self._send_status_response(client_socket)
        elif command_upper.startswith('^XQ'):
            # Cancel all jobs
            self.print_queue.clear()
            logger.info("🗑️  Cola de impresión vaciada")
        elif command_upper.startswith('~JQ'):
            # Job Queue Status
            self._send_queue_status(client_socket)
        else:
            logger.debug(f"Comando no reconocido: {command}")
    
    def _send_status_response(self, client_socket: socket.socket):
        """Envía estado de la impresora"""
        status = {
            "printer_status": "online" if self.is_online else "offline",
            "paper_status": self.paper_status,
            "ribbon_status": self.ribbon_status,
            "temperature": self.temperature,
            "queue_length": len(self.print_queue),
            "total_jobs": self.total_jobs,
            "successful_jobs": self.successful_jobs,
            "failed_jobs": self.failed_jobs
        }
        
        response = f"STATUS: {json.dumps(status)}\n"
        try:
            client_socket.send(response.encode('utf-8'))
        except:
            pass
    
    def _send_queue_status(self, client_socket: socket.socket):
        """Envía estado de la cola"""
        queue_info = []
        for job in self.print_queue:
            queue_info.append({
                "job_id": job.job_id,
                "status": job.status,
                "timestamp": job.timestamp,
                "copies": job.copies
            })
        
        response = f"QUEUE: {json.dumps(queue_info)}\n"
        try:
            client_socket.send(response.encode('utf-8'))
        except:
            pass
    
    def _extract_copies_from_zpl(self, zpl_code: str) -> int:
        """Extrae número de copias del código ZPL"""
        # Buscar comando ^PQ (Print Quantity)
        match = re.search(r'\^PQ(\d+)', zpl_code)
        if match:
            return int(match.group(1))
        return 1
    
    def _process_print_queue(self):
        """Procesa la cola de impresión"""
        while self.is_running:
            if self.print_queue and self.is_online:
                job = self.print_queue.pop(0)
                self._simulate_printing(job)
            else:
                time.sleep(0.1)
    
    def _simulate_printing(self, job: PrintJob):
        """Simula el proceso de impresión"""
        logger.info(f"🖨️  Iniciando impresión {job.job_id}")
        job.status = "printing"
        
        # Simular tiempo de impresión
        print_time = self.config.get("simulation_delay", 2.0)
        
        try:
            # Analizar ZPL para obtener información
            zpl_info = self._analyze_zpl(job.zpl_code)
            
            # Mostrar contenido de la etiqueta
            print("\n" + "="*60)
            print(f"🏷️  IMPRIMIENDO ETIQUETA - {job.job_id}")
            print("="*60)
            
            if zpl_info:
                for key, value in zpl_info.items():
                    print(f"{key}: {value}")
            
            print(f"📋 Copias: {job.copies}")
            print(f"⏱️  Tiempo estimado: {print_time:.1f}s")
            print("="*60)
            
            # Simular progreso de impresión
            for i in range(int(print_time * 10)):
                if not self.is_running:
                    break
                time.sleep(0.1)
                if i % 10 == 0:  # Cada segundo
                    progress = (i / (print_time * 10)) * 100
                    print(f"📊 Progreso: {progress:.0f}%")
            
            # Marcar como completado
            job.status = "completed"
            self.successful_jobs += 1
            
            print(f"✅ Impresión {job.job_id} completada")
            print("\n")
            
        except Exception as e:
            job.status = "error"
            self.failed_jobs += 1
            logger.error(f"❌ Error imprimiendo {job.job_id}: {e}")
    
    def _analyze_zpl(self, zpl_code: str) -> Dict[str, str]:
        """Analiza código ZPL para extraer información"""
        info = {}
        
        # Buscar campos de texto (^FD...^FS)
        text_fields = re.findall(r'\^FD([^\^]+)\^FS', zpl_code)
        
        # Intentar identificar campos comunes
        for i, text in enumerate(text_fields):
            if 'producto' in text.lower() or 'product' in text.lower():
                info['Producto'] = text
            elif 'peso' in text.lower() or 'weight' in text.lower():
                info['Peso'] = text
            elif 'fecha' in text.lower() or 'date' in text.lower():
                info['Fecha'] = text
            elif 'estado' in text.lower() or 'status' in text.lower():
                info['Estado'] = text
            elif 'lote' in text.lower() or 'batch' in text.lower():
                info['Lote'] = text
            else:
                info[f'Campo {i+1}'] = text
        
        # Buscar códigos de barras (^BC, ^B3, etc.)
        barcode_match = re.search(r'\^B[C3]\^FD([^\^]+)\^FS', zpl_code)
        if barcode_match:
            info['Código de Barras'] = barcode_match.group(1)
        
        return info
    
    def get_status(self) -> Dict[str, Any]:
        """Retorna estado completo del simulador"""
        return {
            "running": self.is_running,
            "online": self.is_online,
            "ip": self.ip,
            "port": self.port,
            "paper_status": self.paper_status,
            "ribbon_status": self.ribbon_status,
            "temperature": self.temperature,
            "queue_length": len(self.print_queue),
            "total_jobs": self.total_jobs,
            "successful_jobs": self.successful_jobs,
            "failed_jobs": self.failed_jobs,
            "config": self.config
        }
    
    def set_printer_status(self, online: bool = None, paper: str = None, ribbon: str = None):
        """Cambia estado de la impresora para simular problemas"""
        if online is not None:
            self.is_online = online
            logger.info(f"🔧 Impresora {'online' if online else 'offline'}")
        
        if paper is not None:
            self.paper_status = paper
            logger.info(f"📄 Estado papel: {paper}")
        
        if ribbon is not None:
            self.ribbon_status = ribbon
            logger.info(f"🖤 Estado ribbon: {ribbon}")

def main():
    """Función principal para pruebas"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Simulador Impresora Zebra')
    parser.add_argument('--ip', default='127.0.0.1', help='Dirección IP')
    parser.add_argument('--port', type=int, default=9100, help='Puerto TCP')
    parser.add_argument('--config', help='Archivo de configuración JSON')
    
    args = parser.parse_args()
    
    # Crear simulador
    simulator = ZebraSimulator(ip=args.ip, port=args.port, config_file=args.config)
    
    try:
        if simulator.start_server():
            print(f"🖨️  Simulador Zebra ejecutándose en {args.ip}:{args.port}")
            print("📋 Comandos disponibles:")
            print("  - status: Mostrar estado")
            print("  - offline/online: Cambiar estado")
            print("  - paper [loaded/empty/jam]: Cambiar estado papel")
            print("  - ribbon [ok/low/empty]: Cambiar estado ribbon")
            print("  - queue: Mostrar cola")
            print("  - clear: Limpiar cola")
            print("  - quit: Salir")
            print()
            
            # Interfaz de comandos simple
            while True:
                try:
                    cmd = input("Zebra> ").strip().lower()
                    
                    if cmd == "quit":
                        break
                    elif cmd == "status":
                        status = simulator.get_status()
                        print(json.dumps(status, indent=2))
                    elif cmd == "offline":
                        simulator.set_printer_status(online=False)
                    elif cmd == "online":
                        simulator.set_printer_status(online=True)
                    elif cmd.startswith("paper "):
                        paper_status = cmd.split()[1]
                        simulator.set_printer_status(paper=paper_status)
                    elif cmd.startswith("ribbon "):
                        ribbon_status = cmd.split()[1]
                        simulator.set_printer_status(ribbon=ribbon_status)
                    elif cmd == "queue":
                        print(f"Cola: {len(simulator.print_queue)} trabajos pendientes")
                        for job in simulator.print_queue:
                            print(f"  {job.job_id}: {job.status}")
                    elif cmd == "clear":
                        simulator.print_queue.clear()
                        print("Cola limpiada")
                    elif cmd == "":
                        continue
                    else:
                        print("Comando no reconocido")
                        
                except KeyboardInterrupt:
                    break
                except EOFError:
                    break
        
    finally:
        simulator.stop_server()

if __name__ == "__main__":
    main()
