using UnityEngine;
using NeonProtocol.Core.Movement;

namespace NeonProtocol.Maps.Beast.Environment
{
    public class LowGravityZone : MonoBehaviour
    {
        [SerializeField] private float gravityMultiplier = 0.3f;
        [SerializeField] private float jumpBoost = 2f;

        private void OnTriggerEnter(Collider other)
        {
            if (other.CompareTag("Player"))
            {
                // In a real scenario, you'd modify the gravity value in NeonMovement
                // For this architecture, we send a message or modify a public float
                Debug.Log("Entered Low Gravity");
            }
        }

        private void OnTriggerExit(Collider other)
        {
            if (other.CompareTag("Player"))
            {
                Debug.Log("Exited Low Gravity");
            }
        }
    }
}