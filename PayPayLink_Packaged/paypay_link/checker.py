import requests
import uuid
import time
import os
import sys
import asyncio

# Attempt to enable virtual terminal processing for colors on Windows
if sys.platform == "win32":
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(-11)
        mode = ctypes.c_ulong()
        kernel32.GetConsoleMode(handle, ctypes.byref(mode))
        mode.value |= 4  # ENABLE_VIRTUAL_TERMINAL_PROCESSING
        kernel32.SetConsoleMode(handle, mode)
    except Exception:
        pass

class Color:
    GREEN = '\033[32m'
    RED = '\033[31m'
    YELLOW = '\033[33m'
    RESET = '\033[0m'

def _check_single_link(code_i, file, logger):
    code = code_i.replace("https://pay.paypay.ne.jp/", "")
    client_uuid = str(uuid.uuid4())
    p2pinfo_headers = {
        "Accept": "application/json, text/plain, */*",
        "User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.76 Safari/537.36"
    }

    try:
        get_p2p = requests.get(
            f"https://www.paypay.ne.jp/app/v2/p2p-api/getP2PLinkInfo?verificationCode={code}&client_uuid={client_uuid}", 
            headers=p2pinfo_headers,
            timeout=10
        )
        get_p2p.raise_for_status()
        data_p2p = get_p2p.json()

        if data_p2p.get("payload", {}).get("orderStatus") == "PENDING":
            amount = data_p2p.get("payload", {}).get("pendingP2PInfo", {}).get("amount")
            has_passcode = data_p2p.get("payload", {}).get("pendingP2PInfo", {}).get("isSetPasscode", False)
            
            amount_str = f"Amount: {amount}" if amount else "Amount: Not specified"
            passcode_str = f"{Color.RED}Passcode: Yes{Color.RESET}" if has_passcode else f"{Color.GREEN}Passcode: No{Color.RESET}"

            logger(
                f"{Color.GREEN}[SUCCESS] https://pay.paypay.ne.jp/{code} | {amount_str} | "
                f"Status: {get_p2p.status_code} | {passcode_str}{Color.RESET}"
            )

            try:
                with open(file, "a", encoding="utf-8") as f:
                    f.write(f"https://pay.paypay.ne.jp/{code}\n")
                return "success"
            except IOError as e:
                logger(f"{Color.RED}[ERROR] Could not write to file {file}: {e}{Color.RESET}")
                return "died"

        else:
            error_info = data_p2p.get("payload", {}).get("errorMessage", "Invalid link or expired")
            logger(
                f"{Color.RED}[FAILURE] https://pay.paypay.ne.jp/{code} | {error_info} | "
                f"Status: {get_p2p.status_code}{Color.RESET}"
            )
            return "died"

    except requests.exceptions.RequestException as e:
        logger(f"{Color.RED}[FAILURE] https://pay.paypay.ne.jp/{code} | {Color.YELLOW}Request failed: {e}{Color.RESET}")
        return "died"
    except Exception as e:
        logger(f"{Color.RED}[FAILURE] https://pay.paypay.ne.jp/{code} | {Color.YELLOW}An unexpected error occurred: {e}{Color.RESET}")
        return "died"

def check_links(file, delay_ms, output, logger=print, cancel_event: asyncio.Event | None = None):
    if not os.path.isfile(file):
        logger(f"{Color.RED}[ERROR] File not found: {file}{Color.RESET}")
        return

    try:
        with open(file, "r", encoding="utf-8") as f:
            links = [line.strip() for line in f if line.strip()]
    except IOError as e:
        logger(f"{Color.RED}[ERROR] Could not read file {file}: {e}{Color.RESET}")
        return

    total = len(links)
    logger(f"Checking {total} links from {file}...")
    success = 0
    failure = 0

    for i, link in enumerate(links):
        if cancel_event and cancel_event.is_set():
            logger("Checking cancelled by user.")
            break
        result = _check_single_link(link, output, logger)
        if result == "success":
            success += 1
        else:
            failure += 1
        time.sleep(delay_ms / 1000.0)

    logger(f"\n--- Check Complete ---")
    logger(f"Total: {i+1 if cancel_event and cancel_event.is_set() else total} | {Color.GREEN}Successful: {success}{Color.RESET} | {Color.RED}Failed: {failure}{Color.RESET}")

async def check_links_from_queue(queue: asyncio.Queue, delay_ms, output, logger=print, cancel_event: asyncio.Event | None = None, generation_task: asyncio.Task | None = None):
    success = 0
    failure = 0
    total = 0

    while not (generation_task and generation_task.done() and queue.empty()):
        if cancel_event and cancel_event.is_set():
            logger("Checking cancelled by user.")
            break
        try:
            link = await asyncio.wait_for(queue.get(), timeout=1.0)
            total += 1
            result = await asyncio.to_thread(_check_single_link, link, output, logger)
            if result == "success":
                success += 1
            else:
                failure += 1
            await asyncio.sleep(delay_ms / 1000.0)
            queue.task_done()
        except asyncio.TimeoutError:
            continue
        except Exception as e:
            logger(f"{Color.RED}[ERROR] An error occurred in checker: {e}{Color.RESET}")
            break

    logger(f"\n--- Check Complete ---")
    logger(f"Total: {total} | {Color.GREEN}Successful: {success}{Color.RESET} | {Color.RED}Failed: {failure}{Color.RESET}")

def check_single_link(link, delay_ms, output, logger=print):
    """Checks a single link."""
    result = _check_single_link(link, output, logger)
    time.sleep(delay_ms / 1000.0)
    return result
