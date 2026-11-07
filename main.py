import os
from typing import Dict, List, Optional

from fastapi import FastAPI
from pydantic import BaseModel, Field
import uvicorn

from src.baseline_ons import Usina, baseline_execucao_ene


class UsinaInput(BaseModel):
    id_ons: str
    nome: str
    disponibilidade_mw: float
    geracao_mw: float
    limite_atual_mw: Optional[float] = None


class BaselineRequest(BaseModel):
    usinas: List[UsinaInput]
    corte_necessario_mw: float


class BaselineResponse(BaseModel):
    criterio: str
    corte_por_usina: Dict[str, float]
    corte_total_mw: float
    residual_mw: float = 0.0
    observacoes: List[str] = Field(default_factory=list)


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


@app.get("/baseline", response_model=BaselineResponse)
def get_baseline(req: BaselineRequest) -> BaselineResponse:
    usinas = [
        Usina(
            id_ons=u.id_ons,
            nome=u.nome,
            disponibilidade_mw=u.disponibilidade_mw,
            geracao_mw=u.geracao_mw,
            limite_atual_mw=u.limite_atual_mw,
        )
        for u in req.usinas
    ]
    res = baseline_execucao_ene(usinas, req.corte_necessario_mw)
    return BaselineResponse(
        criterio=res.criterio,
        corte_por_usina=res.corte_por_usina,
        corte_total_mw=res.corte_total_mw,
        residual_mw=res.residual_mw,
        observacoes=res.observacoes,
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
