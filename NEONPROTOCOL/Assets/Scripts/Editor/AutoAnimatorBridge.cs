using UnityEngine;
using UnityEditor;
using System.IO;

namespace NeonProtocol.Editor
{
    public class AutoAnimatorBridge : AssetPostprocessor
    {
        private const string ANIM_FOLDER = "Animations";
        private const string READY_FOLDER = "Animations/Ready";

        private void OnPreprocessModel()
        {
            // Only process files inside our designated Animations folder
            if (!assetPath.Contains(ANIM_FOLDER)) return;

            ModelImporter importer = assetImporter as ModelImporter;
            if (importer == null) return;

            // 1. Force Humanoid Rig for Mixamo skeletons
            importer.animationType = ModelImporterAnimationType.Humanoid;
            importer.avatarSetup = ModelImporterAvatarSetup.CreateFromThisModel;
            
            Debug.Log($"[AutoAnimator] Rigged {Path.GetFileName(assetPath)} as Humanoid.");
        }

        private void OnPostprocessModel(GameObject g)
        {
            if (!assetPath.Contains(ANIM_FOLDER)) return;
            if (assetPath.Contains(READY_FOLDER)) return; // Avoid infinite loop if extracting to subfolder

            string fileName = Path.GetFileNameWithoutExtension(assetPath);
            Object[] assets = AssetDatabase.LoadAllAssetsAtPath(assetPath);

            foreach (Object asset in assets)
            {
                if (asset is AnimationClip)
                {
                    AnimationClip originalClip = asset as AnimationClip;
                    if (originalClip.name.Contains("__preview__")) continue;

                    // 2. Extract and Save Clip
                    AnimationClip newClip = new AnimationClip();
                    EditorUtility.CopySerialized(originalClip, newClip);

                    // 3. Auto-Looping Logic
                    if (fileName.Contains("Idle", System.StringComparison.OrdinalIgnoreCase) ||
                        fileName.Contains("Run", System.StringComparison.OrdinalIgnoreCase) ||
                        fileName.Contains("Walk", System.StringComparison.OrdinalIgnoreCase))
                    {
                        var settings = AnimationUtility.GetAnimationClipSettings(newClip);
                        settings.loopTime = true;
                        AnimationUtility.SetAnimationClipSettings(newClip, settings);
                        Debug.Log($"[AutoAnimator] Looping enabled for {fileName}");
                    }

                    // Ensure Directory Exists
                    if (!Directory.Exists(Application.dataPath + "/" + READY_FOLDER))
                    {
                        Directory.CreateDirectory(Application.dataPath + "/" + READY_FOLDER);
                    }

                    string outPath = "Assets/" + READY_FOLDER + "/" + fileName + ".anim";
                    AssetDatabase.CreateAsset(newClip, outPath);
                    Debug.Log($"[AutoAnimator] Extracted {fileName}.anim to {READY_FOLDER}");
                }
            }
        }
    }
}