using UnityEngine;

namespace NeonProtocol.Core.Data
{
    [CreateAssetMenu(fileName = "New Weapon", menuMenuName = "NeonProtocol/WeaponData")]
    public class WeaponData : ScriptableObject
    {
        public string weaponName;
        public float damage = 20f;
        public float fireRate = 0.1f;
        public int clipSize = 30;
        public int maxReserve = 120;
        public float reloadTime = 2.0f;
        public int weight = 10; // For Mystery Box weighted random
        public GameObject weaponModel;
    }
}