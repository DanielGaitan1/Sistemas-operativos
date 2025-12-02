import tkinter as tk
from tkinter import scrolledtext
import threading
import time
import random

# --- CONFIGURACIÓN ---
SILLAS_ESPERA = 5       # Número de sillas en la sala de espera
TIEMPO_CORTE_MIN = 1.0  # Segundos que tarda un corte
TIEMPO_CORTE_MAX = 3.0
LLEGADA_CLIENTES_MIN = 0.5
LLEGADA_CLIENTES_MAX = 2.0

# Colores de estado
COL_BARBERO_DURMIENDO = "#FF4444" # Rojo
COL_BARBERO_CORTANDO = "#44FF44"  # Verde
COL_SILLA_VACIA = "#DDDDDD"       # Gris claro
COL_SILLA_OCUPADA = "#5555FF"     # Azul

class BarberiaGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Simulación: El Barbero Dormilón")
        self.root.geometry("600x500")
        
        # Variables compartidas y Semáforos
        self.clientes_esperando = 0
        self.sillas_gui = [] # Lista para guardar referencias a los labels de las sillas
        self.mutex = threading.Lock()
        self.sem_clientes_listos = threading.Semaphore(0)
        self.sem_barbero_listo = threading.Semaphore(0)
        self.running = True

        # --- INTERFAZ GRÁFICA ---
        # 1. Zona del Barbero
        frame_barbero = tk.LabelFrame(root, text=" Zona del Barbero ", font=("Arial", 12, "bold"), padx=10, pady=10)
        frame_barbero.pack(fill="x", padx=20, pady=10)

        self.lbl_estado_barbero = tk.Label(frame_barbero, text="DURMIENDO Zzz...", bg=COL_BARBERO_DURMIENDO, fg="white", font=("Arial", 14, "bold"), width=25, height=2, relief="ridge")
        self.lbl_estado_barbero.pack()
        
        self.lbl_silla_barbero = tk.Label(frame_barbero, text="[ Silla del Barbero ]", font=("Arial", 10))
        self.lbl_silla_barbero.pack(pady=5)

        # 2. Zona de Espera
        frame_espera = tk.LabelFrame(root, text=f" Sala de Espera ({SILLAS_ESPERA} lugares) ", font=("Arial", 12), padx=10, pady=10)
        frame_espera.pack(fill="x", padx=20, pady=10)
        
        frame_sillas_container = tk.Frame(frame_espera)
        frame_sillas_container.pack()

        # Crear visualmente las sillas de espera
        for i in range(SILLAS_ESPERA):
            lbl_silla = tk.Label(frame_sillas_container, text=f"Silla {i+1}", bg=COL_SILLA_VACIA, width=8, height=3, relief="sunken", borderwidth=2)
            lbl_silla.pack(side=tk.LEFT, padx=5)
            self.sillas_gui.append(lbl_silla)

        # 3. Log de eventos (para no usar la terminal negra)
        tk.Label(root, text="Registro de Eventos:").pack(anchor="w", padx=20)
        self.log_box = scrolledtext.ScrolledText(root, height=8, width=70, state='disabled')
        self.log_box.pack(padx=20, pady=(0,20))

        # --- INICIAR HILOS ---
        self.thread_barbero = threading.Thread(target=self.proceso_barbero, daemon=True)
        self.thread_barbero.start()
        
        # Hilo generador de clientes
        self.thread_generador = threading.Thread(target=self.generar_clientes, daemon=True)
        self.thread_generador.start()

    # --- FUNCIONES AUXILIARES GUI (THREAD-SAFE) ---
    def log(self, mensaje):
        # Método seguro para escribir en el log desde otros hilos
        self.root.after(0, self._log_safe, mensaje)

    def _log_safe(self, mensaje):
        self.log_box.config(state='normal')
        self.log_box.insert(tk.END, mensaje + "\n")
        self.log_box.see(tk.END) # Auto-scroll al final
        self.log_box.config(state='disabled')

    def actualizar_silla_espera(self, indice, ocupada):
        color = COL_SILLA_OCUPADA if ocupada else COL_SILLA_VACIA
        texto = f"Cliente\nEsperando" if ocupada else f"Silla {indice+1}\nVacía"
        fg_color = "white" if ocupada else "black"
        # Usamos root.after para que el hilo principal de la GUI haga el cambio
        self.root.after(0, lambda: self.sillas_gui[indice].config(bg=color, text=texto, fg=fg_color))

    def actualizar_barbero(self, estado_cortando):
        color = COL_BARBERO_CORTANDO if estado_cortando else COL_BARBERO_DURMIENDO
        texto = "CORTANDO CABELLO ✂️" if estado_cortando else "DURMIENDO Zzz..."
        silla_txt = "[ Silla Ocupada por Cliente ]" if estado_cortando else "[ Silla del Barbero Vacía ]"
        self.root.after(0, lambda: self.lbl_estado_barbero.config(bg=color, text=texto))
        self.root.after(0, lambda: self.lbl_silla_barbero.config(text=silla_txt))

    # --- LÓGICA DE HILOS ---
    def proceso_barbero(self):
        while self.running:
            self.log("Barbero: No hay nadie, me duermo...")
            self.actualizar_barbero(estado_cortando=False)
            
            # Espera a que llegue un cliente (se duerme)
            self.sem_clientes_listos.acquire()
            
            # Despierta y atiende
            with self.mutex:
                # Encuentra qué silla liberar (la primera ocupada)
                silla_a_liberar = -1
                for i in range(SILLAS_ESPERA):
                     # Checamos el color para saber si está ocupada (un truco visual rapido)
                    if self.sillas_gui[i].cget("bg") == COL_SILLA_OCUPADA:
                        silla_a_liberar = i
                        break
                
                if silla_a_liberar != -1:
                    self.actualizar_silla_espera(silla_a_liberar, False)
                    self.clientes_esperando -= 1
                    self.log(f"Barbero: Desperté! Atendiendo cliente de silla {silla_a_liberar+1}. Quedan {self.clientes_esperando} esperando.")

            # Avisa que está listo para cortar
            self.sem_barbero_listo.release()
            
            # Cortando el cabello (tiempo y visual)
            self.actualizar_barbero(estado_cortando=True)
            tiempo_corte = random.uniform(TIEMPO_CORTE_MIN, TIEMPO_CORTE_MAX)
            time.sleep(tiempo_corte)
            self.log("Barbero: Corte terminado. ¡Siguiente!")

    def proceso_cliente(self, id_cliente):
        self.log(f"Cliente {id_cliente}: Llegó a la barbería.")
        with self.mutex:
            if self.clientes_esperando < SILLAS_ESPERA:
                # Hay lugar, buscamos silla vacía
                silla_libre = -1
                for i in range(SILLAS_ESPERA):
                    if self.sillas_gui[i].cget("bg") == COL_SILLA_VACIA:
                        silla_libre = i
                        break
                
                self.clientes_esperando += 1
                self.actualizar_silla_espera(silla_libre, True)
                self.log(f"Cliente {id_cliente}: Tomé la silla {silla_libre+1}. Espero mi turno.")
                self.sem_clientes_listos.release() # Despierta al barbero si duerme
            else:
                 self.log(f"Cliente {id_cliente}: Barbería llena. Me voy enojado.")
                 return # Se va

        # Espera a que el barbero le corte el pelo
        self.sem_barbero_listo.acquire()
        # (El tiempo de corte ocurre en el hilo del barbero)
        self.log(f"Cliente {id_cliente}: ¡Me cortaron el pelo! Me voy feliz.")

    def generar_clientes(self):
        id_counter = 1
        while self.running:
            time.sleep(random.uniform(LLEGADA_CLIENTES_MIN, LLEGADA_CLIENTES_MAX))
            t = threading.Thread(target=self.proceso_cliente, args=(id_counter,), daemon=True)
            t.start()
            id_counter += 1

if __name__ == "__main__":
    root = tk.Tk()
    app = BarberiaGUI(root)
    # Manejo seguro del cierre de ventana
    def on_closing():
        app.running = False
        app.log("Cerrando aplicación... Espere a que terminen los hilos activos.")
        # Liberamos semáforos para evitar deadlocks al cerrar
        app.sem_clientes_listos.release() 
        root.destroy()
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()