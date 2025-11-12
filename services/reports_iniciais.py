# services/reports_agendamentos.py

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains

from datetime import datetime
import time

def _abrir_dialog_excel(driver, wait):
    """
    Abre o diálogo de exportação para Excel e muda para o iframe.
    Aguarda até o iframe real ser carregado (src válido), mesmo que demore vários minutos.
    """
    try:
        # Aguarda o botão Excel aparecer
        btn_excel = WebDriverWait(driver, 120).until(
            EC.element_to_be_clickable((By.ID, "btnExcel"))
        )
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn_excel)
        time.sleep(0.5)
        driver.execute_script("arguments[0].click();", btn_excel)
        print("📥 Botão Excel clicado. Aguardando diálogo abrir...")

        # Detecta o diálogo
        dialog = WebDriverWait(driver, 300).until(
            EC.presence_of_element_located((By.ID, "btnExcel_dlg"))
        )
        print("🪟 Diálogo Excel detectado: #btnExcel_dlg")

        # Espera o iframe real ser carregado
        iframe = None
        max_wait = 600  # até 10 minutos
        step = 10
        elapsed = 0

        while elapsed < max_wait:
            try:
                iframe = dialog.find_element(By.TAG_NAME, "iframe")
                src = iframe.get_attribute("src") or ""
                if "elawReportGerarDialog.elaw" in src and src.strip() != "":
                    print(f"📄 Iframe detectado com src válido após {elapsed}s.")
                    break
            except Exception:
                pass
            time.sleep(step)
            elapsed += step
            print(f"⏳ Aguardando iframe carregar ({elapsed}/{max_wait}s)...")

        if not iframe:
            raise Exception("Iframe do diálogo Excel não apareceu dentro do tempo limite.")

        # Agora muda pro iframe
        driver.switch_to.frame(iframe)
        print("🔄 Mudamos para o iframe do relatório com sucesso.")

    except Exception as e:
        raise Exception(f"❌ Falha ao abrir diálogo Excel: {e}")

def _configurar_modelo(driver, wait):
    """Seleciona modelo pré-configurado e relatório 'Tarefas'."""
    try:
        lbl = wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//label[@for='elawReportForm:elawReportOption:0']"))
        )
        lbl.click()
        print("☑️ Selecionado: Modelos pré-configurados")

        btn_continuar = wait.until(EC.element_to_be_clickable((By.ID, "elawReportForm:continuarBtn")))
        btn_continuar.click()
        print("➡️ Continuar clicado.")

        # Dropdown de relatórios
        dd = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "[id$='selectElawReport_label']")))
        dd.click()

        opcoes = WebDriverWait(driver, 20).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "ul[id$='selectElawReport_items'] li"))
        )
        time.sleep(1)

        alvo = next((o for o in opcoes if o.text.strip().lower() == "tarefas"), None)
        if not alvo:
            raise Exception("❌ Opção 'Tarefas' não encontrada no dropdown!")

        wait.until(EC.element_to_be_clickable(alvo)).click()
        print("✔️ Relatório selecionado: Tarefas")

        btn_gerar = wait.until(EC.element_to_be_clickable((By.ID, "elawReportForm:elawReportGerarBtn")))
        btn_gerar.click()
        print("📊 Gerar relatório clicado.")
    except Exception as e:
        raise Exception(f"❌ Falha ao configurar modelo de relatório: {e}")


def _capturar_id(driver, wait):
    """Captura o ID do relatório gerado."""
    try:
        id_elem = wait.until(EC.presence_of_element_located((
            By.XPATH, "//span[normalize-space()='ID']/ancestor::div[contains(@class,'ui-g')]/div[last()]"
        )))
        relatorio_id = id_elem.text.strip()
        print(f"🆔 Relatório solicitado com ID: {relatorio_id}")
        return relatorio_id
    except Exception as e:
        raise Exception(f"❌ Falha ao capturar ID do relatório: {e}")

