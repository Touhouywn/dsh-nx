import json
import os
import runpy
import socket
import traceback

import NXOpen
import NXOpen.Features


HOST = "127.0.0.1"
PORT = int(os.environ.get("NX2512_LEGACY_PORT", "25120"))
PROJECT_ROOT = (
    os.environ.get("NX2512_PROJECT_ROOT")
    or os.environ.get("DC2512_PROJECT_ROOT")
    or os.path.join(os.environ.get("USERPROFILE", os.getcwd()), "Documents", "Codex", "NX2512")
)
_SHUTDOWN = False


def _session():
    return NXOpen.Session.GetSession()


def _part_info(part):
    if part is None:
        return None
    return {
        "name": getattr(part, "Name", ""),
        "fullPath": getattr(part, "FullPath", ""),
    }


def _status(_params):
    session = _session()
    return {
        "ok": True,
        "workPart": _part_info(session.Parts.Work),
        "displayPart": _part_info(session.Parts.Display),
    }


def _create_modeling_part(params):
    session = _session()

    part_path = params.get("part_path")
    if not part_path:
        import datetime

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        part_path = os.path.join(PROJECT_ROOT, "nx_live_modeling_%s.prt" % timestamp)

    part = session.Parts.NewDisplay(part_path, NXOpen.Part.Units.Millimeters)
    session.Parts.SetWork(part)
    session.Parts.SetDisplay(part, False, False)
    session.ApplicationSwitchImmediate("UG_APP_MODELING")
    part.ModelingViews.WorkView.Fit()

    if params.get("save", True):
        part.Save(NXOpen.BasePart.SaveComponents.TrueValue, NXOpen.BasePart.CloseAfterSave.FalseValue)

    session.ListingWindow.Open()
    session.ListingWindow.WriteLine("Codex bridge created part: " + part_path)
    return {"ok": True, "partPath": part_path}


def _create_block(params):
    session = _session()
    part = session.Parts.Work
    if part is None:
        raise RuntimeError("No work part is open in the current NX window.")

    session.ApplicationSwitchImmediate("UG_APP_MODELING")
    length = str(params.get("length", 80))
    width = str(params.get("width", 50))
    height = str(params.get("height", 25))

    builder = part.Features.CreateBlockFeatureBuilder(None)
    builder.SetOriginAndLengths(NXOpen.Point3d(0.0, 0.0, 0.0), length, width, height)
    feature = builder.CommitFeature()
    builder.Destroy()
    part.ModelingViews.WorkView.Fit()

    if params.get("save", True):
        part.Save(NXOpen.BasePart.SaveComponents.TrueValue, NXOpen.BasePart.CloseAfterSave.FalseValue)

    session.ListingWindow.Open()
    session.ListingWindow.WriteLine("Codex bridge created block: %s x %s x %s" % (length, width, height))
    return {"ok": True, "featureName": getattr(feature, "Name", "")}


def _run_script_file(params):
    path = params.get("path")
    if not path:
        raise RuntimeError("Missing script path.")
    full_path = os.path.abspath(path)
    if not os.path.isfile(full_path):
        raise RuntimeError("Script file does not exist: " + full_path)
    runpy.run_path(full_path, run_name="__main__")
    return {"ok": True, "path": full_path}


COMMANDS = {
    "ping": lambda _params: {"ok": True, "message": "nx2512 bridge alive"},
    "status": _status,
    "create_modeling_part": _create_modeling_part,
    "create_block": _create_block,
    "run_script_file": _run_script_file,
}


def _handle_request(payload):
    global _SHUTDOWN

    command = payload.get("command")
    params = payload.get("params") or {}
    if command == "shutdown":
        _SHUTDOWN = True
        return {"ok": True, "message": "nx2512 bridge shutting down"}
    if command not in COMMANDS:
        raise RuntimeError("Unknown command: " + str(command))
    return COMMANDS[command](params)


def _serve_client(conn):
    with conn:
        raw = b""
        while not raw.endswith(b"\n"):
            chunk = conn.recv(65536)
            if not chunk:
                break
            raw += chunk
        payload = json.loads(raw.decode("utf-8"))
        try:
            result = _handle_request(payload)
            response = {"ok": True, "result": result}
        except Exception as exc:
            response = {
                "ok": False,
                "error": str(exc),
                "traceback": traceback.format_exc(),
            }
        conn.sendall((json.dumps(response, ensure_ascii=False) + "\n").encode("utf-8"))


def main():
    global _SHUTDOWN

    session = _session()
    lw = session.ListingWindow
    lw.Open()

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        server.bind((HOST, PORT))
    except OSError:
        lw.WriteLine("Codex NX bridge is already running on %s:%s" % (HOST, PORT))
        return

    server.listen(5)
    server.settimeout(0.5)

    lw.WriteLine("Codex NX bridge started on %s:%s" % (HOST, PORT))
    lw.WriteLine("NX will stay busy while the bridge is active. Send command 'shutdown' to stop it.")

    try:
        while not _SHUTDOWN:
            try:
                conn, _addr = server.accept()
            except socket.timeout:
                continue
            _serve_client(conn)
    finally:
        server.close()
        lw.WriteLine("Codex NX bridge stopped.")

if __name__ == "__main__":
    main()
