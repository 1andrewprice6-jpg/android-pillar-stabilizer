using UnityEngine;
using NeonProtocol.Core.AI;

namespace NeonProtocol.Maps.Shaolin.Enemies
{
    public class RollerSkaterAI : ZombieController
    {
        [Header("Skater Logic")]
        [SerializeField] private float skateSpeedBoost = 1.5f;
        [SerializeField] private float turnSmoothing = 5f;

        public override void OnSpawn()
        {
            base.OnSpawn();
            GetComponent<UnityEngine.AI.NavMeshAgent>().speed *= skateSpeedBoost;
            // Add skating animation triggers
        }

        // Potential override for movement behavior to make it feel like "skating"
        // (Less frequent path recalculations, higher momentum)
    }
}