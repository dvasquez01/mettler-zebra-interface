#!/usr/bin/env python3
"""
Ejemplo de uso básico del sistema Mettler-Zebra
"""

import sys
import os
import time

# Agregar directorio src al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from mettler_simulator import MettlerToledoSimulatorNoSerial
from protocol_converter import ProtocolConverter
from zebra_simulator import ZebraSimulator
import threading

def ejemplo_basico():
    """Ejemplo básico de uso"""
    print("🚀 Iniciando ejemplo básico Mettler-Zebra")
    
    # 1. Crear componentes
    mettler = MettlerToledoSimulatorNoSerial()
    converter = ProtocolConverter()
    zebra = ZebraSimulator()
    
    # 2. Iniciar simulador Zebra
    print("🖨️  Iniciando simulador Zebra...")
    if not zebra.start_server():
        print("❌ Error iniciando Zebra")
        return
    
    # 3. Generar algunos datos de prueba
    print("📊 Generando datos de prueba...")
    
    mensajes_prueba = [
        "\x02WT,01250.5,g,S,T,PROD001,2024-08-25T10:30:15\x0341\r\n",
        "\x02WT,00950.2,g,S,O,PROD002,2024-08-25T10:31:20\x0342\r\n", 
        "\x02WT,01100.8,g,U,T,PROD003,2024-08-25T10:32:25\x0343\r\n"
    ]
    
    # 4. Procesar mensajes
    for i, mensaje in enumerate(mensajes_prueba, 1):
        print(f"\n--- Procesando mensaje {i} ---")
        print(f"📨 Mettler: {mensaje.strip()}")
        
        # Convertir a ZPL
        zpl = converter.convert_message(mensaje, template="standard")
        
        if zpl:
            print("✅ ZPL generado:")
            print(zpl[:100] + "..." if len(zpl) > 100 else zpl)
            
            # Enviar a Zebra
            import socket
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect(("127.0.0.1", 9100))
                sock.send(zpl.encode('utf-8'))
                sock.close()
                print("📤 Enviado a impresora Zebra")
            except Exception as e:
                print(f"❌ Error enviando: {e}")
        else:
            print("⚠️  No se generó ZPL")
        
        time.sleep(2)
    
    # 5. Mostrar estadísticas
    print(f"\n📊 Estado Zebra:")
    status = zebra.get_status()
    print(f"  - Trabajos totales: {status['total_jobs']}")
    print(f"  - Exitosos: {status['successful_jobs']}")
    print(f"  - Fallidos: {status['failed_jobs']}")
    
    # 6. Limpiar
    print("\n🧹 Limpiando...")
    zebra.stop_server()
    print("✅ Ejemplo completado")

def ejemplo_continuo():
    """Ejemplo con simulación continua"""
    print("🔄 Iniciando ejemplo continuo (Ctrl+C para detener)")
    
    # Componentes
    mettler = MettlerToledoSimulatorNoSerial()
    converter = ProtocolConverter()
    zebra = ZebraSimulator()
    
    # Configurar Mettler para generar datos más frecuentemente
    mettler.weight_interval = 5.0  # cada 5 segundos
    
    # Iniciar Zebra
    if not zebra.start_server():
        print("❌ Error iniciando Zebra")
        return
    
    # Función para procesar mensajes Mettler
    def procesar_mensaje_mettler():
        # Generar dato
        data = mettler._generate_weight_data()
        mensaje = mettler._format_mettler_message(data)
        
        print(f"📊 Peso: {data['weight']:.1f}g - {data['product_code']}")
        
        # Convertir
        zpl = converter.convert_message(mensaje)
        if zpl:
            # Enviar a Zebra
            import socket
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect(("127.0.0.1", 9100))
                sock.send(zpl.encode('utf-8'))
                sock.close()
                print("✅ Etiqueta enviada")
            except Exception as e:
                print(f"❌ Error: {e}")
    
    # Sobrescribir método de Mettler
    mettler.send_weight_data = procesar_mensaje_mettler
    
    try:
        # Iniciar simulación
        mettler.start_simulation()
        
        # Mantener vivo
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n🛑 Deteniendo...")
        mettler.stop_simulation()
        zebra.stop_server()
        print("✅ Detenido")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Ejemplos Mettler-Zebra')
    parser.add_argument('--continuo', action='store_true', help='Ejecutar ejemplo continuo')
    
    args = parser.parse_args()
    
    if args.continuo:
        ejemplo_continuo()
    else:
        ejemplo_basico()
