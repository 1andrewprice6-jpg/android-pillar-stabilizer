using UnityEngine;
using NeonProtocol.Core.Input;
using NeonProtocol.Core.UI;

namespace NeonProtocol.Core.Interactions
{
    public class InteractionRaycaster : MonoBehaviour
    {
        [SerializeField] private float interactRange = 3f;
        [SerializeField] private LayerMask interactLayer;
        
        private Transform _cam;

        private void Awake() => _cam = Camera.main.transform;

        private void Update()
        {
            RaycastHit hit;
            if (Physics.Raycast(_cam.position, _cam.forward, out hit, interactRange, interactLayer))
            {
                if (hit.collider.TryGetComponent(out NeonInteractable interactable))
                {
                    // Update UI Prompt (e.g., "Press X to Buy Door [$1000]")
                    // UIController.Instance.ShowPrompt(interactable.GetPrompt());

                    if (NeonInputHandler.Instance.JumpInput) // Using Jump as temp Interact button
                    {
                        interactable.Interact();
                    }
                }
            }
            else
            {
                // UIController.Instance.HidePrompt();
            }
        }
    }
}