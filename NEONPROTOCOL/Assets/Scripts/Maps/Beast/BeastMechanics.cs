using UnityEngine;
using UnityEngine.AI;

namespace NeonProtocol.Maps.Beast
{
    public class BeastMechanics : MonoBehaviour
    {
        [Header("Cryptid Settings")]
        [SerializeField] private LayerMask wallLayer;
        [SerializeField] private float rayDistance = 2f;
        [SerializeField] private float alignSpeed = 5f;
        
        private NavMeshAgent _agent;
        private Transform _modelTransform; // The visual mesh

        private void Awake()
        {
            _agent = GetComponent<NavMeshAgent>();
            _modelTransform = transform.GetChild(0); // Assuming model is child
        }

        private void Update()
        {
            AlignToSurface();
        }

        private void AlignToSurface()
        {
            RaycastHit hit;
            // Cast ray downwards/forwards to detect slope/wall
            // Logic: If on wall, rotate model Up vector to match wall Normal
            
            if (Physics.Raycast(transform.position, -transform.up, out hit, rayDistance, wallLayer))
            {
                Quaternion targetRot = Quaternion.FromToRotation(transform.up, hit.normal) * transform.rotation;
                _modelTransform.rotation = Quaternion.Slerp(_modelTransform.rotation, targetRot, Time.deltaTime * alignSpeed);
            }
            else if (Physics.Raycast(transform.position, transform.forward, out hit, rayDistance, wallLayer))
            {
                // Wall Climb Logic: Disable NavMeshAgent Y update? 
                // In a real scenario, we'd use OffMeshLinks for wall traversal.
                // This simulates the visual "sticking" to surfaces.
                Quaternion targetRot = Quaternion.LookRotation(Vector3.Cross(transform.right, hit.normal), hit.normal);
                 _modelTransform.rotation = Quaternion.Slerp(_modelTransform.rotation, targetRot, Time.deltaTime * alignSpeed);
            }
        }
    }
}