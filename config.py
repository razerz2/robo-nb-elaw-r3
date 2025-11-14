from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()

# Credenciais
USER = os.getenv("EUSER")
PASSWORD = os.getenv("EPASS")

# URLs
URL_INICIAL = "https://sicredi.elaw.com.br/processoView.elaw"
URL_LOGOUT  = "https://sicredi.elaw.com.br/logout"
URL_LOGIN   = "https://sicredi.elaw.com.br/login.elaw"

# Execução
HEADLESS = os.getenv("HEADLESS", "true").lower() == "true"
WORK_START_HOUR = int(os.getenv("WORK_START_HOUR", "8"))
WORK_END_HOUR   = int(os.getenv("WORK_END_HOUR",   "18"))

# Horário exato desejado para a execução
RUN_AT_HOUR = int(os.getenv("HOUR", "10"))
RUN_AT_MINUTE = int(os.getenv("MINUTE", "30"))

INTERVALO_EXECUCAO = int(os.getenv("INTERVALO_EXECUCAO", "60"))
INTERVALO_BAIXAR   = int(os.getenv("INTERVALO_BAIXAR",   "5"))

# Arquivo/pastas
OUTPUT_NAME = os.getenv("OUTPUT_NAME", "relatorio_recebimentos.xlsx")
FINAL_DIR   = Path(os.getenv("FINAL_DIR", ".")).expanduser()

# Downloads temporários (relativo ao projeto)
DOWNLOADS_TEMP = Path.cwd() / "downloads_temp"

# Validações leves
if not USER or not PASSWORD:
    raise RuntimeError("EUSER/EPASS não definidos no .env")

FINAL_DIR.mkdir(parents=True, exist_ok=True)
DOWNLOADS_TEMP.mkdir(parents=True, exist_ok=True)
