using UnityEngine;
using UnityEditor;
using System.IO;

namespace NeonProtocol.Editor
{
    /// <summary>
    /// Editor tool that procedurally generates tileable textures for all map themes.
    /// Provides a one-click pipeline to regenerate textures from within Unity.
    /// Access via: Neon Protocol > Generate Textures
    /// </summary>
    public class NeonTextureGenerator : EditorWindow
    {
        private int _resolution = 512;
        private bool _generateNormals = true;
        private bool _generateEmission = true;

        [MenuItem("Neon Protocol/Generate Textures")]
        public static void ShowWindow()
        {
            GetWindow<NeonTextureGenerator>("Neon Texture Generator");
        }

        private void OnGUI()
        {
            GUILayout.Label("Neon Protocol: Procedural Texture Generator", EditorStyles.boldLabel);
            GUILayout.Space(10);

            _resolution = EditorGUILayout.IntPopup("Resolution", _resolution,
                new[] { "256", "512", "1024", "2048" },
                new[] { 256, 512, 1024, 2048 });

            _generateNormals = EditorGUILayout.Toggle("Generate Normal Maps", _generateNormals);
            _generateEmission = EditorGUILayout.Toggle("Generate Emission Maps", _generateEmission);

            GUILayout.Space(10);
            GUILayout.Label("Per-Map Generation", EditorStyles.boldLabel);

            if (GUILayout.Button("Generate ALL Map Textures"))
            {
                GenerateSpaceland();
                GenerateRave();
                GenerateShaolin();
                GenerateRadioactive();
                GenerateBeast();
                GenerateShared();
                AssetDatabase.Refresh();
                Debug.Log("[NeonTexGen] All textures generated successfully.");
            }

            GUILayout.Space(5);

            EditorGUILayout.BeginHorizontal();
            if (GUILayout.Button("Spaceland")) { GenerateSpaceland(); AssetDatabase.Refresh(); }
            if (GUILayout.Button("Rave")) { GenerateRave(); AssetDatabase.Refresh(); }
            if (GUILayout.Button("Shaolin")) { GenerateShaolin(); AssetDatabase.Refresh(); }
            EditorGUILayout.EndHorizontal();

            EditorGUILayout.BeginHorizontal();
            if (GUILayout.Button("Radioactive")) { GenerateRadioactive(); AssetDatabase.Refresh(); }
            if (GUILayout.Button("Beast")) { GenerateBeast(); AssetDatabase.Refresh(); }
            if (GUILayout.Button("Shared")) { GenerateShared(); AssetDatabase.Refresh(); }
            EditorGUILayout.EndHorizontal();
        }

        // ── Helpers ──────────────────────────────────────────────

        private Texture2D CreateTexture(string name)
        {
            return new Texture2D(_resolution, _resolution, TextureFormat.RGBA32, true) { name = name };
        }

        private void SaveTexture(Texture2D tex, string relativePath)
        {
            string fullPath = Path.Combine(Application.dataPath, relativePath);
            Directory.CreateDirectory(Path.GetDirectoryName(fullPath));
            byte[] png = tex.EncodeToPNG();
            File.WriteAllBytes(fullPath, png);
            Debug.Log($"[NeonTexGen] Saved {relativePath}");
            Object.DestroyImmediate(tex);
        }

        private Texture2D GenerateGrid(Color bg, Color line, int spacing, int thickness)
        {
            var tex = CreateTexture("Grid");
            for (int y = 0; y < _resolution; y++)
            {
                for (int x = 0; x < _resolution; x++)
                {
                    bool isLine = (x % spacing < thickness) || (y % spacing < thickness);
                    tex.SetPixel(x, y, isLine ? line : bg);
                }
            }
            tex.Apply();
            return tex;
        }