def gerar_relatorio(driver):
    """
    Gera o relatório de agendamentos (Tarefas Concluídas e Concluídas em atraso)
    com pausas e lógica robusta de seleção.
    """
    wait = WebDriverWait(driver, 30)
    url = "https://sicredi.elaw.com.br/agendamentoContenciosoList.elaw"
    driver.get(url)
    time.sleep(2)
    print("📄 Página de Agendamentos carregada.")

    # 🗓️ Preencher datas
    hoje = datetime.now()
    data_inicial = datetime(hoje.year, 1, 1).strftime("%d/%m/%Y 00:00")
    data_final = hoje.strftime("%d/%m/%Y 23:59")

    campo_data_ini = wait.until(EC.presence_of_element_located((By.ID, "tabSearchTab:dataFrom_input")))
    campo_data_fim = wait.until(EC.presence_of_element_located((By.ID, "tabSearchTab:dataTo_input")))

    campo_data_ini.clear()
    #campo_data_ini.send_keys(data_final)
    campo_data_ini.send_keys(data_inicial)
    campo_data_fim.clear()
    campo_data_fim.send_keys(data_final)
   
    print(f"🗓️ Período definido: {data_inicial} → {data_final}")
    time.sleep(2)

    # FECHA o datepicker de forma garantida ANTES de qualquer outra interação
    _ok = _fechar_datepicker(driver, wait)
    if not _ok:
        print("⚠️ Aviso: datepicker pode ainda estar visível, seguindo com fallback...")

    time.sleep(1)

    # ☑️ Marcar "Tarefa" clicando no label (após garantir overlay fechado)
    try:
        label_tarefa = wait.until(EC.element_to_be_clickable((By.XPATH, "//label[normalize-space()='Tarefa']")))
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", label_tarefa)
        time.sleep(0.5)
        driver.execute_script("arguments[0].click();", label_tarefa)
        print("☑️ Checkbox 'Tarefa' marcado com sucesso.")
    except Exception as e:
        print(f"⚠️ Falha ao marcar 'Tarefa': {e}")

    time.sleep(2)

     # 🔹 Fecha janela "Escolher colunas" se estiver aberta
    try:
        dialogo = WebDriverWait(driver, 3).until(
            EC.presence_of_element_located((By.ID, "escolherColumnDialog"))
        )
        if dialogo.is_displayed():
            print("🪟 Janela 'Escolher colunas' detectada — fechando...")
            btn_fechar = dialogo.find_element(By.CSS_SELECTOR, "a.ui-dialog-titlebar-close")
            driver.execute_script("arguments[0].click();", btn_fechar)
            time.sleep(1)
            print("✅ Janela 'Escolher colunas' fechada com sucesso.")
    except Exception:
        pass

        
    # --- STATUS: abrir pelo triângulo, limpar tokens, marcar 1, 3 e 4 com scroll interno e fechar no X ---
    try:
        print("⏳ Abrindo seletor de status...")
        # 1) abre pelo triângulo (seta)
        tri = wait.until(EC.element_to_be_clickable((
            By.CSS_SELECTOR, "#tabSearchTab\\:status .ui-icon-triangle-1-s"
        )))
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", tri)
        time.sleep(0.4)
        tri.click()
        print("📂 Painel de status aberto pela seta.")
        time.sleep(1)

        # 2) limpa tokens (Pendentes etc.) fora do painel
        close_icons = driver.find_elements(
            By.CSS_SELECTOR, "#tabSearchTab\\:status .ui-selectcheckboxmenu-token-icon"
        )
        for icon in close_icons:
            try:
                driver.execute_script("arguments[0].click();", icon)
                time.sleep(0.2)
            except Exception:
                pass
        print("🔄 Tokens anteriores removidos.")
        time.sleep(0.5)

        # 3) garante painel visível e pega o wrapper de itens (área rolável)
        panel = wait.until(EC.visibility_of_element_located(
            (By.ID, "tabSearchTab:status_panel")
        ))
        wrapper = panel.find_element(By.CSS_SELECTOR, ".ui-selectcheckboxmenu-items-wrapper")

        # helper JS: rola até o li e clica no .ui-chkbox-box via JS (evita not interactable)
        js_click_by_value = """
            (function(panel, value){
                const li = panel.querySelector("li.ui-selectcheckboxmenu-item[data-item-value='" + value + "']");
                if (!li) return "LI_NAO_ENCONTRADO:" + value;
                const box = li.querySelector(".ui-chkbox-box");
                if (!box) return "BOX_NAO_ENCONTRADO:" + value;
                const wrapper = panel.querySelector(".ui-selectcheckboxmenu-items-wrapper");
                if (wrapper && li.offsetTop != null) {
                    wrapper.scrollTop = li.offsetTop - 10;
                }
                // forçar reflow antes do clique
                box.getBoundingClientRect();
                box.click();
                return "OK:" + value;
            })(arguments[0], arguments[1]);
        """

         # 4) marca “Atrasadas” (4), “A vencer” (8) e “Pendentes” (1)
        for value in ["4", "8", "1"]:
            res = driver.execute_script(js_click_by_value, panel, value)
            print(f"🧪 Clique em data-item-value={value}: {res}")
            time.sleep(0.5)

        # 5) valida visualmente: tokens devem aparecer no container de tokens
        tokens_text = [el.text.strip() for el in driver.find_elements(
            By.CSS_SELECTOR, "#tabSearchTab\\:status .ui-selectcheckboxmenu-token-label"
        )]
        print(f"🔍 Tokens atuais: {tokens_text}")
        if not all(x in tokens_text for x in ["Atrasadas", "A vencer", "Pendentes"]):
            # fallback extra: tenta clicar pelos labels -> .ui-chkbox-box anterior ao label
            for nome in ["Atrasadas", "A vencer", "Pendentes"]:
                try:
                    lbl = panel.find_element(By.XPATH, f".//label[normalize-space()='{nome}']")
                    box = lbl.find_element(By.XPATH, "./preceding-sibling::div[contains(@class,'ui-chkbox')]/div")
                    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", box)
                    time.sleep(0.2)
                    driver.execute_script("arguments[0].click();", box)
                    print(f"↪️ Fallback: box de '{nome}' clicado.")
                    time.sleep(0.4)
                except Exception:
                    pass

            tokens_text = [el.text.strip() for el in driver.find_elements(
                By.CSS_SELECTOR, "#tabSearchTab\\:status .ui-selectcheckboxmenu-token-label"
            )]
            print(f"🔁 Tokens após fallback: {tokens_text}")
            
        # 6) fecha no X do painel
        fechar = panel.find_element(By.CSS_SELECTOR, ".ui-icon-circle-close")
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", fechar)
        time.sleep(0.2)
        fechar.click()
        print("📁 Painel de status fechado (X).")

    except Exception as e:
        print(f"⚠️ Falha ao manipular status: {e}")


    time.sleep(2)

        # 🔎 Clicar em "Pesquisar" após o painel de status
    try:
        time.sleep(1.5)  # aguarda painel fechar visualmente
        btn_pesquisar = wait.until(EC.element_to_be_clickable((By.ID, "tabSearchTab:btnPesquisar")))
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn_pesquisar)
        time.sleep(0.5)
        btn_pesquisar.click()
        print("🔎 Botão 'Pesquisar' clicado com sucesso.")
    except Exception as e:
        print(f"⚠️ Falha ao clicar em 'Pesquisar': {e}")

    # ⏳ Aguardar tabela carregar
    try:
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "table[id*='dataTable']")))
        print("✅ Resultados carregados com sucesso.")
    except Exception:
        print("⚠️ Não foi possível confirmar o carregamento da tabela.")

    time.sleep(2)

    # ⏳ Aguardar resultados
    try:
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "table[id*='dataTable']")))
        print("✅ Resultados carregados com sucesso.")
    except Exception:
        print("⚠️ Não foi possível confirmar o carregamento da tabela.")
    time.sleep(2)

    # 📥 Excel + geração de relatório
    _abrir_dialog_excel(driver, wait)
    time.sleep(2)
    _configurar_modelo(driver, wait)
    time.sleep(2)
    relatorio_id = _capturar_id(driver, wait)

    # 🔚 Finaliza execução com segurança
    driver.switch_to.default_content()
    print(f"🆔 Relatório solicitado com ID: {relatorio_id}")
    print("✅ Fluxo concluído com sucesso (sem refresh).")

    return relatorio_id

