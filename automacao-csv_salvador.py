import os
import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from webdriver_manager.chrome import ChromeDriverManager
import ddddocr 
from dotenv import load_dotenv
load_dotenv()  # lê o .env local (não vai para o GitHub)

# =============================================================================
# CONFIGURAÇÕES INICIAIS
# =============================================================================
CAMINHO_PLANILHA = os.getenv("CAMINHO_PLANILHA")
BASE_DIR_DOWNLOAD = os.getenv("BASE_DIR_DOWNLOAD")
NOME_DA_ABA = "032026"

ocr = ddddocr.DdddOcr(show_ad=False)

def limpar_arquivos_temporarios():
    """Remove a foto do captcha e o arquivo de IA do DdddOcr após o uso."""
    print("\n🧹 Limpando arquivos temporários (faxina)...")
    arquivos_para_apagar = ["captcha.png", "common_old.onnx"]
    
    for arquivo in arquivos_para_apagar:
        try:
            if os.path.exists(arquivo):
                os.remove(arquivo)
                print(f"  -> Apagado: {arquivo}")
        except Exception as e:
            pass # Ignora silenciosamente se o arquivo já não existir ou estiver bloqueado

def resolver_captcha(driver):
    try:
        wait = WebDriverWait(driver, 1)
        
        try:
            captcha_img = driver.find_element(By.CSS_SELECTOR, "img[src*='aptcha'], img[src*='APTCHA']")
        except:
            xpath_imagem = "//input[@id='tbCaptcha']/preceding::img[1]"
            captcha_img = wait.until(EC.presence_of_element_located((By.XPATH, xpath_imagem)))
        
        time.sleep(10) 
        
        caminho_imagem = "captcha.png"
        captcha_img.screenshot(caminho_imagem)
        
        with open(caminho_imagem, 'rb') as f:
            img_bytes = f.read()
            
        texto_captcha = ocr.classification(img_bytes)
        
        texto_limpo = ''.join(e for e in texto_captcha if e.isalnum()).upper()
        return texto_limpo
    except Exception as e:
        print(f"  -> Erro interno ao processar captcha: {e}")
        return ""

def iniciar_navegador(pasta_download):
    chrome_options = Options()
    prefs = {
        "download.default_directory": pasta_download,
        "download.prompt_for_download": False,
        "directory_upgrade": True,
        "safebrowsing.enabled": True
    }
    chrome_options.add_experimental_option("prefs", prefs)
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    driver.maximize_window()
    time.sleep(1)
    return driver

