using UnityEngine;

namespace NeonProtocol.Core.Interactions
{
    public enum PerkType { TuffNuff, Quickies, BangBangs, RacingStripes, BlueBolts }

    public class NeonPerkMachine : NeonInteractable
    {
        [Header("Perk Settings")]
        [SerializeField] private PerkType perkType;

        protected override void OnPurchaseSuccess()
        {
            Debug.Log($"Drank {perkType}!");
            // Apply perk modifier to player
            ApplyPerkEffect();
        }

        private void ApplyPerkEffect()
        {
            switch (perkType)
            {
                case PerkType.TuffNuff: // Juggernog equivalent
                    // Increase Player Health
                    break;
                case PerkType.RacingStripes: // Stamin-Up
                    // Increase Sprint Speed
                    break;
                case PerkType.Quickies: // Speed Cola
                    // Faster Reload
                    break;
            }
        }
    }
}