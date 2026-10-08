#!/usr/bin/env python3

import sys
import os
import json
import time
import signal
import subprocess
import urllib.request
import urllib.error
from pathlib import Path

try:
    from freellmapi_client import chat as freellmapi_chat, configured as freellmapi_configured
except Exception:
    freellmapi_chat = None
    freellmapi_configured = lambda: False


# ============================================================
# PATHS
# ============================================================

BASE = Path(__file__).resolve().parent

MODEL_MANAGER = BASE / "model_manager.py"
MODELS_JSON = BASE / "models" / "models.json"

MEMORY_DIR = BASE / "memory"
MEMORY_PY = MEMORY_DIR / "memory.py"
MEMORY_ACTIONS = MEMORY_DIR / "actions.py"

WEB_DIR = BASE / "web"

SERVER_BIN = (
    Path.home()
    / "llama.cpp"
    / "build"
    / "bin"
    / "llama-server"
)

SERVER_PID_FILE = BASE / "server.pid"
SERVER_LOG = BASE / "server.log"

SERVER_HOST = "127.0.0.1"
SERVER_PORT = 8080

CHAT_URL = (
    f"http://{SERVER_HOST}:{SERVER_PORT}"
    "/v1/chat/completions"
)

HEALTH_URL = (
    f"http://{SERVER_HOST}:{SERVER_PORT}/health"
)


# ============================================================
# IMPORT WEB + MEMORY
# ============================================================

sys.path.insert(0, str(WEB_DIR))

try:
    from web import search_web, read_page, gold_summary
except Exception as e:
    search_web = None
    read_page = None
    gold_summary = None
    WEB_IMPORT_ERROR = str(e)
else:
    WEB_IMPORT_ERROR = None


sys.path.insert(0, str(MEMORY_DIR))

try:
    from actions import handle_memory_action
except Exception:
    handle_memory_action = None

try:
    import importlib.util
    _auto_memory_file = MEMORY_DIR / "auto_memory.py"
    _auto_memory_spec = importlib.util.spec_from_file_location("jiraiya_auto_memory", _auto_memory_file)
    _auto_memory_module = importlib.util.module_from_spec(_auto_memory_spec)
    _auto_memory_spec.loader.exec_module(_auto_memory_module)
    process_auto_memory = _auto_memory_module.process_message
    AUTO_MEMORY_IMPORT_ERROR = None
except Exception as e:
    process_auto_memory = None
    AUTO_MEMORY_IMPORT_ERROR = repr(e)


# ============================================================
# CYBER FOUNDATION
# ============================================================

try:
    from cyber.service import service as cyber_service
    CYBER_IMPORT_ERROR = None
except Exception as e:
    cyber_service = None
    CYBER_IMPORT_ERROR = repr(e)


def is_cyber_intent(text):
    lower = text.lower()
    words = [
        "bug bounty", "vulnerability", "security test", "security assessment",
        "pentest", "pen test", "cyber", "xss", "ssrf", "idor", "injection",
        "security finding", "bug report", "bug bounty report",
    ]
    return any(word in lower for word in words)


def cyber_status():
    if cyber_service is None:
        return "🔐 Cyber module unavailable."
    scope = cyber_service.scope
    findings = cyber_service.list_findings()
    if scope is None:
        return "🛡️ Jiraiya-Cyber is ready. No target scope is configured yet."
    return (
        f"🛡️ Cyber scope: {scope.program} | "
        f"Allowed hosts: {', '.join(scope.allowed_hosts)} | "
        f"Findings: {len(findings)} | "
        "Active PoC execution remains authorization-gated."
    )


# ============================================================
# PID MANAGEMENT
# ============================================================

def read_pid():

    try:

        if not SERVER_PID_FILE.exists():
            return None

        value = SERVER_PID_FILE.read_text().strip()

        if not value:
            return None

        return int(value)

    except Exception:
        return None


def write_pid(pid):

    SERVER_PID_FILE.write_text(
        str(pid)
    )


def remove_pid():

    try:
        SERVER_PID_FILE.unlink()
    except FileNotFoundError:
        pass


def pid_alive(pid):

    if not pid:
        return False

    try:

        os.kill(pid, 0)

        return True

    except OSError:
        return False


# ============================================================
# SERVER HEALTH
# ============================================================

