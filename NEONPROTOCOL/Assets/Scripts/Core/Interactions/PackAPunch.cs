using UnityEngine;
using NeonProtocol.Core.Combat;

namespace NeonProtocol.Core.Interactions
{
    public class PackAPunch : NeonInteractable
    {
        [Header("Upgrade Settings")]
        [SerializeField] private float damageMultiplier = 2.0f;
        [SerializeField] private int ammoBoost = 2;
        [SerializeField] private Material upgradedMaterial;

        protected override void OnPurchaseSuccess()
        {
            // Get current weapon from player
            // NeonWeapon currentWeapon = PlayerCombat.Instance.GetCurrentWeapon();
            
            // if (currentWeapon != null && !currentWeapon.IsUpgraded)
            // {
            //    UpgradeWeapon(currentWeapon);
            // }
            Debug.Log("Weapon Upgraded! Neon Infused!");
        }

        private void UpgradeWeapon(NeonWeapon weapon)
        {
            // weapon.Damage *= damageMultiplier;
            // weapon.MaxAmmo *= ammoBoost;
            // weapon.IsUpgraded = true;
            // weapon.ApplyMaterial(upgradedMaterial);
            // weapon.PlayUpgradeSound();
        }
    }
}