def _fechar_datepicker(driver, wait, tentativas=3):
    """
    Fecha overlays de datepicker do PrimeFaces de forma robusta.
    Tenta: ESC, blur + esconder via JS, clique fora com ActionChains.
    Só retorna quando não houver datepicker visível.
    """
    for _ in range(tentativas):
        # 1) ESC no elemento ativo e no body
        try:
            driver.switch_to.default_content()
            driver.switch_to.active_element.send_keys(Keys.ESCAPE)
        except Exception:
            pass
        try:
            body = driver.find_element(By.TAG_NAME, "body")
            body.send_keys(Keys.ESCAPE)
        except Exception:
            pass

        # 2) blur + esconder overlays via JS
        try:
            driver.execute_script("""
                if (document.activeElement) document.activeElement.blur();
                var hide = el => { if (!el) return; el.style.display = 'none'; el.classList.add('force-hidden'); };
                var els = Array.from(document.querySelectorAll('.ui-datepicker, .ui-datepicker-div, .ui-input-overlay'));
                els.forEach(hide);
            """)
        except Exception:
            pass

        # 3) clique fora (canto superior esquerdo seguro)
        try:
            body = driver.find_element(By.TAG_NAME, "body")
            ActionChains(driver).move_to_element_with_offset(body, 10, 10).click().perform()
        except Exception:
            pass

        # 4) checa se ainda há overlays visíveis
        try:
            visiveis = driver.execute_script("""
                return Array.from(document.querySelectorAll('.ui-datepicker, .ui-datepicker-div, .ui-input-overlay'))
                    .some(e => {
                        const st = window.getComputedStyle(e);
                        return st.display !== 'none' && st.visibility !== 'hidden' && e.offsetWidth > 0 && e.offsetHeight > 0;
                    });
            """)
            if not visiveis:
                return True
        except Exception:
            return True

        time.sleep(0.5)

    return False

def _safe_refresh(driver, retries=3, delay=15):
    for i in range(retries):
        try:
            driver.switch_to.default_content()
            driver.refresh()
            print("🔄 Página recarregada com sucesso.")
            return
        except Exception as e:
            print(f"⚠️ Falha ao atualizar (tentativa {i+1}/{retries}): {e}")
            time.sleep(delay)
    raise Exception("❌ Não foi possível atualizar a página após várias tentativas.")

