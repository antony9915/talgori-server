

import subprocess
import threading
import tkinter as tk
from tkinter import ttk, messagebox
import json
import time
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
NGROK_PATH = r"C:\Users\aron9\AppData\Local\Microsoft\WindowsApps\ngrok.exe"
# ======================================================
# VARIABLES GLOBALES
# ======================================================
proceso = None
pares_seleccionados_gui = []
modo_tabla = "pares"  # pares | historial
ultimo_heartbeat = time.time()
filas_live = {}
ultimo_cierre = {}
MAX_FILAS = 30
perdidas_seguidas = 0
# ======================================================
# PROCESAR EVENTOS GUI (SOLO HILO PRINCIPAL)
# ======================================================
def procesar_evento(linea):
    try:
        data = json.loads(linea)
    except:
        return  # ignora basura

    ventana.after(0, procesar_evento_gui, data)


def procesar_evento_gui(data):
    global modo_tabla
    global ultimo_heartbeat
    global perdidas_seguidas

    tipo = data.get("type")
    #print("data:", data)
    
    if tipo == "heartbeat":
        ultimo_heartbeat = time.time()
        lbl_estado.config(text="🟢 Bot activo")    
        return
      
    if tipo == "estado":
        lbl_estado.config(text=data.get("msg", ""))

    elif tipo == "pares_disponibles":
        limpiar_tabla()
        configurar_tabla_pares()
        for p in data.get("pares", []):
            tabla.insert("", "end", values=(p["par"], f"{p['profit']}%"))

    elif tipo == "par_agregado":
        par = data["par"]
        if par not in pares_seleccionados_gui:
            pares_seleccionados_gui.append(par)

        texto = "Pares seleccionados:\n" + "\n".join(f"• {p}" for p in pares_seleccionados_gui)
        lbl_pares_sel.config(text=texto)
        lbl_info.config(text=f"➕ Par agregado: {par}")

    elif tipo == "maximo_par_alcanzado":
        messagebox.showinfo("Límite", "Máximo de pares alcanzado")

        limpiar_tabla()
        configurar_tabla_historial()
        modo_tabla = "historial"

    elif tipo == "selecciona_importe":
        lbl_info.config(text="💰 Ingrese el importe y presione ENTER")
        entry_importe.focus()

    elif tipo == "seleccione_un_numero":
        messagebox.showwarning("Importe", "Ingrese un número válido")
        entry_importe.focus()

    elif tipo == "importe":
        valor = data.get("valor")
        importe_var.set(str(valor))
        lbl_info.config(text=f"💰 Importe confirmado: ${valor}")

    elif tipo == "sl_tp":
        lbl_sl_tp.config(text=f"SL / TP:{data.get('sl')} / {data.get('tp')}")

    elif tipo == "compra":
        par = data.get("par", "-")
        direccion = data.get("direccion", "-").upper()
        monto = data.get("monto", "-")
        hora = data.get("hora", "-")

        texto_tipo = f"hora = {hora} | {direccion} | monto = $: {monto}"
        lbl_info.config(text=texto_tipo)
        iid = tabla.insert(
            "",
            "end",
            values=(
                par,          # 👈 columna PAR
                texto_tipo,   # 👈 todo lo demás en columna TIPO
                " ",          # columnas restantes vacías
                " ",
                " "
            ),
            tags=("compra",)
        )

        tabla.see(iid)
        tabla.yview_moveto(1.0)
        
    elif tipo == "simulada":
        iid = tabla.insert(
            "",
            "end",
            values=(
                data.get("par"),   # PAR
                "SIMULADA",        # TIPO
                " ",               # VALOR
                " ",               # BALANCE
                data.get("score")  # SCORE 👈 AQUÍ
            ),
            tags=("simulada",)
        )

        tabla.see(iid)
        tabla.yview_moveto(1.0)
 
    elif tipo == "resultado":
        valor = data.get("valor", 0)
        balance = data.get("balance", "-")
        score = data.get("score", "-")
        if valor < 0 :
            perdidas_seguidas += 1  
        elif valor > 0:
            perdidas_seguidas = 0

        
        tag = "resultado_pos" if balance > 0 else "resultado_neg"

        iid = tabla.insert(
            "",
            "end",
            values=(
                " ",        # PAR (no aplica)
                "RESULTADO",
                f"$ : {valor}",
                f"$ : {balance}",
                score       # SCORE 👈 AQUÍ
            ),
            tags=(tag,)
        )
        
        tabla.see(iid)
        tabla.yview_moveto(1.0)

        if perdidas_seguidas >= 6:
            detener()
            messagebox.showinfo("Límite", "bot detenido stop alcanzado")
            

    elif data.get("type") == "datas":
        datos = data.get("datos", {})
        #print('datos : ', datos)

        # 👉 Caso A: solo segundos (NO insertar en tabla)
        if "datos" not in datos:
            # segundos = datos.get("segundos")  # si quieres usarlo en un label
            return

        # 👉 Caso B: datos completos
        datos_internos = datos.get("datos", {})
        payload = datos_internos.get("payload", {})
        #print('payload',payload)
        if not payload:
            return

        par = payload.get("par")
        if not par:
            return
        
        # segundos solo para la primera fila
        segundos_valor = ""
        if filas_live:
            primer_iid = next(iter(filas_live.values()))
            if filas_live.get(par) == primer_iid:
                segundos_valor = payload.get("segundos", "")
        else:
            # aún no hay filas, esta será la primera
            segundos_valor = payload.get("segundos", "")

        valores = (
            par,
            payload.get("micro", ""),
            payload.get("max_r", ""),
            payload.get("min_r", ""),
            payload.get("open", ""),
            payload.get("cierre", ""),
            payload.get("fluctuacion", ""),
            payload.get("segundos", "")
        )

        cierre_actual = payload.get("cierre")

        # 🎯 determinar color
        tag_color = "neutral"

        if par in ultimo_cierre and cierre_actual is not None:
            try:
                if cierre_actual > ultimo_cierre[par]:
                    tag_color = "sube"
                elif cierre_actual < ultimo_cierre[par]:
                    tag_color = "baja"
            except:
                pass

        # guardar último cierre
        if cierre_actual is not None:
            ultimo_cierre[par] = cierre_actual

        valores = (
            par,
            payload.get("micro", ""),
            payload.get("max_r", ""),
            payload.get("min_r", ""),
            payload.get("open", ""),
            cierre_actual,
            payload.get("fluctuacion", ""),
            segundos_valor
        )

        # ➕ insertar SIEMPRE nueva fila (stream)
        iid = tabla_live.insert(
            "",
            "end",
            values=valores,
            tags=(tag_color,)
        )

        # 🔽 scroll automático al último
        tabla_live.see(iid)

        # 🧹 mantener solo las últimas 20 filas
        filas_actuales = tabla_live.get_children()

        if len(filas_actuales) > MAX_FILAS:
            for fila in filas_actuales[:len(filas_actuales) - MAX_FILAS]:
                tabla_live.delete(fila)

        #print(f"🔄 {par} cierre={cierre_actual} tag={tag_color}")


        
