using UnityEngine;

namespace NeonProtocol.Maps.Spaceland
{
    public class Teleporter : MonoBehaviour
    {
        [SerializeField] private Transform destination;
        [SerializeField] private float cooldown = 5f;
        
        private float _lastUseTime;

        private void OnTriggerEnter(Collider other)
        {
            if (other.CompareTag("Player") && Time.time > _lastUseTime + cooldown)
            {
                Teleport(other.transform);
            }
        }

        private void Teleport(Transform player)
        {
            _lastUseTime = Time.time;
            // Add Screen Flash FX
            player.position = destination.position;
            player.rotation = destination.rotation;
        }
    }
}