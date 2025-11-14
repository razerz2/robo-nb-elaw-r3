import time
import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from config import USER, PASSWORD, URL_INICIAL, URL_LOGOUT

def login(driver, timeout=30):
    driver.get(URL_INICIAL)
    wait = WebDriverWait(driver, timeout)

    # Espera os campos corretos da tela de login
    usuario = wait.until(EC.presence_of_element_located((By.ID, "fieldUser")))
    senha   = wait.until(EC.presence_of_element_located((By.ID, "fieldPassword")))

    usuario.clear()
    usuario.send_keys(USER)
    senha.clear()
    senha.send_keys(PASSWORD)
    senha.submit()  # equivale ao pressionar Enter

    # Espera até a URL mudar para o painel
    wait.until(lambda d: "processoView.elaw" in d.current_url or "homePage.elaw" in d.current_url)

    return True

def logout(driver):
    driver.get(URL_LOGOUT)
    time.sleep(2)
    logging.info("↩️ Logout executado.")

def is_logged_in(driver):
    try:
        # VERIFICA ALGO QUE SÓ EXISTE QUANDO LOGADO
        driver.find_element(By.ID, "menu-relatorios") # exemplo
        return True
    except:
        return False

