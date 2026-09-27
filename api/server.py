#!/usr/bin/env python3

from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import io
import contextlib
import sys
from pathlib import Path

# ============================================================
# PROJECT PATH
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))


# ============================================================
# AGENT
# ============================================================

import agent

try:
    from cyber.service import service as cyber_service
    CYBER_SERVICE_ERROR = None
except Exception as exc:
    cyber_service = None
    CYBER_SERVICE_ERROR = str(exc)


# ============================================================
# SESSION CONTEXT
# ============================================================

try:
    from api.session_context import build_context_message
    SESSION_CONTEXT_ERROR = None
except Exception as exc:
    build_context_message = None
    SESSION_CONTEXT_ERROR = str(exc)


# ============================================================
# SESSION MANAGER
# ============================================================

try:
    from sessions.session_manager import (
        create_session,
        get_session,
        list_sessions,
        add_message,
        rename_session,
        delete_session,
    )

    SESSION_MANAGER_ERROR = None

except Exception as exc:

    create_session = None
    get_session = None
    list_sessions = None
    add_message = None
    rename_session = None
    delete_session = None

    SESSION_MANAGER_ERROR = str(exc)


# ============================================================
# SERVER CONFIG
# ============================================================

HOST = "127.0.0.1"
PORT = 8090


# ============================================================
# HTTP HANDLER
# ============================================================

