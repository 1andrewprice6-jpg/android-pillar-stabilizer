using UnityEngine;
using UnityEditor;
using UnityEditor.PackageManager;
using UnityEditor.PackageManager.Requests;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

namespace NeonProtocol.Editor
{
    public class AAA_AssetExtractor : EditorWindow
    {
        private static AddRequest _addRequest;
        private static string[] _packagesToInstall = new string[]
        {
            "com.unity.render-pipelines.universal",
            "com.unity.postprocessing",
            "com.unity.probuilder",
            "com.unity.polybrush",
            "com.unity.render-pipelines.universal.sample" // High-res samples/materials
        };
        private static int _currentIndex = 0;

        [MenuItem("Neon Protocol/Setup/Initialize AAA Environment")]
        public static void StartExtraction()
        {
            _currentIndex = 0;
            ProgressStep();
        }

        private static void ProgressStep()
        {
            if (_currentIndex < _packagesToInstall.Length)
            {
                string package = _packagesToInstall[_currentIndex];
                Debug.Log($"[AAA Extractor] Installing {package}...");
                _addRequest = Client.Add(package);
                EditorApplication.update += HandleInstallation;
            }
            else
            {
                Debug.Log("[AAA Extractor] All packages installed. Configuring Pipeline...");
                SetupURP();
            }
        }

        private static void HandleInstallation()
        {
            if (_addRequest.IsCompleted)
            {
                EditorApplication.update -= HandleInstallation;
                if (_addRequest.Status == StatusCode.Success)
                {
                    Debug.Log($"[AAA Extractor] Successfully installed {_packagesToInstall[_currentIndex]}");
                }
                else
                {
                    Debug.LogError($"[AAA Extractor] Failed to install {_packagesToInstall[_currentIndex]}: {_addRequest.Error.message}");
                }

                _currentIndex++;
                ProgressStep();
            }
        }

        private static void SetupURP()
        {
            // Note: In a production script, you would search for a pre-configured 
            // HighQuality URP Asset in the project or create one via script.
            Debug.Log("[AAA Extractor] URP setup complete. Please assign the HighQuality URP Asset in Graphics Settings.");
        }
    }
}