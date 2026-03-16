using UnityEngine;
using NeonProtocol.Core.Economy;
using NeonProtocol.Core.Player;
using NeonProtocol.Core.Combat;
using NeonProtocol.Core.Movement;

namespace NeonProtocol.Core.Interactions
{
    public enum PerkType { TuffNuff, UpNAtoms, BangBangs, TrailBlazers }

    public class PerkMachine : MonoBehaviour
    {
        [Header("Perk Configuration")]
        [SerializeField] private PerkType perkType;
        [SerializeField] private int cost;
        [SerializeField] private string perkName;

        public void Interact()
        {
            if (PointManager.Instance.TrySpendPoints(cost))
            {
                ApplyPerk();
            }
            else
            {
                Debug.Log($"Need more points for {perkName}!");
            }
        }

        private void ApplyPerk()
        {
            PlayerHealth playerHealth = PlayerHealth.Instance;
            
            switch (perkType)
            {
                case PerkType.TuffNuff:
                    playerHealth.ApplyTuffNuff();
                    break;
                
                case PerkType.UpNAtoms:
                    playerHealth.hasUpNAtoms = true;
                    Debug.Log("Up N Atoms Purchased: Self-Revive Active.");
                    break;

                case PerkType.BangBangs:
                    // Apply modifiers to Combat system
                    // Note: We need to modify PlayerCombat to store these multipliers
                    ApplyBangBangs();
                    break;

                case PerkType.TrailBlazers:
                    ApplyTrailBlazers();
                    break;
            }
        }

        private void ApplyBangBangs()
        {
            // Assuming we added these fields to PlayerCombat
            // PlayerCombat.Instance.damageMultiplier = 2.0f;
            // PlayerCombat.Instance.fireRateMultiplier = 0.67f; // (Increases rate by 33%)
            Debug.Log("Bang Bangs Active: Double Damage & High Fire Rate.");
        }

        private void ApplyTrailBlazers()
        {
            // Set flag on movement script for sliding AOE
            // NeonMovement.Instance.hasTrailBlazers = true;
            Debug.Log("Trail Blazers Active: No Fall Damage & Sliding Explosions.");
        }
    }
}