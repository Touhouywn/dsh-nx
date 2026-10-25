import os

import NXOpen


APPLICATION_DIR = os.path.dirname(os.path.abspath(__file__))
RUNTIME_ROOT = os.path.dirname(APPLICATION_DIR)
PLUGIN_ROOT = os.path.dirname(RUNTIME_ROOT)
SERVER_DLL = os.environ.get(
    "NX2512_LIVE_BRIDGE_DLL",
    os.path.join(RUNTIME_ROOT, "startup", "NXCodexLiveBridgeServer.dll"),
)
SERVER_CLASS = "NXCodexLiveBridgeServer"


def main():
    session = NXOpen.Session.GetSession()
    session.ListingWindow.Open()

    if not os.path.isfile(SERVER_DLL):
        session.ListingWindow.WriteLine("Codex live bridge DLL is missing: " + SERVER_DLL)
        session.ListingWindow.WriteLine(
            "Run: powershell -NoProfile -ExecutionPolicy Bypass -File "
            + os.path.join(PLUGIN_ROOT, "scripts", "build_dotnet_bridge.ps1")
        )
        return

    session.Execute(SERVER_DLL, SERVER_CLASS, "Start", [])
    session.ListingWindow.WriteLine("Codex live bridge requested. Test with scripts\\nx_live_cli.ps1 -Command ping.")


if __name__ == "__main__":
    main()
