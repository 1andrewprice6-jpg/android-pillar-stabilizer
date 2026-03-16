using UnityEngine;
using System.Collections;
using System.Collections.Generic;
using NeonProtocol.Core.Data;
using NeonProtocol.Core.Combat;

namespace NeonProtocol.Core.Economy
{
    public class MysteryBox : MonoBehaviour
    {
        [Header("Settings")]
        [SerializeField] private int boxCost = 950;
        [SerializeField] private float spinTime = 4f;
        [SerializeField] private List<WeaponData> weaponPool;
        [SerializeField] private Transform weaponDisplaySocket;
        [SerializeField] private GameObject interactionPromptUI;

        private bool _isSpinning;
        private WeaponData _selectedWeapon;
        private bool _canCollect;

        public void Interact()
        {
            if (_isSpinning) return;

            if (_canCollect)
            {
                CollectWeapon();
            }
            else if (PointManager.Instance.TrySpendPoints(boxCost))
            {
                StartCoroutine(SpinRoutine());
            }
        }

        private IEnumerator SpinRoutine()
        {
            _isSpinning = true;
            float elapsed = 0;
            float switchInterval = 0.1f;

            while (elapsed < spinTime)
            {
                _selectedWeapon = weaponPool[Random.Range(0, weaponPool.Count)];
                UpdateDisplayModel(_selectedWeapon.weaponModel);
                
                yield return new WaitForSeconds(switchInterval);
                elapsed += switchInterval;
                switchInterval *= 1.05f; // Slow down the spin
            }

            _selectedWeapon = GetWeightedRandomWeapon();
            UpdateDisplayModel(_selectedWeapon.weaponModel);
            
            _isSpinning = false;
            _canCollect = true;
            
            // Auto-despawn if not collected
            Invoke("ResetBox", 12f);
        }

        private WeaponData GetWeightedRandomWeapon()
        {
            int totalWeight = 0;
            foreach (var w in weaponPool) totalWeight += w.weight;

            int rand = Random.Range(0, totalWeight);
            int cursor = 0;

            foreach (var w in weaponPool)
            {
                cursor += w.weight;
                if (rand <= cursor) return w;
            }
            return weaponPool[0];
        }

        private void UpdateDisplayModel(GameObject model)
        {
            // Simple visual update logic
            foreach (Transform child in weaponDisplaySocket) Destroy(child.gameObject);
            Instantiate(model, weaponDisplaySocket);
        }

        private void CollectWeapon()
        {
            PlayerCombat.Instance.SwapWeapon(_selectedWeapon);
            ResetBox();
        }

        private void ResetBox()
        {
            _canCollect = false;
            _selectedWeapon = null;
            foreach (Transform child in weaponDisplaySocket) Destroy(child.gameObject);
            CancelInvoke("ResetBox");
        }
    }
}