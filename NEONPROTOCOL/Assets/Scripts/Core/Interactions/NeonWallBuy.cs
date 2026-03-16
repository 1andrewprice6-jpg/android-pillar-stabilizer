using UnityEngine;
using NeonProtocol.Core.Combat;

namespace NeonProtocol.Core.Interactions
{
    public class NeonWallBuy : NeonInteractable
    {
        [Header("Weapon Settings")]
        [SerializeField] private string weaponName;
        [SerializeField] private GameObject weaponPrefab;

        protected override void OnPurchaseSuccess()
        {
            Debug.Log($"Purchased {weaponName}!");
            // Logic to give player weapon
            // PlayerCombat.Instance.EquipWeapon(weaponPrefab);
        }
    }
}