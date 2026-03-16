using UnityEngine;
using System.Collections;

namespace NeonProtocol.Maps.Rave
{
    public class Zipline : MonoBehaviour
    {
        [SerializeField] private Transform startPoint;
        [SerializeField] private Transform endPoint;
        [SerializeField] private float travelSpeed = 15f;

        private bool _isUsing = false;

        public void UseZipline(GameObject player)
        {
            if (_isUsing) return;
            StartCoroutine(TravelRoutine(player.transform));
        }

        private IEnumerator TravelRoutine(Transform player)
        {
            _isUsing = true;
            float distance = Vector3.Distance(startPoint.position, endPoint.position);
            float duration = distance / travelSpeed;
            float time = 0;

            // Disable player movement during zipline
            var moveScript = player.GetComponent<NeonProtocol.Core.Movement.NeonMovement>();
            if (moveScript) moveScript.enabled = false;

            while (time < 1f)
            {
                time += Time.deltaTime / duration;
                player.position = Vector3.Lerp(startPoint.position, endPoint.position, time);
                yield return null;
            }

            if (moveScript) moveScript.enabled = true;
            _isUsing = false;
        }
    }
}