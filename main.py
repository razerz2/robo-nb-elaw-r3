import logging
from logging.handlers import RotatingFileHandler
import shutil
import tempfile
import time
from datetime import datetime
from pathlib import Path

from config import (
    INTERVALO_BAIXAR, OUTPUT_NAME, FINAL_DIR,
    WORK_START_HOUR, WORK_END_HOUR
)
from services.driver_factory import create_driver
from services.auth import login, logout
# from services.reports_processos import gerar_relatorio
from services.reports_iniciais import gerar_relatorio
from services.baixar_relatorio import baixar_relatorio
from services.utils import dentro_horario, proximo_dia_util_at, perguntar_com_timeout


# =================== LOGGING ===================
LOG_PATH = Path("logs/robo-elaw.log")
LOG_PATH.parent.mkdir(exist_ok=True)

logger = logging.getLogger("robo-elaw")
logger.setLevel(logging.INFO)
fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

fh = RotatingFileHandler(LOG_PATH, maxBytes=2_000_000, backupCount=3, encoding="utf-8")
fh.setFormatter(fmt)
logger.addHandler(fh)

ch = logging.StreamHandler()
ch.setFormatter(fmt)
logger.addHandler(ch)
# =================================================


def run_once():
    """Executa o ciclo completo: login → gerar → baixar → logout → fechar navegador."""
    profile_path = Path(tempfile.mkdtemp())
    driver = create_driver()
    try:
        logger.info("🚀 Login...")
        login(driver)

        logger.info("🧾 Gerando relatório de processos...")
        relatorio_id = gerar_relatorio(driver)
        # relatorio_id = "3611642"
        logger.info(f"🆔 ID: {relatorio_id}")

        logger.info("⬇️ Baixando relatório...")
        baixar_relatorio(driver, relatorio_id, FINAL_DIR, OUTPUT_NAME, INTERVALO_BAIXAR)

        logger.info("✅ Execução OK.")

    except Exception as e:
        logger.exception(f"❌ Erro durante a execução: {e}")
        raise

    finally:
        # 🔹 Sempre tentar logout, mesmo em caso de erro
        try:
            logout(driver)
            logger.info("↩️ Logout executado com sucesso.")
        except Exception as e:
            logger.warning(f"⚠️ Falha ao realizar logout: {e}")

        # 🔹 Fecha completamente o navegador
        try:
            driver.quit()
            logger.info("🧹 Navegador encerrado.")
        except Exception as e:
            logger.warning(f"⚠️ Falha ao encerrar navegador: {e}")

        # 🔹 Limpa perfil temporário do Chrome
        shutil.rmtree(profile_path, ignore_errors=True)

def main():
    """Loop principal: executa uma vez por dia útil, dentro do horário configurado."""
    ultima_execucao = None

    try:
        while True:
            now = datetime.now()

            # Evita rodar duas vezes no mesmo dia
            if ultima_execucao and ultima_execucao.date() == now.date():
                logger.info("✅ Já executado hoje. Aguardando próximo dia útil 08:00...")
                prox = proximo_dia_util_at(WORK_START_HOUR)
                time.sleep(max(10, (prox - now).total_seconds()))
                continue

            # Checa horário permitido
            if not dentro_horario(WORK_START_HOUR, WORK_END_HOUR):
                resposta = perguntar_com_timeout(
                    "⏸ Fora do horário de execução (Seg-Sex, 08h às 18h).\n👉 Deseja executar mesmo assim? (Y/N): ",
                    timeout=15,
                )
                if resposta != "y":
                    logger.info("⏳ Fora do horário, aguardando 30 minutos para checar novamente...")
                    time.sleep(30 * 60)
                    continue
                else:
                    logger.warning("⚠️ Executando fora do horário por confirmação manual do usuário.")

            # Executa rotina principal
            try:
                run_once()
                ultima_execucao = datetime.now()
            except Exception as e:
                logger.exception(f"❌ Erro na execução principal: {e}")
                logger.info("🕒 Tentará novamente em 5 minutos...")
                time.sleep(300)

    except KeyboardInterrupt:
        logger.info("🧩 Execução interrompida manualmente pelo usuário. 🛑 Encerrando com segurança...")
        # Evita que apareça o traceback feio
        return

   
if __name__ == "__main__":
    main()
