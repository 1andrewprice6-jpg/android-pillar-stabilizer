using UnityEngine;

namespace NeonProtocol.Core.Graphics.Procedural
{
    public class NeonShaderFactory : MonoBehaviour
    {
        public static NeonShaderFactory Instance;

        public Material neonGridMat;
        public Material neonZombieMat;
        public Material neonWallMat;

        private void Awake()
        {
            Instance = this;
            GenerateMaterials();
        }

        private void GenerateMaterials()
        {
            // 1. The Tron Grid
            neonGridMat = new Material(Shader.Find("Universal Render Pipeline/Lit"));
            neonGridMat.name = "Neon_Grid_M";
            neonGridMat.SetColor("_BaseColor", Color.black);
            neonGridMat.SetColor("_EmissionColor", new Color(0, 1, 1) * 3f); // Super bright Cyan
            neonGridMat.EnableKeyword("_EMISSION");
            // Note: Assign a texture if you want grid lines, otherwise it's just a glowing plane

            // 2. The Holographic Enemy
            neonZombieMat = new Material(Shader.Find("Universal Render Pipeline/Lit"));
            neonZombieMat.name = "Neon_Hologram_M";
            neonZombieMat.SetColor("_BaseColor", new Color(1, 0, 1, 0.5f)); // Magenta Transparent
            neonZombieMat.SetColor("_EmissionColor", new Color(1, 0, 1) * 2f);
            neonZombieMat.EnableKeyword("_EMISSION");
            neonZombieMat.EnableKeyword("_SURFACE_TYPE_TRANSPARENT");
            neonZombieMat.SetFloat("_Surface", 1); // Transparent Mode

            // 3. The World Geometry
            neonWallMat = new Material(Shader.Find("Universal Render Pipeline/Lit"));
            neonWallMat.name = "Neon_Construct_M";
            neonWallMat.SetColor("_BaseColor", new Color(0.1f, 0.1f, 0.1f));
            neonWallMat.SetColor("_EmissionColor", new Color(0.5f, 0, 1) * 1.5f); // Deep Purple
            neonWallMat.EnableKeyword("_EMISSION");
        }
    }
}