class JiraiyaHandler(BaseHTTPRequestHandler):

    # --------------------------------------------------------
    # CORS
    # --------------------------------------------------------

    def _send_cors_headers(self):

        self.send_header(
            "Access-Control-Allow-Origin",
            "*"
        )

        self.send_header(
            "Access-Control-Allow-Methods",
            "GET, POST, PUT, DELETE, OPTIONS"
        )

        self.send_header(
            "Access-Control-Allow-Headers",
            "Content-Type"
        )

    # --------------------------------------------------------
    # JSON RESPONSE
    # --------------------------------------------------------

    def _send_json(self, data, status=200):

        body = json.dumps(
            data,
            ensure_ascii=False
        ).encode("utf-8")

        self.send_response(status)

        self.send_header(
            "Content-Type",
            "application/json; charset=utf-8"
        )

        self.send_header(
            "Content-Length",
            str(len(body))
        )

        self._send_cors_headers()

        self.end_headers()

        self.wfile.write(body)

    # --------------------------------------------------------
    # JSON REQUEST
    # --------------------------------------------------------

    def _read_json(self):

        length = int(
            self.headers.get(
                "Content-Length",
                0
            )
        )

        if length <= 0:
            return {}

        raw = self.rfile.read(length)

        try:

            return json.loads(
                raw.decode("utf-8")
            )

        except Exception:

            return {}

    # --------------------------------------------------------
    # OPTIONS / CORS PREFLIGHT
    # --------------------------------------------------------

    def do_OPTIONS(self):

        self.send_response(204)

        self._send_cors_headers()

        self.end_headers()

    # ========================================================
    # GET
    # ========================================================

    def do_GET(self):

        if self._cyber_get(self.path):
            return

        # ----------------------------------------------------
        # HEALTH
        # ----------------------------------------------------

        if self.path == "/health":

            self._send_json({

                "ok": True,

                "service": "jiraiya-api",

                "engine": (
                    agent is not None
                ),

                "session_context": (
                    build_context_message
                    is not None
                ),

                "session_manager": (
                    list_sessions is not None
                )

            })

            return

        # ----------------------------------------------------
        # LIST SESSIONS
        # ----------------------------------------------------

        if self.path == "/api/sessions":

            if list_sessions is None:

                self._send_json({

                    "ok": False,

                    "error":
                        "Session manager unavailable"

                }, 500)

                return

            sessions = list_sessions()

            self._send_json({

                "ok": True,

                "sessions": sessions

            })

            return

        # ----------------------------------------------------
        # GET SINGLE SESSION
        # ----------------------------------------------------

        if self.path.startswith(
            "/api/sessions/"
        ):

            session_id = self.path.split(
                "/api/sessions/",
                1
            )[1]

            if not session_id:

                self._send_json({

                    "ok": False,

                    "error":
                        "Missing session id"

                }, 400)

                return

            if get_session is None:

                self._send_json({

                    "ok": False,

                    "error":
                        "Session manager unavailable"

                }, 500)

                return

            session = get_session(
                session_id
            )

            if session is None:

                self._send_json({

                    "ok": False,

                    "error":
                        "Session not found"

                }, 404)

                return

            self._send_json({

                "ok": True,

                "session": session

            })

            return

        # ----------------------------------------------------
        # NOT FOUND
        # ----------------------------------------------------

        self._send_json({

            "ok": False,

            "error": "Not found"

        }, 404)

    # ========================================================
    # POST
    # ========================================================

    def _cyber_error(self, exc):
        status = 400
        if isinstance(exc, KeyError):
            status = 404
        self._send_json({"ok": False, "error": str(exc)}, status)

    def _cyber_get(self, path):
        if cyber_service is None:
            self._send_json({"ok": False, "error": CYBER_SERVICE_ERROR or "Cyber service unavailable"}, 500)
            return True
        if path == "/api/cyber/findings":
            self._send_json({"ok": True, "findings": cyber_service.list_findings()})
            return True
        if path.startswith("/api/cyber/authorization/"):
            auth_id = path.rsplit("/", 1)[-1]
            record = cyber_service.authorization.get(auth_id)
            if record is None:
                self._send_json({"ok": False, "error": "authorization not found"}, 404)
            else:
                self._send_json({"ok": True, "authorization": record})
            return True
        return False

    def _cyber_post(self, path, data):
        if cyber_service is None:
            self._send_json({"ok": False, "error": CYBER_SERVICE_ERROR or "Cyber service unavailable"}, 500)
            return True
        try:
            if path == "/api/cyber/scope":
                self._send_json({"ok": True, "scope": cyber_service.set_scope(data)})
                return True
            if path == "/api/cyber/recon":
                urls = data.get("urls", [])
                if not isinstance(urls, list):
                    raise ValueError("urls must be a list")
                self._send_json({"ok": True, **cyber_service.recon([str(x) for x in urls], int(data.get("max_requests", 5)))})
                return True
            if path.startswith("/api/cyber/report/"):
                finding_id = path.rsplit("/", 1)[-1]
                self._send_json({"ok": True, "report": cyber_service.report(finding_id, str(data.get("impact", "")), str(data.get("remediation", "")))})
                return True
            if path == "/api/cyber/finding":
                self._send_json({"ok": True, "finding": cyber_service.create_finding(data)})
                return True
            if path.startswith("/api/cyber/finding/") and path.endswith("/verification"):
                finding_id = path.split("/api/cyber/finding/", 1)[1].rsplit("/verification", 1)[0]
                self._send_json({"ok": True, "plan": cyber_service.verification_plan(finding_id)})
                return True
            if path.startswith("/api/cyber/finding/") and path.endswith("/authorization"):
                finding_id = path.split("/api/cyber/finding/", 1)[1].rsplit("/authorization", 1)[0]
                self._send_json({"ok": True, "authorization": cyber_service.request_authorization(
                    finding_id,
                    str(data.get("action", "controlled_non_destructive_poc")),
                    int(data.get("max_attempts", 1)),
                    int(data.get("expires_in_seconds", 300)),
                )})
                return True
            if path.startswith("/api/cyber/authorization/") and path.endswith("/approve"):
                auth_id = path.split("/api/cyber/authorization/", 1)[1].rsplit("/approve", 1)[0]
                self._send_json({"ok": True, "authorization": cyber_service.authorization.authorize(auth_id).as_dict()})
                return True
            if path.startswith("/api/cyber/authorization/") and path.endswith("/consume"):
                auth_id = path.split("/api/cyber/authorization/", 1)[1].rsplit("/consume", 1)[0]
                self._send_json({"ok": True, **cyber_service.consume_authorization(
                    auth_id, str(data.get("finding_id", "")), str(data.get("action", "controlled_non_destructive_poc"))
                )})
                return True
        except Exception as exc:
            self._cyber_error(exc)
            return True
        return False

    def do_POST(self):

        data = self._read_json()
        if self._cyber_post(self.path, data):
            return

        # ----------------------------------------------------
        # CREATE SESSION
        # ----------------------------------------------------

        if self.path == "/api/sessions":

            if create_session is None:

                self._send_json({

                    "ok": False,

                    "error":
                        "Session manager unavailable"

                }, 500)

                return

            title = data.get(
                "title",
                "New Chat"
            )

            session = create_session(
                title
            )

            self._send_json({

                "ok": True,

                "session": session

            })

            return

        # ----------------------------------------------------
        # CHAT
        # ----------------------------------------------------

        if self.path == "/api/chat":

            message = str(
                data.get(
                    "message",
                    ""
                )
            ).strip()

            if not message:

                self._send_json({

                    "ok": False,

                    "error":
                        "Message is required"

                }, 400)

                return

            history = data.get(
                "history",
                []
            )

            if not isinstance(
                history,
                list
            ):

                history = []

            history = history[-20:]

            session_id = data.get(
                "session_id"
            )

            # ------------------------------------------------
            # BUILD CURRENT CONVERSATION CONTEXT
            # ------------------------------------------------

            context_message = message

            if build_context_message is not None:

                context_message = (
                    build_context_message(
                        message,
                        history
                    )
                )

            # ------------------------------------------------
            # RUN AGENT
            # ------------------------------------------------

            output = io.StringIO()

            try:

                with contextlib.redirect_stdout(
                    output
                ):

                    reply = (
                        agent.route_user_message(
                            context_message
                        )
                    )

                reply = str(
                    reply or ""
                )

            except Exception as exc:

                self._send_json({

                    "ok": False,

                    "error": str(exc)

                }, 500)

                return

            # ------------------------------------------------
            # SAVE SESSION MESSAGES
            # ------------------------------------------------

            if (
                session_id
                and add_message is not None
            ):

                add_message(
                    session_id,
                    "user",
                    message
                )

                add_message(
                    session_id,
                    "assistant",
                    reply
                )

            # ------------------------------------------------
            # RESPONSE
            # ------------------------------------------------

            self._send_json({

                "ok": True,

                "message": message,

                "reply": reply,

                "session_id": session_id

            })

            return

        # ----------------------------------------------------
        # NOT FOUND
        # ----------------------------------------------------

        self._send_json({

            "ok": False,

            "error": "Not found"

        }, 404)

    # ========================================================
    # PUT
    # ========================================================

    def do_PUT(self):

        if self.path.startswith(
            "/api/sessions/"
        ):

            session_id = self.path.split(
                "/api/sessions/",
                1
            )[1]

            if rename_session is None:

                self._send_json({

                    "ok": False,

                    "error":
                        "Session manager unavailable"

                }, 500)

                return

            data = self._read_json()

            title = data.get(
                "title",
                "New Chat"
            )

            session = rename_session(
                session_id,
                title
            )

            if session is None:

                self._send_json({

                    "ok": False,

                    "error":
                        "Session not found"

                }, 404)

                return

            self._send_json({

                "ok": True,

                "session": session

            })

            return

        self._send_json({

            "ok": False,

            "error": "Not found"

        }, 404)

    # ========================================================
    # DELETE
    # ========================================================

    def do_DELETE(self):

        if self.path.startswith(
            "/api/sessions/"
        ):

            session_id = self.path.split(
                "/api/sessions/",
                1
            )[1]

            if delete_session is None:

                self._send_json({

                    "ok": False,

                    "error":
                        "Session manager unavailable"

                }, 500)

                return

            success = delete_session(
                session_id
            )

            if not success:

                self._send_json({

                    "ok": False,

                    "error":
                        "Session not found"

                }, 404)

                return

            self._send_json({

                "ok": True,

                "deleted": session_id

            })

            return

        self._send_json({

            "ok": False,

            "error": "Not found"

        }, 404)

    # ========================================================
    # DISABLE DEFAULT HTTP LOG
    # ========================================================

    def log_message(
        self,
        format,
        *args
    ):
        return


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        f"🧠 Jiraiya API running at "
        f"http://{HOST}:{PORT}"
    )

    server = HTTPServer(
        (HOST, PORT),
        JiraiyaHandler
    )

    server.serve_forever()


if __name__ == "__main__":
    main()
