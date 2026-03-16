using UnityEngine;

namespace NeonProtocol.Core.Interactions
{
    public class NeonDoor : NeonInteractable
    {
        [Header("Door Settings")]
        [SerializeField] private GameObject doorMesh;
        [SerializeField] private float slideDistance = 3f;
        [SerializeField] private float openSpeed = 2f;

        private bool _isOpen = false;

        protected override void OnPurchaseSuccess()
        {
            if (_isOpen) return;
            _isOpen = true;
            StartCoroutine(OpenDoorRoutine());
        }

        private System.Collections.IEnumerator OpenDoorRoutine()
        {
            Vector3 startPos = doorMesh.transform.position;
            Vector3 endPos = startPos + Vector3.up * slideDistance;
            float time = 0;

            while (time < 1)
            {
                time += Time.deltaTime * openSpeed;
                doorMesh.transform.position = Vector3.Lerp(startPos, endPos, time);
                yield return null;
            }
            
            // Re-bake or update NavMesh if necessary
            gameObject.SetActive(false);
        }
    }
}