def server_healthy():

    try:

        req = urllib.request.Request(
            HEALTH_URL,
            headers={
                "User-Agent": "Jiraiya/1.0"
            }
        )

        with urllib.request.urlopen(
            req,
            timeout=2
        ) as response:

            return response.status == 200

    except Exception:
        return False


# ============================================================
# SERVER STOP
# ============================================================

def stop_server():

    pid = read_pid()

    if not pid:
        return

    if not pid_alive(pid):

        remove_pid()
        return

    print("🛑 Stopping current model...")

    try:

        os.kill(
            pid,
            signal.SIGTERM
        )

    except Exception:
        pass

    for _ in range(30):

        if not pid_alive(pid):

            break

        time.sleep(0.2)

    if pid_alive(pid):

        try:

            os.kill(
                pid,
                signal.SIGKILL
            )

        except Exception:
            pass

    remove_pid()

    time.sleep(1)


# ============================================================
# MODEL MANAGER
# ============================================================

def load_models():

    try:

        with open(
            MODELS_JSON,
            "r",
            encoding="utf-8"
        ) as f:

            return json.load(f)

    except Exception as e:

        print(
            "❌ Cannot load models:",
            e
        )

        return {}


def get_model(model_id):

    models = load_models()

    return models.get(model_id)


def list_models():

    models = load_models()

    print("\n🤖 Available models:\n")

    for model_id, model in models.items():

        print(
            f"  {model_id:<10} "
            f"{model.get('name', '')}"
        )

    print()


# ============================================================
# SERVER START
# ============================================================

def start_server(model_id):

    model = get_model(model_id)

    if not model:

        print(
            f"❌ Model not found: {model_id}"
        )

        return False

    model_path = (
        BASE
        / "models"
        / model["file"]
    )

    if not model_path.exists():

        print(
            "❌ Model file not found:"
        )

        print(model_path)

        return False

    # --------------------------------------------------------
    # Check existing server
    # --------------------------------------------------------

    old_pid = read_pid()

    if old_pid and pid_alive(old_pid):

        if server_healthy():

            print(
                f"✅ Existing server is already running "
                f"(PID {old_pid})"
            )

            return True

    # --------------------------------------------------------
    # Check orphan server
    # --------------------------------------------------------

    if server_healthy():

        print(
            "⚠️ Port 8080 is already occupied "
            "by another llama-server."
        )

        print(
            "Stop it manually before continuing."
        )

        return False

    # --------------------------------------------------------
    # Start server
    # --------------------------------------------------------

    print(
        f"🚀 Loading model: "
        f"{model.get('name', model_id)}"
    )

    print(
        f"📦 Context: "
        f"{model.get('context', 8192)}"
    )

    print(
        f"🧵 Threads: "
        f"{model.get('threads', 6)}"
    )

    SERVER_LOG.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    log_file = open(
        SERVER_LOG,
        "a",
        encoding="utf-8"
    )

    command = [
        str(SERVER_BIN),

        "-m",
        str(model_path),

        "-c",
        str(model.get("context", 8192)),

        "-t",
        str(model.get("threads", 6)),

        "--host",
        SERVER_HOST,

        "--port",
        str(SERVER_PORT),
    ]

    try:

        process = subprocess.Popen(
            command,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            start_new_session=True
        )

    except Exception as e:

        log_file.close()

        print(
            "❌ Failed to start server:",
            e
        )

        return False

    write_pid(process.pid)

    # --------------------------------------------------------
    # Wait for health
    # --------------------------------------------------------

    print(
        "⏳ Waiting for model server..."
    )

    for _ in range(120):

        if server_healthy():

            print(
                f"✅ Server ready "
                f"(PID {process.pid})"
            )

            return True

        if not pid_alive(process.pid):

            print(
                "❌ llama-server stopped unexpectedly."
            )

            remove_pid()

            return False

        time.sleep(1)

    print(
        "❌ Server startup timeout."
    )

    return False


# ============================================================
# MODEL SWITCH
# ============================================================

def switch_model(model_id):

    model = get_model(model_id)

    if not model:

        print(
            f"❌ Unknown model: {model_id}"
        )

        list_models()

        return False

    current_pid = read_pid()

    if (
        current_pid
        and pid_alive(current_pid)
        and server_healthy()
    ):

        print(
            f"🔄 Switching to "
            f"{model.get('name', model_id)}"
        )

        stop_server()

    return start_server(model_id)