        private Texture2D GenerateNoise(System.Func<float, Color> colorFunc, int scale = 8)
        {
            var tex = CreateTexture("Noise");
            float[,] grid = new float[scale + 1, scale + 1];
            for (int gy = 0; gy <= scale; gy++)
                for (int gx = 0; gx <= scale; gx++)
                    grid[gy, gx] = Random.value;

            for (int y = 0; y < _resolution; y++)
            {
                for (int x = 0; x < _resolution; x++)
                {
                    float gx = (float)x / _resolution * scale;
                    float gy = (float)y / _resolution * scale;
                    int ix = Mathf.FloorToInt(gx) % scale;
                    int iy = Mathf.FloorToInt(gy) % scale;
                    float fx = gx - Mathf.Floor(gx);
                    float fy = gy - Mathf.Floor(gy);

                    float v00 = grid[iy, ix];
                    float v10 = grid[iy, (ix + 1) % scale];
                    float v01 = grid[(iy + 1) % scale, ix];
                    float v11 = grid[(iy + 1) % scale, (ix + 1) % scale];
                    float v = Mathf.Lerp(
                        Mathf.Lerp(v00, v10, fx),
                        Mathf.Lerp(v01, v11, fx),
                        fy);

                    tex.SetPixel(x, y, colorFunc(v));
                }
            }
            tex.Apply();
            return tex;
        }

        private Texture2D GenerateNormalFromHeight(Texture2D heightTex)
        {
            var normal = CreateTexture("Normal");
            int w = heightTex.width;
            int h = heightTex.height;
            for (int y = 0; y < h; y++)
            {
                for (int x = 0; x < w; x++)
                {
                    float left = heightTex.GetPixel((x - 1 + w) % w, y).grayscale;
                    float right = heightTex.GetPixel((x + 1) % w, y).grayscale;
                    float up = heightTex.GetPixel(x, (y + 1) % h).grayscale;
                    float down = heightTex.GetPixel(x, (y - 1 + h) % h).grayscale;
                    float dx = (left - right) * 0.5f + 0.5f;
                    float dy = (down - up) * 0.5f + 0.5f;
                    normal.SetPixel(x, y, new Color(dx, dy, 1f));
                }
            }
            normal.Apply();
            return normal;
        }

        // ── Map Generators ───────────────────────────────────────

        private void GenerateSpaceland()
        {
            EditorUtility.DisplayProgressBar("NeonTexGen", "Generating Spaceland...", 0.1f);

            var floor = GenerateGrid(new Color(0.04f, 0.04f, 0.06f), new Color(0, 1, 1, 0.8f), 64, 2);
            SaveTexture(floor, "Maps/Spaceland/Textures/Floor_BaseMap.png");

            if (_generateEmission)
            {
                var emit = GenerateGrid(Color.black, new Color(0, 1, 1, 1), 64, 3);
                SaveTexture(emit, "Maps/Spaceland/Textures/Floor_Emission.png");
            }

            var wall = GenerateNoise(v => new Color(v * 0.6f + 0.3f, v * 0.6f + 0.3f, v * 0.65f + 0.3f), 6);
            SaveTexture(wall, "Maps/Spaceland/Textures/Wall_BaseMap.png");

            if (_generateNormals)
            {
                var floorN = GenerateGrid(new Color(0.04f, 0.04f, 0.06f), Color.white, 64, 2);
                SaveTexture(GenerateNormalFromHeight(floorN), "Maps/Spaceland/Textures/Floor_Normal.png");
                Object.DestroyImmediate(floorN);

                var wallH = GenerateNoise(v => new Color(v, v, v), 6);
                SaveTexture(GenerateNormalFromHeight(wallH), "Maps/Spaceland/Textures/Wall_Normal.png");
                Object.DestroyImmediate(wallH);
            }

            EditorUtility.ClearProgressBar();
        }

        private void GenerateRave()
        {
            EditorUtility.DisplayProgressBar("NeonTexGen", "Generating Rave...", 0.3f);

            var floor = GenerateNoise(v => new Color(v * 0.1f + 0.04f, v * 0.13f, v * 0.1f + 0.02f), 8);
            SaveTexture(floor, "Maps/Rave/Textures/Floor_BaseMap.png");

            var wall = GenerateNoise(v => new Color(v * 0.1f + 0.08f, v * 0.08f + 0.04f, v * 0.07f + 0.02f), 4);
            SaveTexture(wall, "Maps/Rave/Textures/Wall_BaseMap.png");

            if (_generateEmission)
            {
                var emit = GenerateNoise(v => {
                    float r = Mathf.Sin(v * Mathf.PI * 4f) * 0.5f + 0.5f;
                    return new Color(r * 0.7f, 0, r, Mathf.Clamp01(r * 0.8f));
                }, 12);
                SaveTexture(emit, "Maps/Rave/Textures/Blacklight_Emission.png");
            }

            EditorUtility.ClearProgressBar();
        }

