using UnityEngine;
using System.Collections;
using System.Collections.Generic;
using NeonProtocol.Core.Interactions;
using NeonProtocol.Core.Combat;

namespace NeonProtocol.Core.Interactions
{
    public class MagicWheel : NeonInteractable
    {
        [Header("Wheel Settings")]
        [SerializeField] private List<GameObject> weaponPool;
        [SerializeField] private float spinDuration = 4f;
        [SerializeField] private Transform weaponDisplaySocket;
        
        private bool _isSpinning = false;
        private GameObject _selectedWeapon;

        protected override void OnPurchaseSuccess()
        {
            if (_isSpinning) return;
            StartCoroutine(SpinRoutine());
        }

        private IEnumerator SpinRoutine()
        {
            _isSpinning = true;
            float timer = 0;
            float switchInterval = 0.1f;
            float nextSwitchTime = 0;

            GameObject currentDisplay = null;

            while (timer < spinDuration)
            {
                if (Time.time >= nextSwitchTime)
                {
                    if (currentDisplay != null) Destroy(currentDisplay);
                    
                    int randomIndex = Random.Range(0, weaponPool.Count);
                    currentDisplay = Instantiate(weaponPool[randomIndex], weaponDisplaySocket);
                    // Disable scripts on display item
                    if (currentDisplay.TryGetComponent(out NeonWeapon w)) w.enabled = false;
                    
                    nextSwitchTime = Time.time + switchInterval;
                    switchInterval *= 1.05f; // Slow down the spin
                }

                timer += Time.deltaTime;
                yield return null;
            }

            _selectedWeapon = currentDisplay;
            _isSpinning = false;
            
            // Allow player to pick up
            interactionPrompt = "Press to Take Weapon";
            cost = 0; 
        }

        public override void Interact()
        {
            if (!_isSpinning && _selectedWeapon != null)
            {
                // Logic to give weapon to player
                // PlayerCombat.Instance.SwapWeapon(_selectedWeapon);
                Destroy(_selectedWeapon);
                _selectedWeapon = null;
                ResetWheel();
            }
            else
            {
                base.Interact();
            }
        }

        private void ResetWheel()
        {
            interactionPrompt = "Spin the Wheel";
            cost = 950;
        }
    }
}