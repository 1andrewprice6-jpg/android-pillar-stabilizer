using UnityEngine;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine.SceneManagement;
using UnityEngine.Rendering;
using System.IO;

namespace NeonProtocol.Editor
{
    /// <summary>
    /// Editor tool that bootstraps properly configured scenes for each map theme.
    /// Creates scenes with correct lighting, fog, post-processing, and core game objects.
    /// Access via: Neon Protocol > Scene Bootstrapper
    /// </summary>
    public class NeonSceneBootstrapper : EditorWindow
    {
        private enum MapType { Spaceland, Rave, Shaolin, Radioactive, Beast }

        private MapType _selectedMap = MapType.Spaceland;
        private bool _includePlayerSpawn = true;
        private bool _includePooler = true;
        private bool _includeLighting = true;

        [MenuItem("Neon Protocol/Scene Bootstrapper")]
        public static void ShowWindow()
        {
            GetWindow<NeonSceneBootstrapper>("Scene Bootstrapper");
        }

        private void OnGUI()
        {
            GUILayout.Label("Neon Protocol: Scene Bootstrapper", EditorStyles.boldLabel);
            GUILayout.Space(10);

            _selectedMap = (MapType)EditorGUILayout.EnumPopup("Map Theme", _selectedMap);
            _includePlayerSpawn = EditorGUILayout.Toggle("Include Player Spawn", _includePlayerSpawn);
            _includePooler = EditorGUILayout.Toggle("Include NeonPooler", _includePooler);
            _includeLighting = EditorGUILayout.Toggle("Configure Lighting", _includeLighting);

            GUILayout.Space(10);

            if (GUILayout.Button($"Create {_selectedMap} Scene"))
            {
                CreateMapScene(_selectedMap);
            }

            GUILayout.Space(20);
            if (GUILayout.Button("Create ALL Map Scenes"))
            {
                foreach (MapType map in System.Enum.GetValues(typeof(MapType)))
                {
                    CreateMapScene(map);
                }
                Debug.Log("[SceneBootstrap] All 5 map scenes created successfully.");
            }
        }

        private void CreateMapScene(MapType map)
        {
            string mapName = map.ToString();
            string scenePath = $"Assets/Maps/{mapName}/Scenes/{mapName}_Main.unity";
            string fullDir = Path.Combine(Application.dataPath, $"Maps/{mapName}/Scenes");
            Directory.CreateDirectory(fullDir);

            // Create new scene
            Scene scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);

            // ── Lighting ─────────────────────────────────────────
            if (_includeLighting)
            {
                ConfigureLighting(map);
            }

            // ── Core Objects ─────────────────────────────────────

            // Directional Light
            var lightObj = new GameObject("Directional Light");
            var light = lightObj.AddComponent<Light>();
            light.type = LightType.Directional;
            light.intensity = GetLightIntensity(map);
            light.color = GetLightColor(map);
            light.shadows = LightShadows.Soft;
            lightObj.transform.rotation = Quaternion.Euler(50, -30, 0);

            // Ground plane
            var ground = GameObject.CreatePrimitive(PrimitiveType.Plane);
            ground.name = $"{mapName}_Ground";
            ground.transform.localScale = new Vector3(50, 1, 50);
            ground.isStatic = true;

            // ── Player Spawn ─────────────────────────────────────
            if (_includePlayerSpawn)
            {
                var spawn = new GameObject("PlayerSpawn");
                spawn.transform.position = new Vector3(0, 1, 0);
                spawn.tag = "Respawn";

                // Visual indicator in editor
                var indicator = GameObject.CreatePrimitive(PrimitiveType.Capsule);
                indicator.name = "SpawnIndicator";
                indicator.transform.SetParent(spawn.transform);
                indicator.transform.localPosition = Vector3.zero;
                var rend = indicator.GetComponent<Renderer>();
                rend.sharedMaterial = new Material(Shader.Find("Universal Render Pipeline/Lit"));
                rend.sharedMaterial.color = Color.green;
            }

            // ── NeonPooler ───────────────────────────────────────
            if (_includePooler)
            {
                var poolerObj = new GameObject("NeonPooler");
                poolerObj.AddComponent<NeonProtocol.Core.Systems.NeonPooler>();
            }

            // ── Map-Specific Objects ─────────────────────────────
            CreateMapSpecificObjects(map);

            // ── Game Manager ─────────────────────────────────────
            var gameManager = new GameObject("GameManager");
            gameManager.AddComponent<AAAConfigurator>();