        private void GenerateShaolin()
        {
            EditorUtility.DisplayProgressBar("NeonTexGen", "Generating Shaolin...", 0.5f);

            var floor = GenerateNoise(v => new Color(v * 0.3f + 0.35f, v * 0.3f + 0.33f, v * 0.3f + 0.3f), 6);
            SaveTexture(floor, "Maps/Shaolin/Textures/Floor_BaseMap.png");

            // Brick wall
            var wall = CreateTexture("Brick");
            int brickH = _resolution / 16, brickW = _resolution / 8;
            for (int y = 0; y < _resolution; y++)
            {
                for (int x = 0; x < _resolution; x++)
                {
                    int row = y / brickH;
                    int offset = (row % 2 == 0) ? 0 : brickW / 2;
                    int bx = (x + offset) % brickW;
                    int by = y % brickH;
                    bool isMortar = bx < 2 || by < 2;
                    if (isMortar)
                        wall.SetPixel(x, y, new Color(0.35f, 0.33f, 0.31f));
                    else
                    {
                        float rv = Random.Range(-0.05f, 0.05f);
                        wall.SetPixel(x, y, new Color(0.51f + rv, 0.26f + rv * 0.5f, 0.18f + rv * 0.3f));
                    }
                }
            }
            wall.Apply();
            SaveTexture(wall, "Maps/Shaolin/Textures/Wall_BaseMap.png");

            EditorUtility.ClearProgressBar();
        }

        private void GenerateRadioactive()
        {
            EditorUtility.DisplayProgressBar("NeonTexGen", "Generating Radioactive...", 0.7f);

            var floor = GenerateNoise(v => new Color(v * 0.3f + 0.4f, v * 0.3f + 0.38f, v * 0.3f + 0.33f), 6);
            SaveTexture(floor, "Maps/Radioactive/Textures/Floor_BaseMap.png");

            if (_generateEmission)
            {
                var emit = GenerateNoise(v => {
                    float glow = Mathf.Pow(v, 3f);
                    return new Color(glow * 0.1f, glow, glow * 0.05f, glow * 0.8f);
                }, 6);
                SaveTexture(emit, "Maps/Radioactive/Textures/ToxicPool_Emission.png");
            }

            var wall = GenerateNoise(v => new Color(v * 0.3f + 0.42f, v * 0.3f + 0.4f, v * 0.3f + 0.38f), 5);
            SaveTexture(wall, "Maps/Radioactive/Textures/Wall_BaseMap.png");

            EditorUtility.ClearProgressBar();
        }

        private void GenerateBeast()
        {
            EditorUtility.DisplayProgressBar("NeonTexGen", "Generating Beast...", 0.9f);

            var floor = GenerateNoise(v => new Color(v * 0.2f + 0.15f, v * 0.06f + 0.04f, v * 0.1f + 0.06f), 8);
            SaveTexture(floor, "Maps/Beast/Textures/Floor_BaseMap.png");

            if (_generateEmission)
            {
                var emit = GenerateNoise(v => {
                    float spore = Mathf.Pow(v, 4f);
                    return new Color(spore * 0.8f, spore * 0.1f, spore * 0.6f, spore);
                }, 10);
                SaveTexture(emit, "Maps/Beast/Textures/Spore_Emission.png");
            }

            var wall = GenerateNoise(v => new Color(v * 0.15f + 0.1f, v * 0.05f + 0.03f, v * 0.08f + 0.06f), 6);
            SaveTexture(wall, "Maps/Beast/Textures/Wall_BaseMap.png");

            EditorUtility.ClearProgressBar();
        }

        private void GenerateShared()
        {
            var grid = GenerateGrid(new Color(0.12f, 0.12f, 0.14f), new Color(0.31f, 0.31f, 0.35f, 0.8f), 64, 1);
            SaveTexture(grid, "Shared/Textures/Default_Grid.png");

            var noise = GenerateNoise(v => new Color(v, v, v), 8);
            SaveTexture(noise, "Shared/Textures/Default_Noise.png");

            // Flat normal
            var flat = CreateTexture("FlatNormal");
            for (int y = 0; y < _resolution; y++)
                for (int x = 0; x < _resolution; x++)
                    flat.SetPixel(x, y, new Color(0.5f, 0.5f, 1f));
            flat.Apply();
            SaveTexture(flat, "Shared/Textures/Default_FlatNormal.png");

            Debug.Log("[NeonTexGen] Shared textures generated.");
        }
    }
}
