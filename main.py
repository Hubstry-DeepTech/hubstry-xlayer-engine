import os
from fastapi import FastAPI
import uvicorn

app = FastAPI(title="Hubstry X-Layer Engine API")

@app.get("/")
def health_check():
    return {"status": "online", "engine": "X-Layer Core Active"}

@app.get("/gates")
def list_gates():
    return {
        "available_modules": [
            "ons_client", "calibragem_v2", "calibragem_v3",
            "gate2_signal_test", "gate31a_analitico", "replay_v2"
        ]
    }

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