# ============================================================
# CHAT WITH LOCAL MODEL
# ============================================================

def ask_model(
    message,
    system_prompt=None,
    max_tokens=400
):

    if freellmapi_chat and freellmapi_configured():
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        try:
            import importlib.util
            _mc_file = MEMORY_DIR / "memory_context.py"
            _mc_spec = importlib.util.spec_from_file_location("jiraiya_memory_context_remote", _mc_file)
            _mc_module = importlib.util.module_from_spec(_mc_spec)
            _mc_spec.loader.exec_module(_mc_module)
            remote_memory_context = _mc_module.get_memory_context(message, limit=3)
        except Exception:
            remote_memory_context = ""
        if remote_memory_context:
            messages.append({"role": "system", "content": remote_memory_context})
        messages.append({"role": "user", "content": message})
        try:
            return freellmapi_chat(messages, max_tokens=max_tokens, temperature=0.2, timeout=300)
        except Exception as remote_error:
            print(f"⚠️ FreeLLMAPI unavailable, using local model: {remote_error}")

    payload = {
        "messages": []
    }

    if system_prompt:

        payload["messages"].append({
            "role": "system",
            "content": system_prompt
        })

    try:
        import importlib.util
        _mc_file = MEMORY_DIR / "memory_context.py"
        _mc_spec = importlib.util.spec_from_file_location("jiraiya_memory_context_runtime", _mc_file)
        _mc_module = importlib.util.module_from_spec(_mc_spec)
        _mc_spec.loader.exec_module(_mc_module)
        memory_context = _mc_module.get_memory_context(message, limit=3)
    except Exception:
        memory_context = ""

    payload["messages"].append({
            "role": "system",
            "content": memory_context
        })

    payload["messages"].append({
        "role": "user",
        "content": message
    })

    payload["temperature"] = 0.2
    payload["max_tokens"] = max_tokens
    payload["stream"] = False

    data = json.dumps(
        payload
    ).encode("utf-8")

    request = urllib.request.Request(
        CHAT_URL,
        data=data,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "Jiraiya/1.0"
        },
        method="POST"
    )

    try:

        with urllib.request.urlopen(
            request,
            timeout=300
        ) as response:

            result = json.loads(
                response.read().decode(
                    "utf-8"
                )
            )

        return (
            result["choices"][0]
            ["message"]
            ["content"]
            .strip()
        )

    except Exception as e:

        return (
            f"❌ Model error: {e}"
        )


# ============================================================
# MEMORY
# ============================================================

def memory_request(text):

    if not handle_memory_action:

        return False, None

    try:

        result = handle_memory_action(
            text
        )

        if not result:
            return False, None

        return True, result

    except Exception:

        return False, None


def remember_direct(text):

    clean = text.strip()

    triggers = [
        "remember that ",
        "remember this ",
        "remember my ",
        "don't forget ",
        "do not forget ",
        "keep in mind ",
        "yaad rakh ",
        "yaad rakhna ",
        "yaad rkh ",
        "याद रखना ",
        "याद रखो ",
        "याद रख ",
    ]

    lower = clean.lower()

    memory_text = None

    for trigger in triggers:

        if lower.startswith(trigger):

            memory_text = clean[
                len(trigger):
            ].strip()

            break

    if not memory_text:
        return False

    # Basic protection against saving obvious secrets
    secret_words = [
        "password",
        "passwd",
        "api key",
        "apikey",
        "secret key",
        "private key",
        "otp",
        "one time password",
    ]

    if any(
        word in memory_text.lower()
        for word in secret_words
    ):

        print(
            "⚠️ I won't automatically save "
            "passwords, OTPs, or secret keys."
        )

        return True

    command = [
        "python",
        str(MEMORY_PY),
        "add",
        "user",
        memory_text
    ]

    try:

        result = subprocess.run(
            command,
            capture_output=True,
            text=True
        )

        if result.returncode == 0:

            pass

        else:

            print(
                "❌ Memory save failed:"
            )

            print(
                result.stderr
            )

    except Exception as e:

        print(
            "❌ Memory error:",
            e
        )

    return True


