using UnityEngine;
using TMPro;

namespace NeonProtocol.Core.Economy
{
    public class PointsSystem : MonoBehaviour
    {
        public static PointsSystem Instance;

        [SerializeField] private TextMeshProUGUI pointsText;
        private int _currentPoints = 500; // Starting cash

        private void Awake() => Instance = this;

        private void Start() => UpdateUI();

        public void AddPoints(int amount)
        {
            _currentPoints += amount;
            UpdateUI();
        }

        public bool TrySpendPoints(int amount)
        {
            if (_currentPoints >= amount)
            {
                _currentPoints -= amount;
                UpdateUI();
                return true;
            }
            return false;
        }

        private void UpdateUI()
        {
            if (pointsText != null)
                pointsText.text = $"${_currentPoints}";
        }
    }
}