def watchdog():
    if time.time() - ultimo_heartbeat > 60:
        lbl_estado.config(text="⚠ Sin datos del bot")
        lbl_info.config(text=f'⚠ Sin datos del bot')
    ventana.after(10000, watchdog)


# ======================================================
# THREAD SAFE
# ======================================================
def procesar_evento(linea):
    try:
        data = json.loads(linea)
    except:
        return
    ventana.after(0, procesar_evento_gui, data)


# ======================================================
# TABLA
# ======================================================
def limpiar_tabla():
    tabla.delete(*tabla.get_children())


def configurar_tabla_pares():
    tabla["columns"] = ("par", "profit")
    tabla.heading("par", text="PAR")
    tabla.heading("profit", text="PROFIT")
    tabla.column("par", width=200)
    tabla.column("profit", width=80, anchor="center")


def configurar_tabla_historial():
    tabla["columns"] = ("par", "tipo", "valor", "balance", "score")

    tabla.heading("par", text="PAR")
    tabla.heading("tipo", text="ESTADO")
    tabla.heading("valor", text="RESULTADO")
    tabla.heading("balance", text="BALANCE")
    tabla.heading("score", text="SCORE")

    tabla.column("par", width=25, anchor="center")
    tabla.column("tipo", width=90, anchor="center")
    tabla.column("valor", width=15, anchor="center")
    tabla.column("balance", width=15, anchor="center")
    # 👇 MÁS ESPACIO PARA SCORE
    tabla.column(
        "score",
        width=160,      # ancho principal
        minwidth=140,   # mínimo si se redimensiona
        anchor="center",
        stretch=True    # permite que crezca
    )


# ======================================================
# BOT
# ======================================================
def ejecutar_bot______________________():
    global proceso

    proceso = subprocess.Popen(
        ["python", "-u", "bot-binarias.py"],
        cwd=BASE_DIR,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )

    threading.Thread(
        target=leer_stdout,
        daemon=True
    ).start()
    

