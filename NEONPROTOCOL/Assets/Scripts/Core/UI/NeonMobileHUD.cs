using UnityEngine;
using UnityEngine.UI;
using TMPro;
using NeonProtocol.Core.Input;

namespace NeonProtocol.Core.UI
{
    public class NeonMobileHUD : MonoBehaviour
    {
        [Header("Health & HUD")]
        [SerializeField] private Slider healthBar;
        [SerializeField] private TextMeshProUGUI ammoText;
        [SerializeField] private CanvasGroup screenBlood;

        [Header("Touch Controls")]
        [SerializeField] private GameObject virtualJoysticks;
        
        private float _maxHealth = 100f;
        private float _currentHealth;

        private void Start()
        {
            _currentHealth = _maxHealth;
            UpdateHealthUI();
        }

        public void TakeDamage(float amount)
        {
            _currentHealth -= amount;
            UpdateHealthUI();
            StartCoroutine(FlashBlood());
            
            if (_currentHealth <= 0)
            {
                // GameOver logic
            }
        }

        private void UpdateHealthUI()
        {
            if (healthBar) healthBar.value = _currentHealth / _maxHealth;
        }

        private System.Collections.IEnumerator FlashBlood()
        {
            screenBlood.alpha = 0.5f;
            while (screenBlood.alpha > 0)
            {
                screenBlood.alpha -= Time.deltaTime;
                yield return null;
            }
        }
        
        public void UpdateAmmo(int current, int reserve)
        {
            ammoText.text = $"{current} / {reserve}";
        }
    }
}