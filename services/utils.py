import sys
import time
import threading
import calendar
import queue
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

def dentro_horario(start_hour: int, end_hour: int) -> bool:
    now = datetime.now()
    return now.weekday() < 5 and start_hour <= now.hour < end_hour

def proximo_dia_util_at(start_hour: int) -> datetime:
    d = datetime.now() + timedelta(days=1)
    while d.weekday() >= 5:  # 5=sábado, 6=domingo
        d += timedelta(days=1)
    return d.replace(hour=start_hour, minute=0, second=0, microsecond=0)

def esperar_download(pasta: Path, nome_final: str, timeout: int = 300, estabilidade_s: int = 3) -> Path:
    """
    Espera sumir .crdownload e tamanho estabilizar.
    Renomeia para nome_final (sobrescreve se existir).
    """
    pasta.mkdir(parents=True, exist_ok=True)
    deadline = time.time() + timeout
    destino = pasta / nome_final

    ultimo_ok: Optional[Path] = None
    ultimo_tam = -1
    ultimo_tam_igual_desde = None

    while time.time() < deadline:
        # pega o arquivo mais recente que NÃO termina com .crdownload
        candidatos = sorted([p for p in pasta.glob("*") if p.is_file() and not p.name.endswith(".crdownload")],
                            key=lambda p: p.stat().st_mtime, reverse=True)
        if candidatos:
            atual = candidatos[0]
            tam = atual.stat().st_size
            if tam == ultimo_tam:
                # mesmo tamanho desde...
                if ultimo_tam_igual_desde is None:
                    ultimo_tam_igual_desde = time.time()
                elif time.time() - ultimo_tam_igual_desde >= estabilidade_s:
                    ultimo_ok = atual
                    break
            else:
                ultimo_tam = tam
                ultimo_tam_igual_desde = None

        time.sleep(1)

    if not ultimo_ok:
    # fallback: se o destino já existir, usa ele mesmo
        if destino.exists():
             return destino
        raise TimeoutError("Tempo limite aguardando conclusão do download.")

    if destino.exists():
        destino.unlink()
    ultimo_ok.rename(destino)
    return destino

def perguntar_com_timeout(pergunta: str, timeout: int = 15) -> str:
    print(pergunta, end="", flush=True)

    q = queue.Queue()

    # Leitura de input em thread separada (não bloqueia o main)
    def ler_input():
        try:
            ans = sys.stdin.readline().strip().lower()
            q.put(ans)
        except:
            q.put(None)

    t = threading.Thread(target=ler_input)
    t.daemon = True
    t.start()

    inicio = time.time()

    while time.time() - inicio < timeout:
        try:
            resp = q.get_nowait()  # input chegou
            return resp
        except queue.Empty:
            time.sleep(0.1)

    print("\n⏰ Tempo esgotado, prosseguindo automaticamente...")
    return "n"

def proxima_execucao_agendada(hora, minuto):
    now = datetime.now()
    agendado = now.replace(hour=hora, minute=minuto, second=0, microsecond=0)

    # Se já passou do horário hoje, agenda para amanhã
    if agendado <= now:
        agendado += timedelta(days=1)

    # Pula finais de semana
    while agendado.weekday() >= 5:  # 5=Saturday, 6=Sunday
        agendado += timedelta(days=1)

    return agendado