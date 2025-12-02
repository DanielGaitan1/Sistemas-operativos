import tkinter as tk
from tkinter import scrolledtext
import threading
import time
import random

# --- CONFIGURACIÓN ---
CAPACIDAD_BUFFER = 8    # Tamaño de la cinta/buffer
TIEMPO_PRODUCIR = (0.5, 1.5)
TIEMPO_CONSUMIR = (1.0, 2.0)

# Colores Profesionales
COL_VACIO = "#E0E0E0"       # Gris claro
COL_LLENO = "#00BCD4"       # Cyan (Producto)
COL_PROD_ACTIVO = "#4CAF50" # Verde
COL_CONS_ACTIVO = "#FF9800" # Naranja
COL_ESPERA = "#F44336"      # Rojo (Bloqueado)
COL_TEXTO = "#000000"

class ProductorConsumidorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Simulación: Productor - Consumidor (Buffer Acotado)")
        self.root.geometry("700x550")
        
        # Variables compartidas
        self.buffer = [None] * CAPACIDAD_BUFFER # None = Vacío
        self.mutex = threading.Lock()
        self.sem_espacios_vacios = threading.Semaphore(CAPACIDAD_BUFFER)
        self.sem_items_disponibles = threading.Semaphore(0)
        self.running = True
        
        # Índices para comportamiento FIFO (Cola Circular)
        self.idx_productor = 0
        self.idx_consumidor = 0

        # --- INTERFAZ GRÁFICA ---
        
        # 1. Panel de Estado (Actores)
        frame_actores = tk.Frame(root, pady=20)
        frame_actores.pack(fill="x")

        # Productor
        self.lbl_prod = tk.Label(frame_actores, text="PRODUCTOR\n[Generando Datos]", 
                                 bg=COL_PROD_ACTIVO, fg="white", font=("Arial", 12, "bold"), 
                                 width=20, height=3, relief="raised")
        self.lbl_prod.pack(side=tk.LEFT, padx=40)

        # Consumidor
        self.lbl_cons = tk.Label(frame_actores, text="CONSUMIDOR\n[Procesando Datos]", 
                                 bg=COL_CONS_ACTIVO, fg="white", font=("Arial", 12, "bold"), 
                                 width=20, height=3, relief="raised")
        self.lbl_cons.pack(side=tk.RIGHT, padx=40)

        # 2. El Buffer (Visualización central)
        tk.Label(root, text="BUFFER DE DATOS (Memoria Compartida)", font=("Arial", 10, "bold")).pack(pady=(10, 5))
        
        frame_buffer = tk.Frame(root, bg="#333", padx=5, pady=5) # Marco oscuro
        frame_buffer.pack()

        self.slots_gui = []
        for i in range(CAPACIDAD_BUFFER):
            # Contenedor para el slot y su índice
            f = tk.Frame(frame_buffer, bg="#333")
            f.pack(side=tk.LEFT, padx=2)
            
            lbl = tk.Label(f, text="VACÍO", bg=COL_VACIO, width=8, height=4, relief="sunken", font=("Arial", 8))
            lbl.pack()
            
            tk.Label(f, text=f"[{i}]", fg="white", bg="#333", font=("Arial", 7)).pack()
            self.slots_gui.append(lbl)

        # 3. Log
        tk.Label(root, text="Log de Operaciones:", anchor="w").pack(fill="x", padx=20, pady=(20,0))
        self.log_box = scrolledtext.ScrolledText(root, height=10, state='disabled')
        self.log_box.pack(fill="both", expand=True, padx=20, pady=10)

        # --- HILOS ---
        self.t1 = threading.Thread(target=self.proceso_productor, daemon=True)
        self.t2 = threading.Thread(target=self.proceso_consumidor, daemon=True)
        self.t1.start()
        self.t2.start()

    # --- GUI UPDATE HELPER ---
    def log(self, msg):
        self.root.after(0, lambda: self._write_log(msg))

    def _write_log(self, msg):
        self.log_box.config(state='normal')
        self.log_box.insert(tk.END, msg + "\n")
        self.log_box.see(tk.END)
        self.log_box.config(state='disabled')

    def actualizar_slot(self, index, lleno, dato=""):
        color = COL_LLENO if lleno else COL_VACIO
        texto = f"DATO\n{dato}" if lleno else "VACÍO"
        self.root.after(0, lambda: self.slots_gui[index].config(bg=color, text=texto))

    def actualizar_actor(self, actor, estado):
        # Estados: 0=Trabajando, 1=Bloqueado/Esperando
        if actor == "prod":
            bg = COL_PROD_ACTIVO if estado == 0 else COL_ESPERA
            txt = "PRODUCTOR\n[Trabajando]" if estado == 0 else "PRODUCTOR\n[ESPERANDO ESPACIO]"
            self.root.after(0, lambda: self.lbl_prod.config(bg=bg, text=txt))
        else:
            bg = COL_CONS_ACTIVO if estado == 0 else COL_ESPERA
            txt = "CONSUMIDOR\n[Procesando]" if estado == 0 else "CONSUMIDOR\n[ESPERANDO DATO]"
            self.root.after(0, lambda: self.lbl_cons.config(bg=bg, text=txt))

    # --- LÓGICA ---
    def proceso_productor(self):
        item_counter = 1
        while self.running:
            # Intentar producir (Si buffer lleno, se bloquea aquí)
            self.actualizar_actor("prod", 1) # Poner en estado de espera visual antes del acquire
            
            self.sem_espacios_vacios.acquire() 
            
            # Entró a zona crítica
            self.actualizar_actor("prod", 0) # Ya pasó, está trabajando
            
            with self.mutex:
                # Producir en la posición actual (Circular)
                dato = f"#{item_counter}"
                idx = self.idx_productor
                
                self.buffer[idx] = dato
                self.actualizar_slot(idx, True, dato)
                self.log(f"🟢 Productor: Creó {dato} en slot [{idx}]")
                
                # Mover índice circular
                self.idx_productor = (self.idx_productor + 1) % CAPACIDAD_BUFFER
                item_counter += 1

            self.sem_items_disponibles.release() # Avisar que hay item
            
            # Simular tiempo de producción real
            time.sleep(random.uniform(*TIEMPO_PRODUCIR))

    def proceso_consumidor(self):
        while self.running:
            # Intentar consumir (Si buffer vacío, se bloquea)
            self.actualizar_actor("cons", 1)
            
            self.sem_items_disponibles.acquire()
            
            # Entró a zona crítica
            self.actualizar_actor("cons", 0)
            
            with self.mutex:
                idx = self.idx_consumidor
                dato = self.buffer[idx]
                
                self.buffer[idx] = None
                self.actualizar_slot(idx, False) # Vaciar slot visualmente
                self.log(f"🔶 Consumidor: Retiró {dato} del slot [{idx}]")
                
                # Mover índice circular
                self.idx_consumidor = (self.idx_consumidor + 1) % CAPACIDAD_BUFFER

            self.sem_espacios_vacios.release() # Avisar que hay espacio
            
            # Simular tiempo de consumo
            time.sleep(random.uniform(*TIEMPO_CONSUMIR))

if __name__ == "__main__":
    root = tk.Tk()
    app = ProductorConsumidorGUI(root)
    
    def on_closing():
        app.running = False
        root.destroy()
        
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()