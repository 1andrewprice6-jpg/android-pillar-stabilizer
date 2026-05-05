using UnityEngine;

namespace NeonProtocol.Core.Data
{
    /// <summary>
    /// ScriptableObject defining the visual theme configuration for a single map.
    /// Create instances via Assets > Create > NeonProtocol > MapThemeData.
    /// </summary>
    [CreateAssetMenu(fileName = "New MapTheme", menuName = "NeonProtocol/MapThemeData")]
    public class MapThemeData : ScriptableObject
    {
        [Header("Identity")]
        public string mapName;
        [TextArea(2, 4)]
        public string mapDescription;
        public Sprite mapIcon;

        [Header("Lighting")]
        public Color ambientColor = new Color(0.1f, 0.1f, 0.15f);
        public Color fogColor = new Color(0.05f, 0.05f, 0.1f);
        public float fogDensity = 0.02f;
        public bool useVolumetricFog = false;

        [Header("Primary Palette")]
        public Color primaryNeon = Color.cyan;
        public Color secondaryNeon = Color.magenta;
        public Color accentColor = Color.yellow;

        [Header("Emission")]
        [Range(0f, 10f)]
        public float emissionIntensity = 2f;
        public bool pulseEmission = false;
        [Range(0.1f, 5f)]
        public float pulseSpeed = 1f;

        [Header("Materials — Assigned at Runtime")]
        public Material floorMaterial;
        public Material wallMaterial;
        public Material skyboxMaterial;

        [Header("Textures — Base Maps")]
        public Texture2D floorBaseMap;
        public Texture2D floorNormal;
        public Texture2D floorEmission;
        public Texture2D wallBaseMap;
        public Texture2D wallNormal;
        public Texture2D wallMetallicSmoothness;

        [Header("Post-Processing")]
        [Range(-1f, 1f)]
        public float saturationOffset = 0f;
        [Range(0f, 2f)]
        public float bloomIntensity = 1f;
        [Range(0f, 1f)]
        public float chromaticAberration = 0f;
        [Range(-50f, 50f)]
        public float colorTemperature = 0f;

        [Header("Audio")]
        public AudioClip ambientLoop;
        [Range(0f, 1f)]
        public float ambientVolume = 0.5f;

        /// <summary>
        /// Applies this theme's fog and ambient settings to the active scene.
        /// Call from the map manager's Awake or Start.
        /// </summary>
        public void ApplyToScene()
        {
            RenderSettings.ambientLight = ambientColor;
            RenderSettings.fog = true;
            RenderSettings.fogColor = fogColor;
            RenderSettings.fogMode = FogMode.ExponentialSquared;
            RenderSettings.fogDensity = fogDensity;

            if (skyboxMaterial != null)
                RenderSettings.skybox = skyboxMaterial;
        }
    }
}