def ejecutar_bot():
    global proceso

    proceso = subprocess.Popen(
        [sys.executable, "-u", "bot-binarias.py"],
        cwd=BASE_DIR,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
    )

    threading.Thread(
        target=leer_stdout,
        daemon=True
    ).start()
    
   
    # =========================================
    # INICIAR FASTAPI
    # =========================================
    subprocess.Popen([sys.executable, "server.py"],cwd=BASE_DIR)
    time.sleep(3)

    # =========================================
    # INICIAR NGROK
    # =========================================
    subprocess.Popen([NGROK_PATH, "http", "8000"],cwd=BASE_DIR)
    time.sleep(5)

    # =========================================
    # ACTUALIZAR GITHUB
    # =========================================
    subprocess.Popen([sys.executable, "update_github.py"],cwd=BASE_DIR)
    print("SERVIDOR COMPLETO INICIADO")

def leer_stdout():
    while True:
        linea = proceso.stdout.readline()
        if not linea:
            break
        procesar_evento(linea.strip())

    ventana.after(
        0,
        lbl_estado.config,
        {"text": "🔴 Bot desconectado"}
    )


def iniciar():
    btn_iniciar.config(state="disabled")
    threading.Thread(target=ejecutar_bot, daemon=True).start()

def detener():
    global proceso
    if proceso and proceso.poll() is None:
        subprocess.call(
            ["taskkill", "/F", "/T", "/PID", str(proceso.pid)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )



def enviar_input(event=None):
    if proceso and proceso.stdin:
        texto = entrada_var.get().strip()
        proceso.stdin.write(texto + "\n")
        proceso.stdin.flush()
        entrada_var.set("")


def enviar_importe(event=None):
    valor = importe_var.get().strip()
    if not valor.isdigit():
        messagebox.showwarning("Importe", "Ingrese un número válido")
        return
    proceso.stdin.write(valor + "\n")
    proceso.stdin.flush()


def seleccionar_par(event):
    if modo_tabla != "pares":
        return
    item = tabla.focus()
    if not item:
        return
    par = tabla.item(item)["values"][0]
    proceso.stdin.write(par + "\n")
    proceso.stdin.flush()


# ======================================================
# GUI
# ======================================================
# ================== VENTANA PRINCIPAL ==================
ventana = tk.Tk()
ventana.title("TALGORI")
ventana.geometry("1100x650")
ventana.configure(bg="#030304")

# ================== STYLE ==================
style = ttk.Style()
style.theme_use("default")
style.configure(
    "Treeview",
    background="#1A1A1D",
    foreground="white",
    fieldbackground="#121212",
    rowheight=15
)
style.configure(
    "Treeview.Heading",
    background="#030304",
    foreground="white",
    font=("Segoe UI", 8)
)
style.map("Treeview", background=[("selected", "#007acc")])

style.map(
    "Treeview.Heading",
    background=[("active", "#1C1B21")],  # color al pasar el mouse
    foreground=[("active", "white")]
)
# usando canvas para las curvas
header = tk.Canvas(
    ventana,
    width=600,
    height=50,
    bg=ventana["bg"],
    highlightthickness=0
)
header.pack(pady=10)

def rounded_rect(canvas, x1, y1, x2, y2, r, **kwargs):
    points = [
        x1+r, y1,
        x2-r, y1,
        x2, y1,
        x2, y1+r,
        x2, y2-r,
        x2, y2,
        x2-r, y2,
        x1+r, y2,
        x1, y2,
        x1, y2-r,
        x1, y1+r,
        x1, y1
    ]
    canvas.create_polygon(points, smooth=True, **kwargs)

# fondo curvo
rounded_rect(
    header,
    5, 5, 595, 45,
    r=18,
    fill="#9E9E9D",
    outline=""
)

# texto TALGORI
header.create_text(
    300, 25,
    text="TALGORI",
    fill="#01000A",  # gold,
    font=("Segoe UI", 16)
)

"""# ================== HEADER ==================
tk.Label(
    ventana,
    text="TALGORI",
    bg="#1C1B21",
    fg="white",
    font=("Segoe UI", 16),
    width=60  # número de caracteres de ancho
).pack(pady=10)"""


# ================== MAIN CONTAINER ==================
main = tk.Frame(ventana, bg="#030304")
main.pack(expand=True, fill="both", padx=10, pady=10)

main.columnconfigure(0, weight=1)
main.columnconfigure(1, weight=3)
main.rowconfigure(0, weight=2)
main.rowconfigure(1, weight=1)

# ================== PARÁMETROS ==================
frame_param = tk.LabelFrame(main, text=" Parámetros ", fg="#9CA708", bg="#1C1B21")
frame_param.grid(row=0, column=0, sticky="nsew", padx=5, pady=7)

lbl_estado = tk.Label(frame_param, text="Esperando inicio...", fg="#00ff00", bg="#030304")
lbl_estado.pack(anchor="w", padx=10, pady=7)

lbl_pares_sel = tk.Label(frame_param, text="Pares seleccionados:\n-", fg="#9CA708", bg="#030304", justify="left")
lbl_pares_sel.pack(anchor="w", padx=10)

frame_importe = tk.Frame(frame_param, bg="#030304")
frame_importe.pack(anchor="w", padx=10, pady=7)

tk.Label(frame_importe, text="💰 Importe:", fg="white", bg="#030304").pack(side="left")
importe_var = tk.StringVar()
entry_importe = tk.Entry(frame_importe, textvariable=importe_var, width=10)
entry_importe.pack(side="left")
entry_importe.bind("<Return>", enviar_importe)

lbl_sl_tp = tk.Label(frame_param, text="SL / TP  : Automatico", fg="white", bg="#030304")
lbl_sl_tp.pack(anchor="w", padx=10)

lbl_getion = tk.Label(frame_param, text="GESTION  : score + martingala", fg="white", bg="#030304")
lbl_getion.pack(anchor="w", padx=10, pady=7)

lbl_score = tk.Label(
    frame_param,
    text=(
        "• SCORE INICIAL : 60 / 100\n"
        "• SCORE MIN     : 58 / 100\n"
        "• FACTOR DECAY  : 0.99"
    ),
    fg="white", bg="#030304", justify="left"
)
lbl_score.pack(anchor="w", padx=10)


# ================== DATOS EN TIEMPO REAL ==================
frame_live = tk.LabelFrame(main, text=" Datos en tiempo real ", fg="#9CA708", bg="#1C1B21")
frame_live.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)

