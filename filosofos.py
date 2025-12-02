import tkinter as tk
from tkinter import scrolledtext
import threading
import time
import random
import math

# --- CONFIGURACIÓN ---
NUM_FILOSOFOS = 5
TIEMPO_PENSAR_MIN = 1.0
TIEMPO_PENSAR_MAX = 3.0
TIEMPO_COMER_MIN = 2.0
TIEMPO_COMER_MAX = 4.0

# Colores
C_PENSANDO = "white"
C_HAMBRIENTO = "#FFD700" # Gold/Amarillo
C_COMIENDO = "#32CD32"   # LimeGreen
C_TENEDOR_LIBRE = "black"
C_TENEDOR_OCUPADO = "red"

class CenaFilosofosGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Simulación: Cena de los Filósofos (Sin Deadlocks)")
        self.root.geometry("700x600")
        
        # Objetos de sincronización
        # Cada tenedor es un Mutex (Lock)
        self.tenedores_locks = [threading.Lock() for _ in range(NUM_FILOSOFOS)]
        self.running = True

        # --- INTERFAZ GRÁFICA ---
        # 1. Panel Superior (Canvas de la Mesa)
        self.canvas = tk.Canvas(root, width=600, height=400, bg="#f0f0f0")
        self.canvas.pack(pady=10)
        
        # Dibujar mesa central
        cx, cy = 300, 200
        radio_mesa = 100
        self.canvas.create_oval(cx-radio_mesa, cy-radio_mesa, cx+radio_mesa, cy+radio_mesa, fill="#8B4513", outline="") # Mesa café

        # Listas para guardar referencias a los dibujos y actualizarlos
        self.filosofos_gui = [] # Círculos
        self.textos_gui = []    # Textos (F1, F2...)
        self.tenedores_gui = [] # Líneas

        # Calcular posiciones en círculo (Trigonometría básica)
        radio_filosofos = 160
        radio_tenedores = 120
        
        for i in range(NUM_FILOSOFOS):
            angulo = (2 * math.pi * i) / NUM_FILOSOFOS - (math.pi / 2) # -pi/2 para empezar arriba
            
            # Posición del Filósofo
            fx = cx + radio_filosofos * math.cos(angulo)
            fy = cy + radio_filosofos * math.sin(angulo)
            
            # Dibujar Filósofo (Círculo)
            f_id = self.canvas.create_oval(fx-30, fy-30, fx+30, fy+30, fill=C_PENSANDO, width=2)
            t_id = self.canvas.create_text(fx, fy, text=f"F{i+1}\nPensando", font=("Arial", 9, "bold"))
            self.filosofos_gui.append(f_id)
            self.textos_gui.append(t_id)

            # Posición del Tenedor (Entre filósofo i y filósofo i+1)
            angulo_t = angulo + (math.pi / NUM_FILOSOFOS)
            tx = cx + radio_tenedores * math.cos(angulo_t)
            ty = cy + radio_tenedores * math.sin(angulo_t)
            
            # Dibujar Tenedor (Línea simple)
            # Hacemos una linea gruesa para que se vea
            l_id = self.canvas.create_line(tx-10, ty-10, tx+10, ty+10, width=5, fill=C_TENEDOR_LIBRE)
            self.canvas.create_text(tx, ty-15, text=f"T{i+1}", font=("Arial", 8))
            self.tenedores_gui.append(l_id)

        # 2. Log de Eventos
        frame_log = tk.LabelFrame(root, text=" Bitácora de la Cena ", padx=10, pady=10)
        frame_log.pack(fill="both", expand=True, padx=20, pady=10)
        
        self.log_box = scrolledtext.ScrolledText(frame_log, height=8, state='disabled')
        self.log_box.pack(fill="both", expand=True)

        # --- INICIAR HILOS ---
        self.threads = []
        for i in range(NUM_FILOSOFOS):
            t = threading.Thread(target=self.proceso_filosofo, args=(i,), daemon=True)
            self.threads.append(t)
            t.start()

    # --- GUI UPDATE SAFE ---
    def log(self, mensaje):
        self.root.after(0, lambda: self._log_internal(mensaje))

    def _log_internal(self, mensaje):
        self.log_box.config(state='normal')
        self.log_box.insert(tk.END, mensaje + "\n")
        self.log_box.see(tk.END)
        self.log_box.config(state='disabled')

    def actualizar_filosofo(self, indice, estado):
        # Estado: 0=Pensando, 1=Hambriento, 2=Comiendo
        color = C_PENSANDO
        texto = "Pensando"
        if estado == 1:
            color = C_HAMBRIENTO
            texto = "HAMBRIENTO"
        elif estado == 2:
            color = C_COMIENDO
            texto = "COMIENDO"
        
        self.root.after(0, lambda: self.canvas.itemconfig(self.filosofos_gui[indice], fill=color))
        self.root.after(0, lambda: self.canvas.itemconfig(self.textos_gui[indice], text=f"F{indice+1}\n{texto}"))

    def actualizar_tenedor(self, indice, ocupado):
        color = C_TENEDOR_OCUPADO if ocupado else C_TENEDOR_LIBRE
        self.root.after(0, lambda: self.canvas.itemconfig(self.tenedores_gui[indice], fill=color))

    # --- LÓGICA FILÓSOFOS ---
    def proceso_filosofo(self, id_filosofo):
        # Identificar tenedores (Izquierda y Derecha)
        # Tenedor izquierdo es el del mismo índice
        # Tenedor derecho es (índice + 1) % N
        tenedor_izq = self.tenedores_locks[id_filosofo]
        tenedor_der = self.tenedores_locks[(id_filosofo + 1) % NUM_FILOSOFOS]
        
        idx_izq = id_filosofo
        idx_der = (id_filosofo + 1) % NUM_FILOSOFOS

        # Para evitar DEADLOCK: Siempre tomar el tenedor de menor índice primero
        # Esto rompe la simetría circular (espera circular)
        primero_lock = tenedor_izq if idx_izq < idx_der else tenedor_der
        segundo_lock = tenedor_der if primero_lock == tenedor_izq else tenedor_izq
        
        idx_primero = idx_izq if idx_izq < idx_der else idx_der
        idx_segundo = idx_der if idx_primero == idx_izq else idx_izq

        while self.running:
            # 1. PENSAR
            self.actualizar_filosofo(id_filosofo, 0)
            tiempo = random.uniform(TIEMPO_PENSAR_MIN, TIEMPO_PENSAR_MAX)
            # self.log(f"Filósofo {id_filosofo+1} está pensando por {tiempo:.1f}s.")
            time.sleep(tiempo)

            # 2. HAMBRIENTO
            self.actualizar_filosofo(id_filosofo, 1)
            self.log(f"Filósofo {id_filosofo+1} tiene HAMBRE.")
            
            # 3. INTENTAR COMER (Tomar tenedores)
            with primero_lock:
                self.actualizar_tenedor(idx_primero, True)
                # self.log(f"Filósofo {id_filosofo+1} tomó tenedor {idx_primero+1}.")
                
                with segundo_lock:
                    self.actualizar_tenedor(idx_segundo, True)
                    
                    # 4. COMIENDO (Sección Crítica)
                    self.actualizar_filosofo(id_filosofo, 2)
                    self.log(f"--- Filósofo {id_filosofo+1} COMIENDO ---")
                    time.sleep(random.uniform(TIEMPO_COMER_MIN, TIEMPO_COMER_MAX))
                
                # Soltó segundo
                self.actualizar_tenedor(idx_segundo, False)
            
            # Soltó primero
            self.actualizar_tenedor(idx_primero, False)
            self.log(f"Filósofo {id_filosofo+1} terminó y soltó tenedores.")

if __name__ == "__main__":
    root = tk.Tk()
    app = CenaFilosofosGUI(root)
    
    def on_closing():
        app.running = False
        root.destroy()
        
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()