# ============================================================
# GOLD FORMATTER
# ============================================================

def format_gold_result(data):

    if not data or not data.get("ok"):

        return None

    city = data.get(
        "city",
        "requested city"
    )

    primary = data.get(
        "primary",
        {}
    )

    rates = primary.get(
        "rates",
        {}
    )

    date = primary.get(
        "date",
        "today"
    )

    source = primary.get(
        "source",
        "Unknown"
    )

    lines = []

    lines.append(
        f"🪙 Gold rate in {city.title()} "
        f"({date}):"
    )

    if rates.get("24K") is not None:

        lines.append(
            f"24K: ₹{rates['24K']:,.0f}/g"
        )

    if rates.get("22K") is not None:

        lines.append(
            f"22K: ₹{rates['22K']:,.0f}/g"
        )

    if rates.get("18K") is not None:

        lines.append(
            f"18K: ₹{rates['18K']:,.0f}/g"
        )

    lines.append(
        f"Source: {source}"
    )

    # --------------------------------------------------------
    # Secondary source comparison
    # --------------------------------------------------------

    sources = data.get(
        "sources",
        []
    )

    if len(sources) > 1:

        secondary = sources[1]

        secondary_rates = secondary.get(
            "rates",
            {}
        )

        secondary_name = secondary.get(
            "source",
            "Secondary source"
        )

        if secondary_rates.get("22K") is not None:

            lines.append(
                f"{secondary_name}: "
                f"22K ₹{secondary_rates['22K']:,.0f}/g"
            )

    lines.append(
        "ℹ️ Jewellery shop final price may "
        "differ because of GST, making charges, "
        "and other applicable charges."
    )

    return "\n".join(lines)


# ============================================================
# INTENT DETECTION
# ============================================================

def cyber_assistant_answer(text):
    status = cyber_status()
    prompt = (
        "You are Jiraiya-Cyber, an authorization-first security assistant. "
        "Help with defensive security assessment, scope definition, finding analysis, "
        "evidence handling, and bug-bounty reporting. Never claim that a target was tested "
        "unless an actual authorized tool result is supplied. Active PoC actions require "
        "explicit authorization for the exact finding, target, and action.\\n\\n"
        f"Current cyber status: {status}\\n\\nUser request:\\n{text}"
    )
    return str(ask_model(prompt, system_prompt="You are Jiraiya-Cyber. Follow authorization boundaries exactly.", max_tokens=500) or "")


def is_memory_intent(text):

    lower = text.lower()

    memory_words = [
        "remember",
        "don't forget",
        "do not forget",
        "keep in mind",
        "yaad rakh",
        "yaad rkh",
        "याद रख",
    ]

    return any(
        word in lower
        for word in memory_words
    )


def is_gold_intent(text):

    lower = text.lower()

    gold_words = [
        "gold rate",
        "gold price",
        "gold rates",
        "gold prices",
        "gold",
        "sona",
        "सोना",
    ]

    rate_words = [
        "rate",
        "price",
        "today",
        "current",
        "latest",
        "aaj",
        "आज",
    ]

    return (
        any(
            word in lower
            for word in gold_words
        )
        and
        any(
            word in lower
            for word in rate_words
        )
    )


def is_calculator_intent(text):

    lower = text.lower()

    calculator_words = [
        "calculate",
        "calculator",
        "what is",
        "how much is",
        "%",
        "percent",
        "+",
        "-",
        "*",
        "/",
    ]

    return any(
        word in lower
        for word in calculator_words
    )


def is_coding_intent(text):

    lower = text.lower()

    coding_words = [
        "write python",
        "write code",
        "python code",
        "coding",
        "program",
        "script",
        "function",
        "debug",
        "fix this code",
        "code for",
    ]

    return any(
        word in lower
        for word in coding_words
    )


def is_web_intent(text):

    lower = text.lower()

    web_words = [
        "latest news",
        "latest",
        "today",
        "current",
        "weather",
        "news",
        "search",
        "internet",
        "online",
        "who is",
        "what happened",
    ]

    return any(
        word in lower
        for word in web_words
    )


# ============================================================
# CALCULATOR
# ============================================================

