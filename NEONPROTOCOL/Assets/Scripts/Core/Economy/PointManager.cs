using UnityEngine;
using TMPro;

namespace NeonProtocol.Core.Economy
{
    public class PointManager : MonoBehaviour
    {
        public static PointManager Instance;

        [SerializeField] private TextMeshProUGUI pointsText;
        private int _totalPoints = 500; // Starting points

        private void Awake()
        {
            Instance = this;
            UpdateUI();
        }

        public void AddPoints(int amount)
        {
            _totalPoints += amount;
            UpdateUI();
        }

        public bool TrySpendPoints(int amount)
        {
            if (_totalPoints >= amount)
            {
                _totalPoints -= amount;
                UpdateUI();
                return true;
            }
            return false;
        }

        private void UpdateUI()
        {
            if (pointsText != null)
                pointsText.text = $"${_totalPoints}";
        }
    }
}