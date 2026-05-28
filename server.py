
from fastapi import FastAPI
from pydantic import BaseModel
import time

app = FastAPI()

latest_signal = None
signal_time = 0

TOKENS_VALIDOS = [
    "cliente1",
    "cliente2",
    "cliente3"
]

class Signal(BaseModel):

    par: str
    direccion: str
    expiracion: int
    segundos: int

@app.get("/")
def home():

    return {
        "message": "Servidor funcionando"
    }

@app.post("/send_signal")
def send_signal(signal: Signal):

    global latest_signal
    global signal_time

    latest_signal = signal.dict()
    signal_time = time.time()

    print("\n===================================")
    print("SEÑAL RECIBIDA")
    print(latest_signal)
    print("===================================\n")

    return {
        "status": "ok"
    }

@app.get("/latest_signal")
def get_signal(token: str):

    global latest_signal
    global signal_time

    if token not in TOKENS_VALIDOS:

        return {
            "error": "acceso denegado"
        }

    if latest_signal is None:

        return {}

    tiempo_pasado = time.time() - signal_time

    if tiempo_pasado > 5:

        return {}

    return latest_signal

# =====================================================
# INICIAR SERVIDOR
# =====================================================

if __name__ == "__main__":

    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000
    )