def calculator_answer(text):

    expression = text

    replacements = {
        "percent": "%",
        "percentage": "%",
    }

    for old, new in replacements.items():

        expression = expression.replace(
            old,
            new
        )

    # --------------------------------------------------------
    # Simple percentage
    # --------------------------------------------------------

    import re

    match = re.search(
        r"(\d+(?:\.\d+)?)\s*%\s*of\s*(\d+(?:\.\d+)?)",
        expression,
        re.IGNORECASE
    )

    if match:

        percentage = float(
            match.group(1)
        )

        number = float(
            match.group(2)
        )

        answer = (
            percentage
            / 100
            * number
        )

        return (
            f"🧮 {percentage:g}% of "
            f"{number:g} = {answer:g}"
        )

    # --------------------------------------------------------
    # Basic arithmetic
    # --------------------------------------------------------

    match = re.search(
        r"(-?\d+(?:\.\d+)?)"
        r"\s*"
        r"([+\-*/])"
        r"\s*"
        r"(-?\d+(?:\.\d+)?)",
        expression
    )

    if match:

        a = float(match.group(1))
        op = match.group(2)
        b = float(match.group(3))

        try:

            if op == "+":
                answer = a + b

            elif op == "-":
                answer = a - b

            elif op == "*":
                answer = a * b

            else:
                answer = a / b

            return (
                f"🧮 {a:g} {op} {b:g} "
                f"= {answer:g}"
            )

        except Exception as e:

            return f"❌ Calculation error: {e}"

    return None


# ============================================================
# WEB ANSWER
# ============================================================

def ask_web(query):

    if not search_web:

        return (
            "❌ Web module unavailable."
        )

    print(
        f"🌐 Searching: {query}"
    )

    results = search_web(
        query,
    )

    if not results:

        return (
            "❌ No web results found."
        )

    context = []

    for i, result in enumerate(
        results,
        1
    ):

        title = result.get(
            "title",
            ""
        )

        url = result.get(
            "url",
            ""
        )

        context.append(
            f"{i}. {title}\n{url}"
        )

    web_context = "\n\n".join(
        context
    )

    prompt = f"""
Use the following web search results to answer the user's question.

User question:
{query}

Search results:
{web_context}

Give a concise answer.
Do not invent facts.
Mention uncertainty when the search results are insufficient.
"""

    return ask_model(
        prompt,
        system_prompt=(
            "You are Jiraiya, a helpful local AI assistant. "
            "Answer using the supplied web results."
        ),
        max_tokens=350
    )


# ============================================================
# NATURAL LANGUAGE ROUTER
# ============================================================

def route_user_message(text):
    """
    Route a user message and RETURN the final response.

    The CLI/API layer decides whether the response should be printed.
    """

    clean = str(text or "").strip()

    if not clean:
        return ""

    # --------------------------------------------------------
    # CYBER
    # --------------------------------------------------------

    if is_cyber_intent(clean):
        return cyber_assistant_answer(clean)

    # --------------------------------------------------------
    # DIRECT MEMORY
    # --------------------------------------------------------

    if remember_direct(clean):
        return ""

    # --------------------------------------------------------
    # AUTOMATIC MEMORY
    # --------------------------------------------------------

    try:
        process_auto_memory(clean)
    except Exception:
        pass

    # --------------------------------------------------------
    # EXPLICIT MEMORY INTENT
    # --------------------------------------------------------

    memory_handled, explicit_memory = memory_request(clean)

    if memory_handled:
        return str(explicit_memory or "")

    # --------------------------------------------------------
    # GOLD
    # --------------------------------------------------------

    if is_gold_intent(clean):

        if gold_summary:

            result = gold_summary(
                clean
            )

            answer = format_gold_result(
                result
            )

            if answer:
                return answer

        return str(ask_web(clean) or "")

    # --------------------------------------------------------
    # CALCULATOR
    # --------------------------------------------------------

    if is_calculator_intent(clean):

        answer = calculator_answer(
            clean
        )

        if answer:
            return str(answer)

    # --------------------------------------------------------
    # CODING
    # --------------------------------------------------------

    if is_coding_intent(clean):

        prompt = (
            "Answer the following coding request. "
            "Provide practical, correct code and "
            "keep the explanation concise.\n\n"
            + clean
        )

        return str(
            ask_model(
                prompt,
                system_prompt=(
                    "You are Jiraiya's coding assistant."
                ),
                max_tokens=500
            ) or ""
        )

    # --------------------------------------------------------
    # GENERAL WEB
    # --------------------------------------------------------

    if is_web_intent(clean):
        return str(
            ask_web(clean) or ""
        )

    # --------------------------------------------------------
    # LOCAL MODEL
    # --------------------------------------------------------

    return str(
        ask_model(
            clean,
            system_prompt=(
                "You are Jiraiya, a helpful "
                "local AI assistant."
            ),
            max_tokens=400
        ) or ""
    )

