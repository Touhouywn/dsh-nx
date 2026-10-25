using System;
using System.Collections;
using System.IO;
using System.Runtime.Remoting;
using System.Runtime.Remoting.Channels;
using System.Runtime.Remoting.Channels.Http;
using System.Runtime.Remoting.Lifetime;
using System.Runtime.Serialization.Formatters;
using System.Threading;

using NXOpen;
using NXOpen.UF;

public class NXCodexLiveBridgeServer
{
    public static readonly int Port = ReadIntEnvOrDefault("NX2512_LIVE_PORT", 25121);

    private static readonly object SyncRoot = new object();
    private static Thread serverThread;
    private static volatile bool isUnloaded;
    private static volatile bool serviceEnded = true;
    private static string logPath;

    public static Session TheSession;
    public static UFSession TheUFSession;
    public static UI TheUI;

    public static void Main(string[] args)
    {
        Start();
    }

    public static int Startup()
    {
        Start();
        return 0;
    }

    public static void Start()
    {
        lock (SyncRoot)
        {
            if (serverThread != null && serverThread.IsAlive)
            {
                WriteListing("Codex NX live bridge is already running on http://localhost:" + Port + "/NXOpenSession");
                return;
            }

            TheSession = Session.GetSession();
            TheUFSession = UFSession.GetUFSession();
            TheUI = UI.GetUI();
            isUnloaded = false;
            serviceEnded = false;

            string assemblyDir = Path.GetDirectoryName(System.Reflection.Assembly.GetExecutingAssembly().Location);
            logPath = Path.Combine(assemblyDir, "NXCodexLiveBridgeServer.log");
            SafeDeleteLog();

            serverThread = new Thread(new ThreadStart(Run));
            serverThread.Name = "NXCodexLiveBridgeServer";
            serverThread.IsBackground = true;
            serverThread.Start();
        }

        WriteListing("Codex NX live bridge start requested on http://localhost:" + Port + "/NXOpenSession");
    }

    private static void Run()
    {
        try
        {
            Log("Starting Codex NX live bridge.");
            LifetimeServices.LeaseTime = TimeSpan.FromDays(10000);

            SoapServerFormatterSinkProvider provider = new SoapServerFormatterSinkProvider();
            provider.TypeFilterLevel = TypeFilterLevel.Full;

            IDictionary props = new Hashtable();
            props["port"] = Port;
            props["name"] = "nx_codex_live_bridge_http";

            ChannelServices.RegisterChannel(new HttpChannel(props, null, provider), false);

            RemotingServices.Marshal(TheSession, "NXOpenSession");
            RemotingServices.Marshal(TheUFSession, "UFSession");
            RemotingServices.Marshal(TheUI, "UI");

            Log("Codex NX live bridge is listening on port " + Port + ".");
        }
        catch (Exception ex)
        {
            Log(ex.ToString());
        }

        while (!isUnloaded)
        {
            Thread.Sleep(1000);
        }

        serviceEnded = true;
        Log("Codex NX live bridge service ended.");
    }

    public static int GetUnloadOption(string dummy)
    {
        return (int)Session.LibraryUnloadOption.Explicitly;
    }

    public static void UnloadLibrary(string arg)
    {
        isUnloaded = true;

        DateTime deadline = DateTime.Now.AddSeconds(10);
        while (!serviceEnded && DateTime.Now < deadline)
        {
            Thread.Sleep(100);
        }

        Disconnect(TheSession, "Session");
        Disconnect(TheUFSession, "UFSession");
        Disconnect(TheUI, "UI");
        WriteListing("Codex NX live bridge stopped.");
    }

    private static void Disconnect(MarshalByRefObject obj, string name)
    {
        if (obj == null)
        {
            return;
        }

        try
        {
            Log("Disconnecting " + name + ".");
            RemotingServices.Disconnect(obj);
        }
        catch (Exception ex)
        {
            Log("Disconnect failed for " + name + ": " + ex);
        }
    }

    private static int ReadIntEnvOrDefault(string name, int defaultValue)
    {
        string value = Environment.GetEnvironmentVariable(name);
        if (String.IsNullOrWhiteSpace(value))
        {
            return defaultValue;
        }
        int parsed;
        if (!Int32.TryParse(value, out parsed))
        {
            return defaultValue;
        }
        return parsed;
    }

    private static void WriteListing(string message)
    {
        try
        {
            Session session = Session.GetSession();
            session.ListingWindow.Open();
            session.ListingWindow.WriteLine(message);
        }
        catch (Exception ex)
        {
            Log("ListingWindow write failed: " + ex);
        }
    }

    private static void Log(string message)
    {
        try
        {
            if (String.IsNullOrEmpty(logPath))
            {
                return;
            }

            using (StreamWriter writer = new StreamWriter(logPath, true))
            {
                writer.WriteLine(DateTime.Now.ToString("s") + " " + message);
            }
        }
        catch
        {
        }
    }

    private static void SafeDeleteLog()
    {
        try
        {
            if (!String.IsNullOrEmpty(logPath) && File.Exists(logPath))
            {
                File.Delete(logPath);
            }
        }
        catch
        {
        }
    }
}
