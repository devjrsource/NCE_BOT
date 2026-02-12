import os
import sys
import time
from datetime import datetime
from typing import Optional, Tuple

try:
    import pyautogui
except ImportError:
    print(
        "[ERRO] Biblioteca 'pyautogui' não encontrada.\n"
        "Instale com: pip install pyautogui opencv-python pillow\n"
    )
    sys.exit(1)


ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")

# Ajustes globais de segurança / performance
pyautogui.FAILSAFE = True  # mover mouse pro canto superior esquerdo aborta o script
pyautogui.PAUSE = 0.1      # pequeno delay entre ações para evitar excesso de eventos


def log(msg: str) -> None:
    """Log simples com timestamp."""
    now = datetime.now().strftime("%H:%M:%S")
    print(f"[{now}] {msg}")


def asset_path(filename: str) -> str:
    path = os.path.join(ASSETS_DIR, filename)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Asset não encontrado: {path}")
    return path


def wait_for_image(
    filename: str,
    timeout: float = 10.0,
    confidence: float = 0.7,
    region: Optional[Tuple[int, int, int, int]] = None,
) -> Optional[Tuple[int, int, int, int]]:
    """
    Espera até 'timeout' segundos pela aparição de uma imagem na tela.

    Retorna a bounding box (left, top, width, height) ou None se não encontrou.
    """
    img_path = asset_path(filename)
    end_time = time.time() + timeout

    while time.time() < end_time:
        try:
            box = pyautogui.locateOnScreen(
                img_path,
                confidence=confidence,
                region=region,
            )
        except Exception as e:  # erros de screenshot / backend gráfico
            log(f"[WARN] Erro ao localizar '{filename}': {e}")
            box = None

        if box is not None:
            return box

        time.sleep(0.2)  # evita busy-wait

    return None


def click_image(
    filename: str,
    button: str = "left",
    clicks: int = 1,
    timeout: float = 10.0,
    confidence: float = 0.7,
) -> bool:
    """
    Espera a imagem aparecer e clica no centro dela.

    Retorna True se clicou, False se não encontrou no timeout.
    """
    log(f"Procurando '{filename}' para clicar com botão {button}...")
    box = wait_for_image(filename, timeout=timeout, confidence=confidence)
    if box is None:
        log(f"[ERRO] Imagem '{filename}' não encontrada em {timeout:.1f}s.")
        return False

    center = pyautogui.center(box)
    log(f"Imagem '{filename}' encontrada em {center}, realizando clique.")
    pyautogui.click(center.x, center.y, clicks=clicks, button=button)
    return True


def wait_for_optional_image(
    filename: str,
    timeout: float = 3.0,
    confidence: float = 0.7,
) -> Optional[Tuple[int, int, int, int]]:
    """
    Espera até 'timeout' pela imagem. Se não aparecer, retorna None silenciosamente.
    """
    box = wait_for_image(filename, timeout=timeout, confidence=confidence)
    if box is None:
        log(f"Imagem opcional '{filename}' NÃO apareceu em {timeout:.1f}s.")
    else:
        log(f"Imagem opcional '{filename}' detectada.")
    return box


def process_single_item() -> None:
    """
    Executa o fluxo completo para UM item da lista (uma ONU).

    Fluxo:
    1. Right-click em 'onu_selected.png'
    2. Left-click em 'configure_onu_menu.png'
    3. Left-click em 'access_control_menu.png'
    4. Left-click em 'enable_radio_input.png'
    5. Left-click em 'ok_button.png'
    6. Left-click em 'final_ok_button.png'
    7. Left-click em 'security_ok_button.png'
    8. Se aparecer 'err_modal.png':
           - Left-click em 'close.png'
           - Left-click em 'cancel_button.png'
       Se NÃO aparecer:
           - Considera sucesso.
    9. Espera 1.5s e tecla "down" para ir ao próximo item.
    """
    # 1. ONU selecionada (right-click)
    if not click_image("onu_selected.png", button="right", timeout=8):
        log("Abortando item atual: não conseguiu encontrar 'onu_selected.png'.")
        return

    # 2. Configurar ONU
    if not click_image("configure_onu_menu.png", button="left", timeout=8):
        log("Abortando item atual: 'configure_onu_menu.png' não apareceu.")
        return

    # 3. Menu Access Control
    if not click_image("access_control_menu.png", button="left", timeout=8):
        log("Abortando item atual: 'access_control_menu.png' não apareceu.")
        return

    # 4. Habilitar rádio/input
    if not click_image("enable_radio_input.png", button="left", timeout=8):
        log("Abortando item atual: 'enable_radio_input.png' não apareceu.")
        return

    # 5. OK
    if not click_image("ok_button.png", button="left", timeout=8):
        log("Abortando item atual: 'ok_button.png' não apareceu.")
        return

    # 6. Final OK
    if not click_image("final_ok_button.png", button="left", timeout=8):
        log("Abortando item atual: 'final_ok_button.png' não apareceu.")
        return

    # 7. Security OK
    if not click_image("security_ok_button.png", button="left", timeout=8):
        log("Abortando item atual: 'security_ok_button.png' não apareceu.")
        return

    # 8. Verifica se apareceu modal de erro
    err_box = wait_for_optional_image("err_modal.png", timeout=3.0, confidence=0.9)

    if err_box is not None:
        log("Fluxo de ERRO: modal de erro detectado.")

        if not click_image("close.png", button="left", timeout=5):
            log("[WARN] 'close.png' não encontrado após err_modal. Tentando seguir mesmo assim.")

        if not click_image("cancel_button.png", button="left", timeout=5):
            log("[WARN] 'cancel_button.png' não encontrado após err_modal.")
    else:
        log("Fluxo de SUCESSO: nenhum modal de erro detectado após 'security_ok_button'.")

    # 9. Avança para próximo item
    log("Esperando 1.5s antes de avançar para o próximo item...")
    time.sleep(1.5)
    log("Pressionando seta para baixo para ir ao próximo item da lista.")
    pyautogui.press("down")


def main_loop() -> None:
    """
    Loop principal: processa itens indefinidamente até Ctrl+C.
    """
    log("Iniciando loop principal de processamento de ONUs.")
    log("Use Ctrl+C ou mova o mouse rapidamente para o canto superior esquerdo para interromper (FAILSAFE).")

    item_index = 1
    try:
        while True:
            log(f"========== Processando item #{item_index} ==========")
            process_single_item()
            item_index += 1
    except KeyboardInterrupt:
        log("Execução interrompida pelo usuário (Ctrl+C).")


if __name__ == "__main__":
    main_loop()