# =============================================================================
# EXECUÇÃO PRINCIPAL
# =============================================================================
def main():
    print(f"Lendo a aba '{NOME_DA_ABA}' da planilha...")
    try:
        df = pd.read_excel(CAMINHO_PLANILHA, sheet_name=NOME_DA_ABA)
        df = df.astype(object) 
    except FileNotFoundError:
        print(f"\nERRO CRÍTICO: Planilha não encontrada em:\n{CAMINHO_PLANILHA}")
        return
    
    mes_filtro = str(int(NOME_DA_ABA[:2]))
    ano_filtro = NOME_DA_ABA[2:]

    for index, row in df.iterrows():
        empresa = str(row.iloc[0]).strip()
        cnpj = str(row.iloc[1]).strip()
        senha = str(row.iloc[7]).strip()
        
        if pd.isna(empresa) or empresa == 'nan' or pd.isna(cnpj) or cnpj == 'nan':
            continue

        print(f"\nIniciando processamento: {empresa} - CNPJ: {cnpj}")
        
        pasta_empresa = os.path.join(BASE_DIR_DOWNLOAD, empresa)
        os.makedirs(pasta_empresa, exist_ok=True)
        
        driver = iniciar_navegador(pasta_empresa)
        sucesso_login = False
        wait = WebDriverWait(driver, 10)
        
        try:
            driver.get("https://nfse.salvador.ba.gov.br/")
            
            campo_login = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input#txtLogin")))
            campo_login.clear()
            campo_login.send_keys(cnpj)
            
            campo_senha = driver.find_element(By.CSS_SELECTOR, "input#txtSenha")
            campo_senha.clear()
            campo_senha.send_keys(senha)
            
            for tentativa in range(1, 31):
                if tentativa > 1:
                    print(f"  -> {tentativa}ª tentativa: Solicitando nova imagem de captcha...")
                    try:
                        btn_recarregar = driver.find_element(By.XPATH, "//*[contains(text(), 'Recarregar')] | //img[contains(@src, 'reload') or contains(@title, 'Recarregar')]")
                        btn_recarregar.click()
                        time.sleep(1.5)
                    except:
                        print("  -> Não encontrou o botão 'Recarregar'.")
                
                texto_captcha = resolver_captcha(driver)
                
                if len(texto_captcha) != 5:
                    print(f"  -> Descartado: '{texto_captcha}' (não tem 5 dígitos exatos).")
                    continue
                
                print(f"  -> Testando a combinação: '{texto_captcha}'...")
                
                campo_captcha = driver.find_element(By.CSS_SELECTOR, "input#tbCaptcha")
                campo_captcha.clear()
                campo_captcha.send_keys(texto_captcha)
                
                driver.find_element(By.CSS_SELECTOR, "input#cmdLogin").click()
                time.sleep(3) 
                
                url_atual = driver.current_url
                if "InformacaoDebito.aspx" in url_atual or "Default.aspx" in url_atual or len(driver.find_elements(By.XPATH, "//a[contains(text(), 'Sair')]")) > 0:
                    sucesso_login = True
                    print("  -> Login realizado com sucesso!")
                    break
                else:
                    print("  -> Login barrado (OCR errou alguma letra).")
                    
                    try:
                        check_cnpj = driver.find_element(By.CSS_SELECTOR, "input#txtLogin")
                        if not check_cnpj.get_attribute('value'):
                            check_cnpj.send_keys(cnpj)
                            
                        check_senha = driver.find_element(By.CSS_SELECTOR, "input#txtSenha")
                        if not check_senha.get_attribute('value'):
                            check_senha.send_keys(senha)
                    except:
                        pass
            
            if not sucesso_login:
                df.at[index, df.columns[8]] = "Erro: Vencido pelo Captcha após 30 tentativas"
                print(f"  -> Falha definitiva no login para {empresa}. Pulando para a próxima...")
                driver.quit()
                continue
                
            # --- Fluxo de Exportação Pós-Login ---
            if "InformacaoDebito.aspx" in driver.current_url:
                wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Acessar Nota Salvador')]"))).click()
                
            wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "a[href*='nota/consulta.aspx']"))).click()
            
            select_ano = Select(wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "select#ddlExercicio"))))
            select_ano.select_by_visible_text(ano_filtro)
            
            select_mes = Select(driver.find_element(By.CSS_SELECTOR, "select#ddlMes"))
            select_mes.select_by_visible_text(mes_filtro)
            
            janela_principal = driver.current_window_handle
            driver.find_element(By.CSS_SELECTOR, "input#btEmitidas").click()
            print("  -> Aguardando a tela do Pop-up...")
            
            # 1. Verifica se abriu nova janela ou iframe
            try:
                WebDriverWait(driver, 5).until(EC.number_of_windows_to_be(2))
                for window_handle in driver.window_handles:
                    if window_handle != janela_principal:
                        driver.switch_to.window(window_handle)
                        break
                print("  -> Pop-up detectado como uma nova janela.")
            except:
                print("  -> Procurando o pop-up dentro da própria página (Iframe)...")
                try:
                    iframe = wait.until(EC.presence_of_element_located((By.TAG_NAME, "iframe")))
                    driver.switch_to.frame(iframe)
                except:
                    print("  -> Nenhum iframe achado. Prosseguindo na tela principal...")

            # 2. Busca dinâmica da caixa de seleção do CSV
            print("  -> Procurando a opção CSV...")
            xpath_select = "//select[.//option[contains(translate(text(), 'csv', 'CSV'), 'CSV')]]"
            select_element = wait.until(EC.presence_of_element_located((By.XPATH, xpath_select)))
            select_tipo = Select(select_element)
            
            for opt in select_tipo.options:
                if "CSV" in opt.text.upper():
                    opt.click()
                    break
            
            # 3. Busca dinâmica do botão de Exportar
            print("  -> Clicando em Exportar...")
            xpath_btn = "//*[(self::input or self::button or self::a) and (contains(translate(@value, 'exportar', 'EXPORTAR'), 'EXPORTAR') or contains(translate(text(), 'exportar', 'EXPORTAR'), 'EXPORTAR') or contains(translate(@value, 'gerar', 'GERAR'), 'GERAR'))]"
            driver.find_element(By.XPATH, xpath_btn).click()
            print("  -> Download iniciado...")
            
            # 4. Aguardar o download concluir na pasta da empresa
            tempo_espera = 0
            download_concluido = False
            while tempo_espera < 30:
                arquivos = os.listdir(pasta_empresa)
                if any(arq.endswith('.csv') for arq in arquivos) and not any(arq.endswith('.crdownload') for arq in arquivos):
                    download_concluido = True
                    break
                time.sleep(1)
                tempo_espera += 1
                
            if download_concluido:
                df.at[index, df.columns[8]] = "Gerado com sucesso"
                print(f"  -> Sucesso: Arquivo salvo na pasta.")
            else:
                df.at[index, df.columns[8]] = "Erro no Download (timeout)"
                print("  -> Erro: O arquivo não baixou a tempo.")
                
            driver.close()
            driver.switch_to.window(janela_principal)
            
        except Exception as e:
            df.at[index, df.columns[8]] = f"Erro na navegação interna: {str(e)[:50]}"
            print(f"  -> Erro crítico na execução: {e}")
            
        finally:
            try:
                driver.quit()
            except:
                pass 

    print("\nSalvando status na planilha Excel...")
    try:
        with pd.ExcelWriter(CAMINHO_PLANILHA, engine="openpyxl", mode="a", if_sheet_exists="replace") as writer:
            df.to_excel(writer, sheet_name=NOME_DA_ABA, index=False)
        print("Automação finalizada! Planilha atualizada.")
    except PermissionError:
         print("ERRO AO SALVAR: Feche o arquivo Excel.")
    except Exception as e:
        print(f"Falhou ao salvar o Excel. Erro: {e}")
        
    # Aciona a faxina final
    limpar_arquivos_temporarios()

if __name__ == "__main__":
    main()