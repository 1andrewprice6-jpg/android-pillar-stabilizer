using UnityEngine;
using System.Collections;
using NeonProtocol.Core.Movement;
using NeonProtocol.Core.Combat;
using NeonProtocol.Core.Economy;

namespace NeonProtocol.Core.Player
{
    public class PlayerHealth : MonoBehaviour
    {
        public static PlayerHealth Instance;

        [Header("Health Stats")]
        public float maxHealth = 100f;
        public float currentHealth;
        [SerializeField] private float regenRate = 25f;
        [SerializeField] private float regenDelay = 4f;

        [Header("State")]
        public bool isDowned = false;
        public bool hasUpNAtoms = false;
        public bool hasTuffNuff = false;

        private float _lastDamageTime;
        private Coroutine _regenCoroutine;

        private void Awake()
        {
            Instance = this;
            currentHealth = maxHealth;
        }

        public void TakeDamage(float amount)
        {
            if (isDowned) return;

            currentHealth -= amount;
            _lastDamageTime = Time.time;

            if (currentHealth <= 0)
            {
                GoToLastStand();
            }
            else
            {
                if (_regenCoroutine != null) StopCoroutine(_regenCoroutine);
                _regenCoroutine = StartCoroutine(RegenerationRoutine());
            }
        }

        private IEnumerator RegenerationRoutine()
        {
            yield return new WaitForSeconds(regenDelay);

            while (currentHealth < maxHealth)
            {
                currentHealth = Mathf.Min(currentHealth + regenRate * Time.deltaTime, maxHealth);
                yield return null;
            }
        }

        private void GoToLastStand()
        {
            isDowned = true;
            currentHealth = 0;
            
            // Disable movement
            GetComponent<NeonMovement>().enabled = false;
            
            // In Solo mode, handle Self Revive
            if (hasUpNAtoms)
            {
                StartCoroutine(SelfReviveRoutine());
            }
            else
            {
                StartCoroutine(LastStandRoutine());
            }
        }

        private IEnumerator LastStandRoutine()
        {
            Debug.Log("Entered Last Stand. 30 seconds remaining...");
            yield return new WaitForSeconds(30f);
            
            if (isDowned)
            {
                Debug.Log("GAME OVER");
                // Trigger Game Over UI
            }
        }

        private IEnumerator SelfReviveRoutine()
        {
            Debug.Log("Self-Revive in progress...");
            yield return new WaitForSeconds(5f);
            Revive();
            hasUpNAtoms = false; // Used up
        }

        public void Revive()
        {
            isDowned = false;
            currentHealth = maxHealth;
            GetComponent<NeonMovement>().enabled = true;
            Debug.Log("Player Revived!");
        }

        public void ApplyTuffNuff()
        {
            hasTuffNuff = true;
            maxHealth = 250f;
            currentHealth = maxHealth;
            Debug.Log("Tuff Nuff Active: 250 HP");
        }
    }
}