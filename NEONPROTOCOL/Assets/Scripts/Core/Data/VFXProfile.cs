using UnityEngine;

namespace NeonProtocol.Core.Data
{
    /// <summary>
    /// Per-map VFX configuration for particle systems, screen effects, and decals.
    /// Create instances via Assets > Create > NeonProtocol > VFXProfile.
    /// </summary>
    [CreateAssetMenu(fileName = "New VFXProfile", menuName = "NeonProtocol/VFXProfile")]
    public class VFXProfile : ScriptableObject
    {
        [Header("Blood / Hit FX")]
        public Color bloodColor = Color.red;
        public Texture2D bloodSplatter;
        public int bloodParticleCount = 15;

        [Header("Muzzle Flash")]
        public Color muzzleFlashColor = new Color(1f, 0.9f, 0.5f);
        [Range(0.01f, 0.2f)]
        public float muzzleFlashDuration = 0.05f;
        public Texture2D muzzleFlashSprite;

        [Header("Impact Decals")]
        public Texture2D bulletHoleDecal;
        public Texture2D scorchDecal;
        [Range(0.5f, 3f)]
        public float decalScale = 1f;

        [Header("Ambient Particles")]
        public bool enableAmbientParticles = true;
        public Texture2D ambientParticleSprite;
        public Color ambientParticleColor = Color.white;
        public int ambientParticleCount = 50;
        [Range(0.1f, 5f)]
        public float ambientParticleSpeed = 0.5f;

        [Header("Screen Effects")]
        [Range(0f, 1f)]
        public float vignetteIntensity = 0.3f;
        [Range(0f, 0.5f)]
        public float filmGrain = 0.05f;
        public bool enableLensDistortion = false;

        [Header("Map-Specific FX")]
        [Tooltip("Tag used by NeonPooler for this map's unique VFX prefab")]
        public string specialFXPoolTag;
        public Color specialFXColor = Color.white;
    }
}
