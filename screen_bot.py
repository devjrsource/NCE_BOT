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

# Windows: envia tecla via WinAPI para ser o mais próximo possível de um teclado físico
IS_WINDOWS = sys.platform.startswith("win")

if IS_WINDOWS:
    try:
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.WinDLL("user32", use_last_error=True)
        KEYEVENTF_KEYUP = 0x0002
        VK_DOWN = 0x28

        def _press_key_vk(vk: int) -> None:
            """Envia uma tecla virtual via WinAPI (key down + key up)."""
            user32.keybd_event(vk, 0, 0, 0)
            time.sleep(0.05)
            user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, 0)

    except Exception as e:
        # Se der problema com WinAPI, apenas loga; cairemos no fallback do pyautogui
        print(f"[WARN] Falha ao inicializar WinAPI: {e}")
        IS_WINDOWS = False


def press_down_key() -> None:
    """
    Pressiona a tecla para baixo.

    - Em Windows, tenta usar WinAPI (keybd_event) para simular a tecla no nível do sistema.
    - Em outras plataformas, usa pyautogui (keyDown/keyUp).
    """
    if IS_WINDOWS:
        log("Enviando tecla DOWN via WinAPI.")
        _press_key_vk(VK_DOWN)  # type: ignore[name-defined]
    else:
        log("Enviando tecla DOWN via pyautogui.")
        pyautogui.keyDown("down")
        time.sleep(0.05)
        pyautogui.keyUp("down")


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
    timeout: float = 1.0,
    confidence: float = 0.7,
) -> Optional[Tuple[int, int, int, int]]:
    """
    Espera até 'timeout' pela imagem. Se não aparecer, retorna None silenciosamente.
    """
    box = wait_for_image(filename, timeout=timeout, confidence=confidence)
    if box is None:
        return None
    return box


def handle_error_modal() -> None:
    """
    Monitora continuamente a tela por um modal de erro e, quando aparecer,
    executa automaticamente os cliques de fechamento.

    Fluxo:
    - Fica em loop procurando 'err_modal.png'.
    - Quando encontrar:
        - Clica em 'close.png'.
        - Clica em 'cancel_button.png'.
        - Aguarda desaparecer o modal de erro antes de voltar a monitorar.
    """
    log("Iniciando monitor de modal de erro.")
    log("Use Ctrl+C ou mova o mouse rapidamente para o canto superior esquerdo para interromper (FAILSAFE).")

    try:
        while True:
            # Checa rapidamente se o modal de erro apareceu
            box = wait_for_optional_image("err_modal.png", timeout=0.5, confidence=0.7)
            if box is None:
                # Nada na tela, volta a checar
                continue

            log("Modal de erro detectado ('err_modal.png'). Iniciando sequência de fechamento.")

            # Tenta clicar no botão de fechar
            if not click_image("close.png", button="left", timeout=3, confidence=0.7):
                log("[WARN] Não foi possível clicar em 'close.png'. Tentando seguir assim mesmo.")

            time.sleep(0.3)

            # Tenta clicar no botão de cancelamento
            if not click_image("cancel_button.png", button="left", timeout=3, confidence=0.7):
                log("[WARN] Não foi possível clicar em 'cancel_button.png'.")

            # Aguarda o modal sumir para evitar tratar o mesmo erro várias vezes
            log("Aguardando o desaparecimento do modal de erro...")
            wait_start = time.time()
            while time.time() - wait_start < 5.0:
                still_there = wait_for_optional_image("err_modal.png", timeout=0.5, confidence=0.7)
                if still_there is None:
                    log("Modal de erro desapareceu. Voltando a monitorar.")
                    break
            else:
                log("[WARN] Modal de erro ainda parece presente após timeout; continuando monitoramento.")

    except KeyboardInterrupt:
        log("Execução interrompida pelo usuário (Ctrl+C).")


if __name__ == "__main__":
    handle_error_modal()





