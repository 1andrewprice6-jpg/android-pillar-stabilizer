using UnityEngine;
using UnityEditor;
using System.IO;

namespace NeonProtocol.Editor
{
    /// <summary>
    /// Editor tool that auto-creates URP materials for each map theme.
    /// Assigns the correct custom shaders and textures based on the map directory structure.
    /// Access via: Neon Protocol > Material Factory
    /// </summary>
    public class MapMaterialFactory : EditorWindow
    {
        [MenuItem("Neon Protocol/Material Factory")]
        public static void ShowWindow()
        {
            GetWindow<MapMaterialFactory>("Material Factory");
        }

        private void OnGUI()
        {
            GUILayout.Label("Neon Protocol: Material Factory", EditorStyles.boldLabel);
            GUILayout.Space(10);

            GUILayout.Label("Creates materials using the custom NeonProtocol shaders");
            GUILayout.Label("and assigns textures from each map's Textures folder.");
            GUILayout.Space(10);

            if (GUILayout.Button("Generate ALL Map Materials"))
            {
                GenerateSpacelandMaterials();
                GenerateRaveMaterials();
                GenerateShaolinMaterials();
                GenerateRadioactiveMaterials();
                GenerateBeastMaterials();
                GenerateSharedMaterials();
                AssetDatabase.Refresh();
                Debug.Log("[MaterialFactory] All materials generated.");
            }

            GUILayout.Space(10);

            EditorGUILayout.BeginHorizontal();
            if (GUILayout.Button("Spaceland")) { GenerateSpacelandMaterials(); AssetDatabase.Refresh(); }
            if (GUILayout.Button("Rave")) { GenerateRaveMaterials(); AssetDatabase.Refresh(); }
            if (GUILayout.Button("Shaolin")) { GenerateShaolinMaterials(); AssetDatabase.Refresh(); }
            EditorGUILayout.EndHorizontal();

            EditorGUILayout.BeginHorizontal();
            if (GUILayout.Button("Radioactive")) { GenerateRadioactiveMaterials(); AssetDatabase.Refresh(); }
            if (GUILayout.Button("Beast")) { GenerateBeastMaterials(); AssetDatabase.Refresh(); }
            if (GUILayout.Button("Shared")) { GenerateSharedMaterials(); AssetDatabase.Refresh(); }
            EditorGUILayout.EndHorizontal();
        }

        // ── Helpers ──────────────────────────────────────────

        private Material CreateMaterial(string shaderName, string matName, string savePath)
        {
            Shader shader = Shader.Find(shaderName);
            if (shader == null)
            {
                Debug.LogWarning($"[MaterialFactory] Shader '{shaderName}' not found, falling back to URP/Lit");
                shader = Shader.Find("Universal Render Pipeline/Lit");
            }

            Material mat = new Material(shader) { name = matName };

            string dir = Path.GetDirectoryName(savePath);
            if (!Directory.Exists(Path.Combine(Application.dataPath, "..", dir)))
            {
                Directory.CreateDirectory(Path.Combine(Application.dataPath, "..", dir));
            }

            AssetDatabase.CreateAsset(mat, savePath);
            Debug.Log($"[MaterialFactory] Created: {savePath}");
            return mat;
        }

        private void AssignTexture(Material mat, string propertyName, string texturePath)
        {
            Texture2D tex = AssetDatabase.LoadAssetAtPath<Texture2D>(texturePath);
            if (tex != null)
            {
                mat.SetTexture(propertyName, tex);
            }
            else
            {
                Debug.LogWarning($"[MaterialFactory] Texture not found: {texturePath}");
            }
        }

        // ── Spaceland ────────────────────────────────────────