# ================== TABLA DATOS EN TIEMPO REAL ==================
tabla_live = ttk.Treeview(frame_live, show="headings")
tabla_live.pack(expand=True, fill="both")


tabla_live["columns"] = ("par", "micro","max_r", "min_r", "open", "cierre", "fluctuacion", "segundos")
tabla_live.tag_configure("sube", foreground="#059605")     # verde
tabla_live.tag_configure("baja", foreground="#8d0303")     # rojo
tabla_live.tag_configure("neutral", foreground="#cfb4b4") # blanco

tabla_live.heading("par", text="PAR")
tabla_live.heading("micro", text="CONTEXTO")
tabla_live.heading("max_r", text="MAX_R")
tabla_live.heading("min_r", text="MIN_R")
tabla_live.heading("open", text="OPEN")
tabla_live.heading("cierre", text="CIERRE")
tabla_live.heading("fluctuacion", text="FLUCT")
tabla_live.heading("segundos", text="SEG")

tabla_live.column("par", width=90)
tabla_live.column("micro", width=140)
tabla_live.column("max_r", width=90, anchor="center")
tabla_live.column("min_r", width=90, anchor="center")
tabla_live.column("open", width=90, anchor="center")
tabla_live.column("cierre", width=90, anchor="center")
tabla_live.column("fluctuacion", width=90, anchor="center")
tabla_live.column("segundos", width=60, anchor="center")


lbl_info = tk.Label(frame_live, text="", fg="cyan", bg="#2b2b2b", justify="left")
lbl_info.pack(anchor="nw", padx=10, pady=10)

# ================== HISTORIAL / RESULTADOS ==================
frame_hist = tk.LabelFrame(main, text=" Resultados ", fg="#9CA708", bg="#2b2b2b")
frame_hist.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=5, pady=5)

tabla = ttk.Treeview(frame_hist, show="headings")
tabla.pack(expand=True, fill="both")
tabla.bind("<Double-1>", seleccionar_par)


# TAGS
tabla.tag_configure("compra", foreground="#5BFC76")
tabla.tag_configure("simulada", foreground="#ffaa00")
tabla.tag_configure("resultado_pos", foreground="#00ff00")
tabla.tag_configure("resultado_neg", foreground="#ff4444")

configurar_tabla_pares()

# ================== INPUT ==================
frame_input = tk.Frame(ventana, bg="#1C1B21")
frame_input.pack(fill="x", padx=10, pady=5)

entrada_var = tk.StringVar()
entrada = tk.Entry(frame_input, textvariable=entrada_var, bg="#030304", fg="white")  # fondo gris oscuro, texto blanco
entrada.pack(side="left", expand=True, fill="x")

entrada.bind("<Return>", enviar_input)

tk.Button(frame_input, text="ENTER", command=enviar_input, bg="#767D1B", fg="black", width=10).pack(side="right")

# ================== BOTONES ==================
frame_btn = tk.Frame(ventana, bg="#2b2b2b")
frame_btn.pack(pady=10)

btn_iniciar = tk.Button(frame_btn, text="▶ INICIO", command=iniciar, bg="#28a745", fg="white", width=15)
btn_iniciar.pack(side="left", padx=5)

tk.Button(frame_btn, text="⛔ DETENER", command=detener, bg="#dc3545", fg="white", width=15).pack(side="left")

watchdog()
ventana.mainloop()
