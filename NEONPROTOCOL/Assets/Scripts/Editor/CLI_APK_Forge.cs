using UnityEditor;
using UnityEngine;
using System.Linq;
using System.IO;

public class CLI_APK_Forge
{
    // This is the static method the terminal will target
    public static void BuildAndroidAPK()
    {
        Debug.Log("[SRA-01] Initializing Headless CLI Build Sequence...");

        // Automatically find all scenes checked in the Build Settings
        string[] scenes = EditorBuildSettings.scenes.Where(s => s.enabled).Select(s => s.path).ToArray();
        
        // Ensure the output directory exists
        string buildDirectory = "Builds";
        if (!Directory.Exists(buildDirectory))
        {
            Directory.CreateDirectory(buildDirectory);
        }

        string buildPath = buildDirectory + "/NeonProtocol.apk";

        BuildPlayerOptions buildOptions = new BuildPlayerOptions
        {
            scenes = scenes,
            locationPathName = buildPath,
            target = BuildTarget.Android,
            options = BuildOptions.None // Change to BuildOptions.CompressWithLz4 if you want faster iteration
        };

        // Execute the forge
        var report = BuildPipeline.BuildPlayer(buildOptions);
        
        if (report.summary.result == UnityEditor.Build.Reporting.BuildResult.Succeeded)
        {
            Debug.Log("[SRA-01] APK Forged Successfully! Size: " + (report.summary.totalSize / (1024 * 1024)) + " MB");
            Debug.Log("[SRA-01] Path: " + report.summary.outputPath);
        }
        else
        {
            Debug.LogError("[SRA-01] CRITICAL ERROR: APK Forge Failed. Check compiler logs.");
            EditorApplication.Exit(1); // Force exit with error code for CI/CD pipelines
        }
    }

    public static void ExportAndroidProject()
    {
        Debug.Log("[SRA-01] Initializing Android Studio Project Export...");

        string[] scenes = EditorBuildSettings.scenes.Where(s => s.enabled).Select(s => s.path).ToArray();
        string exportPath = "Builds/AndroidProject";

        if (Directory.Exists(exportPath))
        {
            Directory.Delete(exportPath, true);
        }

        BuildPlayerOptions buildOptions = new BuildPlayerOptions
        {
            scenes = scenes,
            locationPathName = exportPath,
            target = BuildTarget.Android,
            options = BuildOptions.AcceptExternalModificationsToPlayer // This flag triggers project export
        };

        var report = BuildPipeline.BuildPlayer(buildOptions);

        if (report.summary.result == UnityEditor.Build.Reporting.BuildResult.Succeeded)
        {
            Debug.Log("[SRA-01] Android Project Exported Successfully!");
            Debug.Log("[SRA-01] Location: " + Path.GetFullPath(exportPath));
        }
        else
        {
            Debug.LogError("[SRA-01] Export Failed.");
            if (Application.isBatchMode) EditorApplication.Exit(1);
        }
    }
}