        private void GenerateSpacelandMaterials()
        {
            string matDir = "Assets/Maps/Spaceland/Materials";
            string texDir = "Assets/Maps/Spaceland/Textures";

            // Floor — NeonGrid shader
            var floor = CreateMaterial("NeonProtocol/NeonGrid", "Spaceland_Floor", $"{matDir}/Spaceland_Floor.mat");
            AssignTexture(floor, "_BaseMap", $"{texDir}/Floor_BaseMap.png");
            floor.SetColor("_GridColor", new Color(0, 1, 1, 1));
            floor.SetFloat("_GridSpacing", 1f);
            floor.SetFloat("_EmissionIntensity", 3f);
            floor.SetFloat("_PulseSpeed", 0.8f);
            EditorUtility.SetDirty(floor);

            // Wall — URP Lit with chrome look
            var wall = CreateMaterial("Universal Render Pipeline/Lit", "Spaceland_Wall", $"{matDir}/Spaceland_Wall.mat");
            AssignTexture(wall, "_BaseMap", $"{texDir}/Wall_BaseMap.png");
            AssignTexture(wall, "_BumpMap", $"{texDir}/Wall_Normal.png");
            wall.SetFloat("_Metallic", 0.8f);
            wall.SetFloat("_Smoothness", 0.7f);
            wall.SetColor("_EmissionColor", new Color(0, 0.5f, 0.5f) * 1.5f);
            wall.EnableKeyword("_EMISSION");
            EditorUtility.SetDirty(wall);
        }

        // ── Rave ─────────────────────────────────────────────

        private void GenerateRaveMaterials()
        {
            string matDir = "Assets/Maps/Rave/Materials";
            string texDir = "Assets/Maps/Rave/Textures";

            // Floor — Blacklight shader
            var floor = CreateMaterial("NeonProtocol/RaveBlacklight", "Rave_Floor", $"{matDir}/Rave_Floor.mat");
            AssignTexture(floor, "_BaseMap", $"{texDir}/Floor_BaseMap.png");
            AssignTexture(floor, "_BlacklightMap", $"{texDir}/Blacklight_Emission.png");
            floor.SetColor("_BlacklightColor", new Color(0.5f, 0, 1f));
            floor.SetFloat("_BlacklightIntensity", 4f);
            floor.SetFloat("_BeatSpeed", 2.5f);
            EditorUtility.SetDirty(floor);

            // Wall — Dark wood
            var wall = CreateMaterial("Universal Render Pipeline/Lit", "Rave_Wall", $"{matDir}/Rave_Wall.mat");
            AssignTexture(wall, "_BaseMap", $"{texDir}/Wall_BaseMap.png");
            AssignTexture(wall, "_BumpMap", $"{texDir}/Wall_Normal.png");
            wall.SetFloat("_Smoothness", 0.2f);
            EditorUtility.SetDirty(wall);
        }

        // ── Shaolin ──────────────────────────────────────────

        private void GenerateShaolinMaterials()
        {
            string matDir = "Assets/Maps/Shaolin/Materials";
            string texDir = "Assets/Maps/Shaolin/Textures";

            // Floor — Concrete
            var floor = CreateMaterial("Universal Render Pipeline/Lit", "Shaolin_Floor", $"{matDir}/Shaolin_Floor.mat");
            AssignTexture(floor, "_BaseMap", $"{texDir}/Floor_BaseMap.png");
            AssignTexture(floor, "_BumpMap", $"{texDir}/Floor_Normal.png");
            floor.SetFloat("_Smoothness", 0.15f);
            EditorUtility.SetDirty(floor);

            // Wall — Grimy brick
            var wall = CreateMaterial("Universal Render Pipeline/Lit", "Shaolin_Wall", $"{matDir}/Shaolin_Wall.mat");
            AssignTexture(wall, "_BaseMap", $"{texDir}/Wall_BaseMap.png");
            AssignTexture(wall, "_BumpMap", $"{texDir}/Wall_Normal.png");
            wall.SetFloat("_Smoothness", 0.1f);
            EditorUtility.SetDirty(wall);

            // Neon sign emission
            var neon = CreateMaterial("Universal Render Pipeline/Lit", "Shaolin_NeonSign", $"{matDir}/Shaolin_NeonSign.mat");
            AssignTexture(neon, "_EmissionMap", $"{texDir}/NeonSign_Emission.png");
            neon.SetColor("_EmissionColor", new Color(1f, 0.4f, 0) * 3f);
            neon.EnableKeyword("_EMISSION");
            EditorUtility.SetDirty(neon);
        }

        // ── Radioactive ──────────────────────────────────────