# ============================================================
# COMMANDS
# ============================================================

def show_model():

    pid = read_pid()

    models = load_models()

    active = "unknown"

    if pid and pid_alive(pid):

        # Infer active model from command line
        try:

            result = subprocess.run(
                [
                    "ps",
                    "-p",
                    str(pid),
                    "-o",
                    "args="
                ],
                capture_output=True,
                text=True
            )

            command = result.stdout.strip()

            for model_id, model in models.items():

                if model.get("file") in command:

                    active = model_id
                    break

        except Exception:
            pass

    print(
        f"🤖 Active model: {active}"
    )

    print(
        f"PID: {pid if pid else 'none'}"
    )

    print(
        f"Health: "
        f"{'OK' if server_healthy() else 'OFF'}"
    )


def show_memories():

    if not MEMORY_PY.exists():

        print(
            "❌ Memory system not found."
        )

        return

    result = subprocess.run(
        [
            "python",
            str(MEMORY_PY),
            "list"
        ],
        capture_output=True,
        text=True
    )

    print(
        result.stdout
    )

    if result.stderr:
        print(
            result.stderr
        )


# ============================================================
# COMMAND LOOP
# ============================================================

def handle_command(text):

    parts = text.strip().split()

    command = parts[0].lower()

    if command == "/exit":

        print(
            "👋 Shutting down Jiraiya..."
        )

        stop_server()

        return "EXIT"

    if command == "/models":

        list_models()

        return True

    if command == "/model":

        if len(parts) == 1:

            show_model()

        else:

            switch_model(
                parts[1]
            )

        return True

    if command == "/memories":

        show_memories()

        return True

    if command == "/remember":

        memory_text = (
            text[len("/remember"):].strip()
        )

        if memory_text:

            remember_direct(
                "remember that "
                + memory_text
            )

        else:

            print(
                "Usage: /remember <memory>"
            )

        return True

    return False


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        "\n"
        "====================================\n"
        "        🐸 JIRAIYA AI\n"
        "====================================\n"
    )

    if freellmapi_configured():
        print("☁️ FreeLLMAPI backend enabled.")
        print("🧠 Inference will be routed by FreeLLMAPI.")
        print("💻 No local GGUF model is required for normal chat.\n")

    elif not SERVER_BIN.exists():

        print(
            "❌ llama-server not found:"
        )

        print(
            SERVER_BIN
        )

        return

    # --------------------------------------------------------
    # Reuse running server
    # --------------------------------------------------------

    pid = read_pid()

    if freellmapi_configured():
        pid = None

    elif (
        pid
        and pid_alive(pid)
        and server_healthy()
    ):

        print(
            f"✅ Reusing running model "
            f"(PID {pid})"
        )

    else:

        if pid and not pid_alive(pid):
            remove_pid()

        # Default model
        if not start_server("coder"):

            print(
                "❌ Unable to start Jiraiya."
            )

            return

    print(
        "\nType /models to list models."
    )

    print(
        "Type /model <id> to switch model."
    )

    print(
        "Type /memories to view memories."
    )

    print(
        "Type /exit to quit.\n"
    )

    while True:

        try:

            user_input = input(
                "You: "
            )

        except (
            KeyboardInterrupt,
            EOFError
        ):

            print()

            stop_server()

            break

        user_input = user_input.strip()

        if not user_input:
            continue

        if user_input.startswith("/"):

            result = handle_command(
                user_input
            )

            if result == "EXIT":
                break

            if result:
                continue

        try:

            route_user_message(
                user_input
            )

        except KeyboardInterrupt:

            print(
                "\n⚠️ Interrupted."
            )

        except Exception as e:

            print(
                f"❌ Error: {e}"
            )


if __name__ == "__main__":
    main()
