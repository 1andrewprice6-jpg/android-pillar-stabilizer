using UnityEngine;
using System.Collections;
using TMPro;

namespace NeonProtocol.Core.UI
{
    public class RoundTransitionUI : MonoBehaviour
    {
        [SerializeField] private TextMeshProUGUI roundText;
        [SerializeField] private CanvasGroup canvasGroup;
        [SerializeField] private float fadeDuration = 2f;

        public void DisplayNewRound(int roundNumber)
        {
            StopAllCoroutines();
            StartCoroutine(RoundRoutine(roundNumber));
        }

        private IEnumerator RoundRoutine(int round)
        {
            roundText.text = round.ToString();
            
            // Fade In
            float t = 0;
            while (t < 1f)
            {
                t += Time.deltaTime / fadeDuration;
                canvasGroup.alpha = t;
                yield return null;
            }

            yield return new WaitForSeconds(3f);

            // Fade Out
            while (t > 0f)
            {
                t -= Time.deltaTime / fadeDuration;
                canvasGroup.alpha = t;
                yield return null;
            }
        }
    }
}