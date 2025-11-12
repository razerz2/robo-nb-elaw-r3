# services/relatorios.py

import os
import time
import shutil
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, ElementClickInterceptedException
from services.utils import esperar_download
from config import INTERVALO_BAIXAR as CFG_INTERVALO, OUTPUT_NAME as CFG_NOME
from pathlib import Path


def baixar_relatorio(driver, relatorio_id, pasta_final, nome_arquivo=None, intervalo_baixar=None):
    """
    Acessa 'Meus relatórios', pesquisa e baixa o relatório pelo ID fornecido.
    Caso o arquivo ainda não esteja pronto, refaz TODO o processo a cada X minutos.
    O arquivo é baixado localmente e movido para o diretório final (sobrescrevendo se existir).

    Parâmetros:
        driver            -> instância ativa do WebDriver
        relatorio_id      -> ID do relatório a baixar
        pasta_final       -> diretório destino do arquivo
        nome_arquivo      -> nome final opcional (default = OUTPUT_NAME do config)
        intervalo_baixar  -> tempo em minutos entre tentativas (default = INTERVALO_BAIXAR do config)
    """
    wait = WebDriverWait(driver, 30)

    # Defaults vindos do config, se não forem passados
    nome_arquivo = nome_arquivo or CFG_NOME
    intervalo_baixar = intervalo_baixar or CFG_INTERVALO

    # Cria pasta temporária para download local
    pasta_temp = Path(os.getcwd()) / "downloads_temp"
    pasta_temp.mkdir(parents=True, exist_ok=True)

    while True:
        try:
            # 1️⃣ Vai para a página inicial após login
            driver.get("https://sicredi.elaw.com.br/processoView.elaw")
            time.sleep(3)

            # 2️⃣ Abre o menu da maleta
            menu_btn = wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//li[@class='notifications-item']//i[contains(@class,'pi-briefcase')]/..")
                )
            )
            menu_btn.click()
            time.sleep(2)

            # 3️⃣ Clica em "Meus relatórios"
            meus_relatorios = wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//a[starts-with(@href,'userElawReportRequestList.elaw?faces-redirect=true&etoken=')]")
                )
            )
            driver.execute_script("arguments[0].click();", meus_relatorios)
            print("📂 Acessando 'Meus relatórios'...")
            time.sleep(2)

            # 4️⃣ Clica em "Pesquisar"
            btn_pesquisar = wait.until(EC.element_to_be_clickable((By.ID, "btnPesquisar")))
            driver.execute_script("arguments[0].click();", btn_pesquisar)
            print("🔎 Pesquisa disparada.")
            time.sleep(3)

            # 5️⃣ Procura o relatório na tabela
            tabela = wait.until(EC.presence_of_element_located((By.ID, "tableElawReportRequest_data")))
            linhas = tabela.find_elements(By.TAG_NAME, "tr")

            alvo = None
            for linha in linhas:
                colunas = linha.find_elements(By.TAG_NAME, "td")
                if len(colunas) > 3 and colunas[3].text.strip() == relatorio_id:
                    alvo = linha
                    break

            if not alvo:
                raise Exception(f"❌ Relatório com ID {relatorio_id} não encontrado na lista.")

            # 6️⃣ Verifica se o link de download está disponível
            try:
                link_download = alvo.find_element(By.CSS_SELECTOR, "td:nth-child(3) a")
                driver.execute_script("arguments[0].click();", link_download)
                print(f"📥 Download iniciado para relatório ID {relatorio_id}")

                # 7️⃣ Espera o download terminar e verifica se o arquivo foi realmente salvo
                arquivo_baixado = esperar_download(pasta_temp, nome_arquivo)

                if not arquivo_baixado or not os.path.exists(arquivo_baixado):
                    raise FileNotFoundError(f"Arquivo {nome_arquivo} não foi encontrado após o download.")

                # 8️⃣ Move para o diretório final (sobrescreve se existir)
                destino_final = os.path.join(pasta_final, nome_arquivo)
                if os.path.exists(destino_final):
                    os.remove(destino_final)

                shutil.move(arquivo_baixado, destino_final)
                print(f"✅ Arquivo movido e sobrescrito em: {destino_final}")
                break  # 🔹 Download concluído, encerra o loop

            except NoSuchElementException:
                print(f"⏳ Relatório {relatorio_id} ainda não está pronto. "
                    f"Tentando novamente em {intervalo_baixar} minutos...")
                time.sleep(intervalo_baixar * 60)
                continue

            except ElementClickInterceptedException:
                print(f"⚠️ O botão de download está visível, mas não clicável ainda. "
                    f"Nova tentativa em {intervalo_baixar} minutos...")
                time.sleep(intervalo_baixar * 60)
                continue

            except Exception as e:
                print(f"⚠️ Erro inesperado ao baixar relatório {relatorio_id}: {type(e).__name__} → {e}")
                time.sleep(intervalo_baixar * 60)
                continue

        except Exception as e:
            print(f"⚠️ Erro durante tentativa de download: {e}")
            print(f"🔁 Repetindo processo em {intervalo_baixar} minutos...")
            time.sleep(intervalo_baixar * 60)

    print("✅ Download solicitado e concluído com sucesso.")
