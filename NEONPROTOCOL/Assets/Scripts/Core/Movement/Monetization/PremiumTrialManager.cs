using UnityEngine;
using UnityEngine.Events;

namespace NeonProtocol.Core.Monetization
{
    public class PremiumTrialManager : MonoBehaviour
    {
        public static PremiumTrialManager Instance;

        [Header("Trial Parameters")]
        public float maxTrialSeconds = 3600f; // 1 Hour "Solid" limit
        public UnityEvent OnTrialExpired;

        private float accumulatedPlayTime = 0f;
        private bool isPremiumUnlocked = false;

        // Security Key for PlayerPrefs
        private readonly string timeKey = "NP_Session_Data_01X";
        private readonly string unlockKey = "NP_Premium_Status";

        void Awake()
        {
            if (Instance == null) { Instance = this; DontDestroyOnLoad(gameObject); }
            else { Destroy(gameObject); }

            LoadTrialData();
        }

        void Update()
        {
            if (isPremiumUnlocked) return; // Halt tracking if they own the game

            // Only count time while they are actually in a match, not paused
            if (Time.timeScale > 0)
            {
                accumulatedPlayTime += Time.unscaledDeltaTime;

                // Trigger the Gate
                if (accumulatedPlayTime >= maxTrialSeconds)
                {
                    ExecuteLockout();
                }
            }
        }

        private void ExecuteLockout()
        {
            Time.timeScale = 0; // Freeze the Matrix
            Debug.Log("[SUI-01] Trial Expired. Initiating Premium Purchase UI.");
            OnTrialExpired.Invoke(); // Triggers your Canvas UI to show the "Buy Full Game" button
        }

        private void LoadTrialData()
        {
            isPremiumUnlocked = PlayerPrefs.GetInt(unlockKey, 0) == 1;
            if (!isPremiumUnlocked)
            {
                accumulatedPlayTime = PlayerPrefs.GetFloat(timeKey, 0f);
            }
        }

        // Call this when the Android application closes or pauses to secure the data
        void OnApplicationPause(bool pauseStatus)
        {
            if (pauseStatus && !isPremiumUnlocked)
            {
                PlayerPrefs.SetFloat(timeKey, accumulatedPlayTime);
                PlayerPrefs.Save();
            }
        }

        // Call this from your Unity IAP success callback
        public void UnlockPremium()
        {
            isPremiumUnlocked = true;
            PlayerPrefs.SetInt(unlockKey, 1);
            PlayerPrefs.Save();
            Time.timeScale = 1; // Unfreeze the Matrix
            Debug.Log("[SUI-01] Premium Unlocked. Time Gate Shattered.");
        }
    }
}