using UnityEditor;
using UnityEngine;
using System.IO;

namespace NeonProtocol.Editor
{
    public class AAA_AssetCompressor : EditorWindow
    {
        [MenuItem("Neon Protocol/Forge Asset Bundles (Android)")]
        static void BuildAllAssetBundles()
        {
            // Define the "Solid" extraction node within your project
            string assetBundleDirectory = "Assets/StreamingAssets";

            // Create the directory if the Matrix hasn't generated it yet
            if (!Directory.Exists(Application.dataPath + "/StreamingAssets"))
            {
                Directory.CreateDirectory(Application.dataPath + "/StreamingAssets");
                Debug.Log("[SRA-01] StreamingAssets node created.");
            }

            // Execute the LZ4 Compression Protocol targeted strictly for Android
            // ChunkBasedCompression = LZ4 (Optimal for fast loading on mobile)
            BuildPipeline.BuildAssetBundles(
                assetBundleDirectory, 
                BuildAssetBundleOptions.ChunkBasedCompression | BuildAssetBundleOptions.StrictMode, 
                BuildTarget.Android
            );

            Debug.Log("[SRA-01] Asset Bundles Forged Successfully. LZ4 Compression Applied. Ready for APK compilation.");
        }
    }
}