            // ── Post-Processing Volume (placeholder) ─────────────
            var ppVolume = new GameObject("PostProcessVolume");
            var volume = ppVolume.AddComponent<Volume>();
            volume.isGlobal = true;
            volume.weight = 1f;

            // Save scene
            EditorSceneManager.SaveScene(scene, scenePath);
            Debug.Log($"[SceneBootstrap] Created scene: {scenePath}");
        }

        private void ConfigureLighting(MapType map)
        {
            switch (map)
            {
                case MapType.Spaceland:
                    RenderSettings.ambientLight = new Color(0.05f, 0.05f, 0.1f);
                    RenderSettings.fogColor = new Color(0.02f, 0.02f, 0.05f);
                    RenderSettings.fogDensity = 0.015f;
                    break;
                case MapType.Rave:
                    RenderSettings.ambientLight = new Color(0.03f, 0.01f, 0.06f);
                    RenderSettings.fogColor = new Color(0.02f, 0, 0.04f);
                    RenderSettings.fogDensity = 0.03f;
                    break;
                case MapType.Shaolin:
                    RenderSettings.ambientLight = new Color(0.08f, 0.06f, 0.04f);
                    RenderSettings.fogColor = new Color(0.06f, 0.05f, 0.04f);
                    RenderSettings.fogDensity = 0.01f;
                    break;
                case MapType.Radioactive:
                    RenderSettings.ambientLight = new Color(0.08f, 0.09f, 0.06f);
                    RenderSettings.fogColor = new Color(0.05f, 0.06f, 0.03f);
                    RenderSettings.fogDensity = 0.025f;
                    break;
                case MapType.Beast:
                    RenderSettings.ambientLight = new Color(0.04f, 0.01f, 0.03f);
                    RenderSettings.fogColor = new Color(0.03f, 0, 0.02f);
                    RenderSettings.fogDensity = 0.035f;
                    break;
            }
            RenderSettings.fog = true;
            RenderSettings.fogMode = FogMode.ExponentialSquared;
        }

        private float GetLightIntensity(MapType map)
        {
            switch (map)
            {
                case MapType.Spaceland: return 0.6f;
                case MapType.Rave: return 0.3f;
                case MapType.Shaolin: return 0.8f;
                case MapType.Radioactive: return 0.7f;
                case MapType.Beast: return 0.4f;
                default: return 1f;
            }
        }

        private Color GetLightColor(MapType map)
        {
            switch (map)
            {
                case MapType.Spaceland: return new Color(0.7f, 0.8f, 1f);
                case MapType.Rave: return new Color(0.4f, 0.2f, 0.8f);
                case MapType.Shaolin: return new Color(1f, 0.9f, 0.7f);
                case MapType.Radioactive: return new Color(0.8f, 0.9f, 0.7f);
                case MapType.Beast: return new Color(0.6f, 0.3f, 0.5f);
                default: return Color.white;
            }
        }

        private void CreateMapSpecificObjects(MapType map)
        {
            var mapRoot = new GameObject($"{map}_Root");

            switch (map)
            {
                case MapType.Spaceland:
                    CreateChild(mapRoot, "ArcadeMachines_Placeholder");
                    CreateChild(mapRoot, "UFO_Skybox_Trigger");
                    CreateChild(mapRoot, "NeonSignGroup");
                    break;
                case MapType.Rave:
                    CreateChild(mapRoot, "TurntableStation");
                    CreateChild(mapRoot, "GlowingFloraGroup");
                    CreateChild(mapRoot, "AudioVisualizerVolume");
                    break;
                case MapType.Shaolin:
                    CreateChild(mapRoot, "DojoInterior");
                    CreateChild(mapRoot, "SubwayEntrance");
                    CreateChild(mapRoot, "NeonSignStreet");
                    break;
                case MapType.Radioactive:
                    CreateChild(mapRoot, "ToxicPoolZone");
                    CreateChild(mapRoot, "CraftingStation");
                    CreateChild(mapRoot, "HazmatZombieSpawner");
                    break;
                case MapType.Beast:
                    CreateChild(mapRoot, "AlienPodCluster");
                    CreateChild(mapRoot, "CryptidSpawnNest");
                    CreateChild(mapRoot, "WallClimbZone");
                    break;
            }
        }

        private GameObject CreateChild(GameObject parent, string name)
        {
            var child = new GameObject(name);
            child.transform.SetParent(parent.transform);
            return child;
        }
    }
}
