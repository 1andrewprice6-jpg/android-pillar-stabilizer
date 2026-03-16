using UnityEngine;
using UnityEditor;

namespace NeonProtocol.Editor
{
    public class MobileLightingOptimizer : EditorWindow
    {
        [MenuItem("Neon Protocol/Optimize Lighting for Android")]
        public static void OptimizeBakeSettings()
        {
            // Forces the Lightmapper into a "Solid" mobile configuration
            LightmapEditorSettings.lightmapper = LightmapEditorSettings.Lightmapper.ProgressiveGPU;
            LightmapEditorSettings.bakeResolution = 15f; // 15 Texels per unit is the mobile sweet spot
            LightmapEditorSettings.maxBounces = 2; // Prevents infinite ray calculation
            LightmapEditorSettings.textureCompression = true;
            LightmapEditorSettings.enableAmbientOcclusion = false; // AO is too expensive to bake at high-res
            
            Debug.Log("[SRA-01] Android Lightmap settings forcefully applied. Ready for Baking.");
        }
    }
}