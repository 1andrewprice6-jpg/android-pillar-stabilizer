using UnityEngine;

namespace NeonProtocol.Maps.Radioactive.Boss
{
    public class ArtilleryStrike : MonoBehaviour
    {
        [SerializeField] private GameObject explosionPrefab;
        [SerializeField] private float strikeDelay = 2f;
        
        public void CallStrike(Vector3 targetPosition)
        {
            // Logic for Kaiju boss fight artillery
            Debug.Log("Artillery inbound!");
            StartCoroutine(ExecuteStrike(targetPosition));
        }

        private System.Collections.IEnumerator ExecuteStrike(Vector3 pos)
        {
            // Visual indicator on ground
            yield return new WaitForSeconds(strikeDelay);
            Instantiate(explosionPrefab, pos, Quaternion.identity);
            // Damage check for Kaiju
        }
    }
}