        private void GenerateRadioactiveMaterials()
        {
            string matDir = "Assets/Maps/Radioactive/Materials";
            string texDir = "Assets/Maps/Radioactive/Textures";

            // Floor — Radiation shader
            var floor = CreateMaterial("NeonProtocol/RadiationGlow", "Radioactive_Floor", $"{matDir}/Radioactive_Floor.mat");
            AssignTexture(floor, "_BaseMap", $"{texDir}/Floor_BaseMap.png");
            AssignTexture(floor, "_EmissionMap", $"{texDir}/ToxicPool_Emission.png");
            AssignTexture(floor, "_NormalMap", $"{texDir}/Floor_Normal.png");
            floor.SetColor("_EmissionColor", new Color(0.2f, 1f, 0.1f));
            floor.SetFloat("_EmissionIntensity", 3f);
            floor.SetFloat("_DesaturationAmount", 0.5f);
            EditorUtility.SetDirty(floor);

            // Wall — Desaturated
            var wall = CreateMaterial("Universal Render Pipeline/Lit", "Radioactive_Wall", $"{matDir}/Radioactive_Wall.mat");
            AssignTexture(wall, "_BaseMap", $"{texDir}/Wall_BaseMap.png");
            AssignTexture(wall, "_BumpMap", $"{texDir}/Wall_Normal.png");
            wall.SetFloat("_Smoothness", 0.15f);
            EditorUtility.SetDirty(wall);
        }

        // ── Beast ────────────────────────────────────────────

        private void GenerateBeastMaterials()
        {
            string matDir = "Assets/Maps/Beast/Materials";
            string texDir = "Assets/Maps/Beast/Textures";

            // Floor — Organic shader
            var floor = CreateMaterial("NeonProtocol/BeastOrganic", "Beast_Floor", $"{matDir}/Beast_Floor.mat");
            AssignTexture(floor, "_BaseMap", $"{texDir}/Floor_BaseMap.png");
            AssignTexture(floor, "_EmissionMap", $"{texDir}/Spore_Emission.png");
            AssignTexture(floor, "_NormalMap", $"{texDir}/Floor_Normal.png");
            floor.SetColor("_EmissionColor", new Color(0.8f, 0.1f, 0.6f));
            floor.SetFloat("_EmissionIntensity", 3f);
            floor.SetFloat("_PulseSpeed", 1.2f);
            floor.SetFloat("_Smoothness", 0.7f);
            EditorUtility.SetDirty(floor);

            // Wall — Alien biomechanical
            var wall = CreateMaterial("NeonProtocol/BeastOrganic", "Beast_Wall", $"{matDir}/Beast_Wall.mat");
            AssignTexture(wall, "_BaseMap", $"{texDir}/Wall_BaseMap.png");
            AssignTexture(wall, "_VeinMap", $"{texDir}/Wall_BaseMap.png"); // Reuse as vein overlay
            AssignTexture(wall, "_NormalMap", $"{texDir}/Wall_Normal.png");
            wall.SetColor("_BaseColor", new Color(0.2f, 0.06f, 0.12f));
            wall.SetFloat("_Smoothness", 0.5f);
            wall.SetFloat("_FleshDisplacement", 0.02f);
            EditorUtility.SetDirty(wall);
        }

        // ── Shared ───────────────────────────────────────────

        private void GenerateSharedMaterials()
        {
            string matDir = "Assets/Shared/Materials";

            // Hologram enemy material
            var holo = CreateMaterial("NeonProtocol/NeonHologram", "Shared_Hologram", $"{matDir}/Shared_Hologram.mat");
            holo.SetColor("_BaseColor", new Color(1, 0, 1, 0.5f));
            holo.SetFloat("_EmissionIntensity", 2f);
            holo.SetColor("_FresnelColor", new Color(0, 1, 1));
            EditorUtility.SetDirty(holo);

            // Default grid material
            var grid = CreateMaterial("NeonProtocol/NeonGrid", "Shared_Grid", $"{matDir}/Shared_Grid.mat");
            AssignTexture(grid, "_BaseMap", "Assets/Shared/Textures/Default_Grid.png");
            grid.SetColor("_GridColor", new Color(0.5f, 0.5f, 0.6f));
            grid.SetFloat("_EmissionIntensity", 1f);
            EditorUtility.SetDirty(grid);
        }
    }
}
