import logging
import shutil
import tempfile
import time
from logging.handlers import RotatingFileHandler
from datetime import datetime
from pathlib import Path
from config import (
    INTERVALO_BAIXAR, OUTPUT_NAME, FINAL_DIR,
    WORK_START_HOUR, WORK_END_HOUR, RUN_AT_HOUR, RUN_AT_MINUTE
)
from services.driver_factory import create_driver
from services.auth import login, logout, is_logged_in
from services.reports_iniciais import gerar_relatorio
from services.baixar_relatorio import baixar_relatorio
from services.utils import dentro_horario, proximo_dia_util_at, perguntar_com_timeout, proxima_execucao_agendada
from services.checkpoint import checkpoint_clear, checkpoint_load, checkpoint_save

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
    estado = checkpoint_load()
    profile_path = Path(tempfile.mkdtemp())
    driver = create_driver()

    # ======================================
    # 0) LOGIN SEMPRE É GARANTIDO AO INICIAR
    # ======================================
    try:
        if not is_logged_in(driver):
            logger.info("🔐 Sessão inexistente. Realizando login...")
            login(driver)
        else:
            logger.info("🔒 Sessão já estava ativa.")
    except:
        logger.info("🔐 Realizando login inicial...")
        login(driver)

    try:
        # ===============================
        # 1) GERAR RELATÓRIO
        # ===============================
        if not estado or estado["stage"] == "login":
            # "login" nunca deve ser uma etapa, removemos isso
            pass

        if not estado or estado["stage"] in ["gerou_relatorio"]:
            # se gerou e reiniciou: retomar ID
            relatorio_id = estado.get("relatorio_id")
            if relatorio_id:
                logger.info(f"🔁 Retomando com relatório ID salvo: {relatorio_id}")
            else:
                logger.info("🧾 Gerando relatório de processos...")
                relatorio_id = gerar_relatorio(driver)
                logger.info(f"🆔 ID: {relatorio_id}")
                checkpoint_save("gerou_relatorio", relatorio_id)

        # ===============================
        # 2) BAIXAR RELATÓRIO
        # ===============================
        if not estado or estado["stage"] == "gerou_relatorio":
            logger.info("⬇️ Baixando relatório...")
            baixar_relatorio(driver, relatorio_id, FINAL_DIR, OUTPUT_NAME, INTERVALO_BAIXAR)
            checkpoint_save("baixou_relatorio", relatorio_id)

        logger.info("✅ Execução OK.")

    except Exception as e:
        logger.exception(f"❌ Erro durante a execução: {e}")
        raise

    finally:
        try:
            logout(driver)
        except:
            pass
        driver.quit()
        checkpoint_clear()

def main():
    
    ultima_execucao = None

    try:
        while True:
            now = datetime.now()
            executar_fora_do_horario = False  # <-- novo

            # Já executou hoje
            if ultima_execucao and ultima_execucao.date() == now.date():
                logger.info("✅ Já executado hoje. Aguardando próximo dia útil 08:00...")
                prox = proximo_dia_util_at(WORK_START_HOUR)
                time.sleep(max(10, (prox - now).total_seconds()))
                continue

            # Fora do horário permitido
            if not dentro_horario(WORK_START_HOUR, WORK_END_HOUR):
                resposta = perguntar_com_timeout(
                    "⏸ Fora do horário de execução (Seg-Sex, 08h às 18h).\n👉 Deseja executar mesmo assim? (Y/N): ",
                    timeout=15,
                )

                if resposta == "y":
                    logger.warning("⚠️ Executando fora do horário por confirmação manual do usuário.")
                    executar_fora_do_horario = True
                else:
                    logger.info("⏳ Fora do horário, aguardando 30 minutos para checar novamente...")
                    time.sleep(30 * 60)
                    continue

            # =============================
            # Checa horário programado apenas se NÃO for execução forçada
            # =============================
            if not executar_fora_do_horario:
                if not (now.hour == RUN_AT_HOUR and now.minute >= RUN_AT_MINUTE):
                    logger.info(
                        f"⏳ Aguardando horário programado: "
                        f"{RUN_AT_HOUR:02d}:{RUN_AT_MINUTE:02d} "
                        f"(agora {now.hour:02d}:{now.minute:02d})"
                    )
                    time.sleep(60)
                    continue

            # Execução principal
            try:
                run_once()
                ultima_execucao = datetime.now()
            except Exception as e:
                logger.exception(f"❌ Erro na execução principal: {e}")
                logger.info("🕒 Tentará novamente em 5 minutos...")
                time.sleep(300)

    except KeyboardInterrupt:
        logger.info("🧩 Execução interrompida manualmente pelo usuário. 🛑 Encerrando com segurança...")
 
if __name__ == "__main__":
    main()
