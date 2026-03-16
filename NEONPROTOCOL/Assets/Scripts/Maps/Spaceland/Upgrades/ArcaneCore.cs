using UnityEngine;
using NeonProtocol.Core.Combat;

namespace NeonProtocol.Maps.Spaceland.Upgrades
{
    public enum ElementType { Fire, Wind, Lightning, Poison }

    public class ArcaneCore : MonoBehaviour
    {
        [SerializeField] private ElementType currentElement;
        [SerializeField] private ParticleSystem elementalEffect;

        public void ApplyToWeapon(NeonWeapon weapon)
        {
            // Logic to modify weapon damage type and VFX
            Debug.Log($"Applied {currentElement} to weapon.");
            if (elementalEffect) elementalEffect.Play();
        }

        // Logic to "collect" souls/souls requirement to charge the core
        public void AddSoul()
        {
            // Counter ++
            // If full, allow pickup
        }
    }
}