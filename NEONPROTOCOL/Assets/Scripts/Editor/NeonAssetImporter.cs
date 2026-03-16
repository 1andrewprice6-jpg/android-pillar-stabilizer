using UnityEngine;
using UnityEditor;
using System.IO;
using System.Collections.Generic;

// NEON PROTOCOL ASSET PIPELINE
// Role: Copilot (Integrator)
// Function: Auto-process imported assets for mobile optimization and URP compliance.

public class NeonAssetImporter : EditorWindow
{
    private GameObject _neonPoolerPrefab;
    private string _targetTag = "Enemy";
    private int _defaultPoolSize = 20;

    [MenuItem("Neon Protocol/Asset Importer")]
    public static void ShowWindow()
    {
        GetWindow<NeonAssetImporter>("Neon Importer");
    }

    private void OnGUI()
    {
        GUILayout.Label("Neon Protocol: Asset Integration Pipeline", EditorStyles.boldLabel);
        GUILayout.Space(10);

        GUILayout.Label("1. Asset Processing", EditorStyles.boldLabel);
        if (GUILayout.Button("Optimize Selected Models for Mobile (URP)"))
        {
            ProcessSelectedModels();
        }

        GUILayout.Space(20);
        GUILayout.Label("2. Pool Registration", EditorStyles.boldLabel);
        _neonPoolerPrefab = (GameObject)EditorGUILayout.ObjectField("Pooler Prefab/Instance", _neonPoolerPrefab, typeof(GameObject), true);
        _targetTag = EditorGUILayout.TextField("Pool Tag", _targetTag);
        _defaultPoolSize = EditorGUILayout.IntField("Pool Size", _defaultPoolSize);

        if (GUILayout.Button("Register Selected Prefab to Pool"))
        {
            RegisterToPool();
        }
    }

    private void ProcessSelectedModels()
    {
        foreach (var obj in Selection.objects)
        {
            string path = AssetDatabase.GetAssetPath(obj);
            if (string.IsNullOrEmpty(path)) continue;

            ModelImporter importer = AssetImporter.GetAtPath(path) as ModelImporter;
            if (importer != null)
            {
                // Mobile Optimization Settings
                importer.meshCompression = ModelImporterMeshCompression.Medium;
                importer.optimizeMesh = true;
                importer.isReadable = false; // Important for memory
                importer.importBlendShapes = false;
                importer.weldVertices = true;
                
                // URP Material Handling (Basic)
                importer.materialImportMode = ModelImporterMaterialImportMode.ImportStandard;
                
                importer.SaveAndReimport();
                Debug.Log($"[NeonImporter] Optimized Model: {obj.name}");
            }
            
            // Texture Optimization
            TextureImporter texImporter = AssetImporter.GetAtPath(path) as TextureImporter;
            if (texImporter != null)
            {
                texImporter.textureCompression = TextureImporterCompression.Compressed;
                texImporter.maxTextureSize = 2048; // Cap for mobile
                texImporter.SaveAndReimport();
                 Debug.Log($"[NeonImporter] Optimized Texture: {obj.name}");
            }
        }
    }

    private void RegisterToPool()
    {
        if (_neonPoolerPrefab == null)
        {
            Debug.LogError("[NeonImporter] Please assign the NeonPooler prefab or instance.");
            return;
        }

        // Note: Direct modification of Prefabs via script requires SerializedObject
        // This is a simplified implementation for the Editor Window
        
        var poolerScript = _neonPoolerPrefab.GetComponent<NeonProtocol.Core.Systems.NeonPooler>();
        if (poolerScript == null)
        {
             Debug.LogError("[NeonImporter] Target object does not have NeonPooler component.");
             return;
        }

        GameObject selectedPrefab = Selection.activeGameObject;
        if (selectedPrefab == null)
        {
             Debug.LogError("[NeonImporter] Please select a Prefab in the project view.");
             return;
        }

        // Create a new pool entry
        NeonProtocol.Core.Systems.NeonPooler.Pool newPool = new NeonProtocol.Core.Systems.NeonPooler.Pool
        {
            tag = _targetTag,
            prefab = selectedPrefab,
            size = _defaultPoolSize
        };

        // We need to use SerializedObject to modify it permanently in Editor
        SerializedObject so = new SerializedObject(poolerScript);
        SerializedProperty poolsProp = so.FindProperty("pools");
        
        int index = poolsProp.arraySize;
        poolsProp.InsertArrayElementAtIndex(index);
        SerializedProperty element = poolsProp.GetArrayElementAtIndex(index);
        
        element.FindPropertyRelative("tag").stringValue = _targetTag;
        element.FindPropertyRelative("prefab").objectReferenceValue = selectedPrefab;
        element.FindPropertyRelative("size").intValue = _defaultPoolSize;

        so.ApplyModifiedProperties();
        
        Debug.Log($"[NeonImporter] Registered {selectedPrefab.name} to Pooler with tag '{_targetTag}'.");
    }
}
